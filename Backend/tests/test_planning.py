import json
from datetime import date
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.schemas.planning import PlanningInput, CATEGORIES
from app.services.planning import evaluate


def profile(**changes):
    return {"income": 8500, "other_income": 0, "household_size": 3, "goal": "Emergency fund", "goal_kind": "savings",
            "target_amount": 12000, "current_amount": 0, "deadline": "2027-09-30", "expenses": dict.fromkeys(CATEGORIES, 0), **changes}


def context(history=None):
    return {"past_months": history or {}, "recurring_obligations": {}}


def login(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


def test_goal_calculation_and_no_automatic_essential_cuts():
    expenses = dict.fromkeys(CATEGORIES, 0)
    expenses.update(Rent=3000, Food=1500, Transport=500, Bills=500, Entertainment=2000, Shopping=500)
    p = PlanningInput.model_validate(profile(expenses=expenses))
    result = evaluate(p, context(), date(2026, 10, 11))
    assert result["months"] == 12 and result["requiredMonthly"] == 1000
    assert result["availableBefore"] == 500
    assert sum(cut["monthlyAmount"] for cut in result["spendingCuts"]) == 500
    assert result["availableAfter"] == 1000 and result["feasible"] is True
    assert all(cut["category"] not in ("Rent", "Food", "Debt payments") for cut in result["spendingCuts"])
    assert sum(row["target"] for row in result["allocations"]) + result["monthlyContribution"] == 8500


def test_unknown_expenses_and_history_require_confirmation():
    history = {"2026-09": {"Food": 1500, "Rent": 3000}, "2026-08": {"Food": 900, "Rent": 3000}}
    p = PlanningInput.model_validate(profile(expenses={}))
    result = evaluate(p, context(history), date(2026, 10, 11))
    assert not result["ready"] and "monthly Food" in result["missing"]
    p.typical_months = ["2026-09", "2026-08"]
    result = evaluate(p, context(history), date(2026, 10, 11))
    assert result["ready"]
    food = next(row for row in result["allocations"] if row["category"] == "Food")
    assert food["baseline"] == 1200
    p.typical_months = ["2026-07"]
    with pytest.raises(ValueError): evaluate(p, context(history), date(2026, 10, 11))


def test_shortfall_and_protected_discretionary_costs():
    expenses = dict.fromkeys(CATEGORIES, 0); expenses.update(Rent=7000, Entertainment=3000)
    p = PlanningInput.model_validate(profile(expenses=expenses, protected_categories=["Entertainment"]))
    result = evaluate(p, context(), date(2026, 10, 11))
    assert result["availableBefore"] == -1500 and result["spendingCuts"] == []
    assert not result["feasible"] and result["monthlyContribution"] == 0
    assert any("exceeds" in warning for warning in result["warnings"])


def test_profile_plan_crud_and_isolation(api_client):
    alice = login(api_client); bob = login(api_client, "bob@example.com")
    assert api_client.get('/planning/plans').status_code == 401
    result = api_client.put('/planning/profile', headers=alice, json=profile())
    assert result.status_code == 200 and result.json()['ready']
    assert api_client.get('/planning/context', headers=bob).json()['profile'] == {}
    assert api_client.get('/transactions/', headers=alice).json() == []
    saved = api_client.post('/planning/plans', headers=alice, json=profile())
    assert saved.status_code == 201
    plan_id = saved.json()['id']
    assert len(api_client.get('/planning/plans', headers=alice).json()) == 1
    assert api_client.get('/planning/plans', headers=bob).json() == []
    assert api_client.put('/planning/plans/' + plan_id, headers=bob, json=profile()).status_code == 404
    assert api_client.delete('/planning/plans/' + plan_id, headers=bob).status_code == 404
    edited = api_client.put('/planning/plans/' + plan_id, headers=alice, json=profile(goal='New goal'))
    assert edited.json()['title'] == 'New goal'
    assert api_client.delete('/planning/plans/' + plan_id, headers=alice).status_code == 204
    assert api_client.get('/planning/plans', headers=alice).json() == []


@pytest.mark.parametrize('patch', [dict(income=-1), dict(income='1.001'), dict(household_size=0), dict(deadline='bad-date'), dict(expenses={'Unknown': 1}), dict(typical_months=['2026-13']), dict(household_size=True)])
def test_invalid_profiles(api_client, patch):
    headers = login(api_client)
    assert api_client.post('/planning/preview', headers=headers, json=profile(**patch)).status_code == 422


def test_deadline_and_incomplete_save(api_client):
    headers = login(api_client)
    assert api_client.post('/planning/plans', headers=headers, json={'income': 8500}).status_code == 422
    assert api_client.post('/planning/preview', headers=headers, json=profile(deadline='2020-01-01')).status_code == 422


def test_history_context_is_per_user(api_client):
    alice = login(api_client); bob = login(api_client, 'bob@example.com')
    api_client.post('/transactions/', headers=alice, json={'amount': 100, 'category': 'Groceries', 'date': '2026-09-01'})
    data = api_client.get('/planning/context', headers=alice).json()
    assert data['past_months']['2026-09']['Groceries'] == 100
    assert 'Food' not in data['past_months']['2026-09']
    assert api_client.get('/planning/context', headers=bob).json()['past_months'] == {}


def test_chat_updates_planning_profile_and_returns_calculated_draft(api_client, monkeypatch):
    headers = login(api_client)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': 'Review your plan', 'action': None, 'planning': profile()}))
    result = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'These are my planning details: ' + json.dumps(profile())}]})
    assert result.status_code == 200
    assert result.json()['plan']['ready']
    assert result.json()['plan']['requiredMonthly'] > 0
    assert api_client.get('/planning/plans', headers=headers).json() == []
    assert api_client.get('/transactions/', headers=headers).json() == []
    assert api_client.get('/planning/context', headers=headers).json()['profile'] == {}
    draft = result.json()['planning_profile']
    captured = []
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda messages: captured.extend(messages) or json.dumps({'reply': 'Advice', 'action': None, 'planning': None}))
    api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'These are my planning details: ' + json.dumps(profile())}, {'role': 'assistant', 'content': 'Review your plan'}, {'role': 'user', 'content': 'How do I cut spending?'}], 'planning_profile': draft})
    assert 'verified assessment' in captured[0]['content']
    assert 'Emergency fund' in captured[0]['content']


