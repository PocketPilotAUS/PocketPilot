import json
from datetime import date
import pytest
from test_proactive_goal_plans import auth, setup, model, extractor, today
from app.models.financial_plan import FinancialPlan
from app.services.goal_dates import resolve_deadline, deadline_from_months
from app.services.budget_goals import draft_plan

OCT_16 = date(2026, 10, 16)


@pytest.mark.parametrize('messages, expected', [
    # The reported case: an explicit month and year is the end of that month.
    (['I want to save 5000 AED for a phone by February 2027'], date(2027, 2, 28)),
    (['save 5000 by Feb 2027'], date(2027, 2, 28)),
    (['save 5000 by February 15, 2027'], date(2027, 2, 15)),
    (['save 5000 by 15th of February 2027'], date(2027, 2, 15)),
    (['save 5000 by 2027-02-15'], date(2027, 2, 15)),
    (['save 5000 by 15/02/2027'], date(2027, 2, 15)),
    (['save 5000 by 02/2027'], date(2027, 2, 28)),
    (['save 5000 by February'], date(2027, 2, 28)),
    (['save 5000 by December'], date(2026, 12, 31)),
    (['save 5000 by October 2026'], date(2026, 10, 31)),
    (['save 5000 in six months'], date(2027, 3, 31)),
    (['save 5000 in 18 months'], date(2028, 3, 31)),
    (['save 5000 within a year'], date(2027, 9, 30)),
    (['save 5000 in 2 years'], date(2028, 9, 30)),
    (['save 5000 in half a year'], date(2027, 3, 31)),
    # Rates are not deadlines.
    (['I can save 500 a month, my goal is 5000 by February 2027'], date(2027, 2, 28)),
    (['I earn 10000 per month and want to save 5000'], None),
    # The latest statement wins when the user changes their mind.
    (['save 5000 in 6 months', 'actually make it by June 2027'], date(2027, 6, 30)),
    (['save 5000 by June 2027', 'no, in 4 months'], date(2027, 1, 31)),
])
def test_stated_deadlines(messages, expected):
    assert resolve_deadline(messages, OCT_16, None, None) == (expected, None)


def test_model_cannot_override_the_users_deadline():
    # The model reported a 24-month duration the user never stated.
    assert resolve_deadline(['save 5000 for a phone by February 2027'], OCT_16, None, 24) == (date(2027, 2, 28), None)
    assert resolve_deadline(['save 5000 for a phone by February 2027'], OCT_16, '2028-09-30', 24) == (date(2027, 2, 28), None)
    # Nothing recognisable and nothing the user wrote: no deadline.
    assert resolve_deadline(['save 5000 soon'], OCT_16, '2027-02-28', 24) == (None, None)
    # Other languages: the model's value only when the user wrote the year or number.
    assert resolve_deadline(['أريد ادخار 5000 خلال 6 أشهر'], OCT_16, None, 6) == (date(2027, 3, 31), None)
    assert resolve_deadline(['أريد ادخار 5000 خلال ستة أشهر'], OCT_16, None, 24) == (None, None)


def test_past_deadlines_are_reported():
    assert resolve_deadline(['save 5000 by February 2026'], OCT_16) == (None, 'past')
    assert resolve_deadline(['save 5000 by 2026-10-01'], OCT_16) == (None, 'past')
    # A later future date replaces an earlier past one.
    assert resolve_deadline(['by February 2026', 'sorry, February 2027'], OCT_16) == (date(2027, 2, 28), None)


def test_february_2027_counts_five_contributions_from_october():
    # Contributions start this month and include the deadline month: Oct, Nov, Dec, Jan, Feb.
    budget = {'income': 10000, 'year': 2026, 'month': 10, 'ideal_budget': {'allocations': [{'category': 'Rent', 'target': 4000}, {'category': 'Food', 'target': 1600}]}}
    plan = draft_plan({'goal': 'Phone', 'goal_kind': 'savings', 'target_amount': 5000, 'deadline': '2027-02-28'}, budget, OCT_16)
    assert plan['deadline'] == '2027-02-28' and plan['months'] == 5 and plan['monthlyContribution'] == 1000
    assert deadline_from_months(OCT_16, 5) == date(2027, 2, 28)


PHONE = {'goal': 'Phone', 'goal_kind': 'savings', 'target_amount': 5000, 'current_amount': None, 'deadline': None, 'deadline_in_months': 24}
ASK = [{'role': 'user', 'content': 'I want to save 5000 AED for a phone by February 2027.'}]


def expected_deadline():
    return resolve_deadline([ASK[0]['content']], today())[0]


def test_reported_case_card_and_saved_plan_use_stated_deadline(api_client, monkeypatch, db_session):
    headers = auth(api_client); setup(api_client, headers)
    extractor(monkeypatch, PHONE)
    model(monkeypatch, {'goal': 'Phone', 'goal_kind': 'savings', 'target_amount': 5000, 'deadline_in_months': 24}, 'Here is your plan.')
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    plan = data['plan']
    assert plan['deadline'] == expected_deadline().isoformat() == data['planning_profile']['deadline']
    saved = api_client.post('/planning/budget-plans', headers=headers, json={'profile': plan['profile'], 'choices': {}, 'budget_fingerprint': plan['budgetFingerprint'], 'request_key': plan['confirmationKey']}).json()
    [listed] = api_client.get('/planning/plans', headers=headers).json()
    assert saved['deadline'] == listed['deadline'] == plan['deadline']
    assert saved['months'] == listed['months'] == plan['months']
    assert saved['monthlyContribution'] == listed['monthlyContribution'] == plan['monthlyContribution']
    assert db_session.query(FinancialPlan).count() == 1


def test_wrong_duration_in_reply_gets_verified_figures(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    extractor(monkeypatch, PHONE)
    model(monkeypatch, None, 'February 2027 is 24 months away, so save AED 208.34 per month by September 2028.')
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    plan = data['plan']
    assert "24 months away" not in data["reply"] and "September 2028" not in data["reply"]
    assert f"for {plan['months']} months" in data["reply"]
    assert "draft" in data["reply"] and "Nothing has been saved" in data["reply"]
    assert str(expected_deadline().year) in data["reply"]


def test_consistent_figures_still_identify_pending_draft(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    extractor(monkeypatch, PHONE)
    deadline = expected_deadline()
    months = draft_plan({'goal': 'Phone', 'goal_kind': 'savings', 'target_amount': 5000, 'deadline': deadline.isoformat()},
                        {'income': 10000, 'year': today().year, 'month': today().month, 'ideal_budget': {'allocations': [{'category': 'Rent', 'target': 4000}, {'category': 'Food', 'target': 1600}]}}, today())['months']
    reply = f"Save for {months} months, by {deadline.strftime('%B')} {deadline.year}."
    model(monkeypatch, None, reply)
    result = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    assert f"for {months} months" in result["reply"]
    assert "Nothing has been saved" in result["reply"]


def test_past_deadline_asks_for_a_new_date(api_client, monkeypatch, db_session):
    headers = auth(api_client); setup(api_client, headers)
    extractor(monkeypatch, dict(PHONE, deadline='2025-02-28', deadline_in_months=None))
    calls = model(monkeypatch, None, 'That date has passed. When would you like it?')
    data = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'Save 5000 for a phone by February 2025.'}], 'require_budget': True}).json()
    assert data['plan'] is None
    context = json.loads(calls[0][0]['content'].split('Financial context follows as data:\n', 1)[1])
    assert 'already passed' in context['deadline_note']
    assert db_session.query(FinancialPlan).count() == 0