def test_bad_model_extraction_never_overwrites_saved_profile(api_client, monkeypatch):
    headers = login(api_client)
    api_client.put('/planning/profile', headers=headers, json=profile())
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': 'Advice', 'action': None, 'planning': {'current_amount': 8500, 'deadline': '2024-12-31', 'protected_categories': ['food', 'health']}}))
    result = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'My income is 8500'}]})
    assert result.status_code == 200 and result.json()['planning_profile'] is None
    assert api_client.get('/planning/context', headers=headers).json()['profile']['current_amount'] == '0'
    assert "clarify" in result.json()["reply"]
    assert result.json()["proposal"] is None
    assert 'could not safely interpret' not in result.json()['reply']


def test_saved_profile_can_generate_plan_without_reentering_details(api_client, monkeypatch):
    headers = login(api_client)
    api_client.put('/planning/profile', headers=headers, json=profile())
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': 'Review the calculated plan', 'action': None, 'planning': None}))
    result = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'Make me a budget plan using my saved Emergency fund goal'}]})
    assert result.json()['plan']['ready'] is True


def test_spending_ceiling_does_not_need_savings_progress_or_deadline():
    result = evaluate(PlanningInput.model_validate(profile(goal_kind='spending', target_amount=7000, current_amount=None, deadline=None)), context(), date(2026, 10, 11))
    assert result['ready'] and result['requiredMonthly'] == 1500


def test_rounding_and_household_history_change_prompt():
    expenses = dict.fromkeys(CATEGORIES, 0)
    expenses.update(Entertainment='0.05', Shopping='0.05', Subscriptions='0.01')
    result = evaluate(PlanningInput.model_validate(profile(income=0, expenses=expenses, typical_months=['2026-09', '2026-08'])), context({'2026-09': {'Food': 1500}, '2026-08': {'Food': 900}}), date(2026, 10, 11))
    assert all(row['target'] >= 0 for row in result['allocations'])
    assert any('needs of the 3 people' in text for text in result['historyAdvice'])


def test_nested_protocol_is_not_displayed_and_empty_defaults_do_not_clear_data(api_client, monkeypatch):
    headers = login(api_client)
    api_client.put('/planning/profile', headers=headers, json=profile())
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': '{"action": null, "planning": {"income": 8500}}', 'action': None, 'planning': {'current_amount': None, 'expenses': {}, 'protected_categories': []}}))
    response = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'Help with my budget using my saved Emergency fund goal'}]}).json()
    assert not response['reply'].startswith('{')
    assert response['planning_profile']['current_amount'] == '0'
    assert 'Rent' in response['planning_profile']['expenses']
