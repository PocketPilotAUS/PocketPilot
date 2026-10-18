import json
import pytest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from conftest import register_user, login_user, auth_headers
from app.services.budget_goals import assess, fingerprint


def budget(income=10000, categories=None):
    return {'income': income, 'year': 2026, 'month': 10, 'ideal_budget': {'allocations': [
        {'category': name, 'target': value, 'spent': 99999} for name, value in (categories or {'Rent': 5000, 'Entertainment': 3000, 'Food': 1000}).items()]}}


GOAL = {'goal': 'Vacation', 'target_amount': 12000, 'current_amount': 0, 'deadline': '2027-03-31'}
TODAY = date(2026, 10, 14)


def test_planned_budget_only_and_conditional_cuts():
    saved = budget()
    result = assess(GOAL, saved, TODAY)
    assert result['availableBefore'] == 1000 and result['requiredMonthly'] == 2000
    assert result['unfundedMonthly'] == 1000
    assert result['availableAfter'] == 1000
    assert result['suggestions'][0] == {'category': 'Entertainment', 'baseline': 3000, 'target': 2100, 'monthlyAmount': 900, 'essential': False}
    assert result['suggestions'][1]['essential'] is True
    assert result['scenarioUnfunded'] == 0
    assert result['later_deadline'] == '2027-09-30'
    assert saved['ideal_budget']['allocations'][0]['target'] == 5000


def test_protected_essential_and_accepted_scenario():
    saved = budget()
    result = assess(GOAL, saved, TODAY, {'protected': ['Rent', 'Food'], 'targets': {'Entertainment': 2000}})
    assert result['feasible'] and result['availableAfter'] == 2000
    assert result['suggestions'] == []
    result = assess(GOAL, saved, TODAY, {'protected': ['Rent', 'Food', 'Entertainment']})
    assert result['suggestions'] == [] and result['later_deadline'] == '2027-09-30'
    result = assess(GOAL, saved, TODAY, {'protected': ['*'], 'targets': {'Rent': 3000}})
    assert result['suggestions'] == [] and result['accepted'] == []
    result = assess(GOAL, saved, TODAY, {'protected': ['rent', 'food', 'entertainment']})
    assert result['suggestions'] == []


def test_zero_surplus_custom_categories_and_rounding():
    result = assess(GOAL, budget(9000), TODAY, {'protected': ['Rent', 'Food', 'Entertainment']})
    assert result['no_surplus'] and result['later_deadline'] is None
    result = assess({**GOAL, 'target_amount': '0.01'}, budget(100, {'School fees': 99}), TODAY)
    assert result['planned_total'] == 99 and result['requiredMonthly'] == .01
    assert result['suggestions'] == []
    result = assess({**GOAL, 'deadline': '2020-01-01'}, budget(), TODAY)
    assert not result['ready'] and result['missing'] == ['future deadline']


def auth(client, email='alice@example.com'):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()['access_token'])


def save_budget(client, headers, income=10000):
    now = datetime.now(timezone(timedelta(hours=4))).date()
    response = client.put(f'/budget/setup?year={now.year}&month={now.month}', headers=headers, json={
        'income': income, 'categories': [{'name': 'Rent', 'amount': 5000}, {'name': 'Entertainment', 'amount': 3000}, {'name': 'School fees', 'amount': 1000}]})
    assert response.status_code == 200
    return response.json()


def test_missing_budget_flow_without_model_and_owner_isolation(api_client, monkeypatch):
    alice = auth(api_client)
    bob = auth(api_client, 'bob@example.com')
    save_budget(api_client, bob)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: (_ for _ in ()).throw(AssertionError('No model needed for missing budget')))
    messages = [{'role': 'user', 'content': 'I want to save for a vacation'}]
    response = api_client.post('/ai/chat', headers=alice, json={'messages': messages}).json()
    assert response['budget_required'] and response['goal_planning']
    assert response['proposal'] is None and response['plan'] is None


@pytest.mark.parametrize('message', ['yo', 'help me', 'I need 50000 by next summer', 'ساعدني', '帮帮我'])
def test_mobile_missing_budget_does_not_depend_on_keywords(api_client, monkeypatch, message):
    headers = auth(api_client)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: pytest.fail('Missing budget must not invoke the model'))
    response = api_client.post('/ai/chat', headers=headers, json={
        'messages': [{'role': 'user', 'content': message}], 'require_budget': True})
    assert response.status_code == 200
    assert response.json()['budget_required'] is True
    assert response.json()['goal_planning'] is True
    assert 'budget tracker' in response.json()['reply']


def test_mobile_saved_budget_does_not_gate_general_chat(api_client, monkeypatch):
    headers = auth(api_client)
    save_budget(api_client, headers)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': 'Hello', 'action': None, 'planning': None}))
    response = api_client.post('/ai/chat', headers=headers, json={
        'messages': [{'role': 'user', 'content': 'yo'}], 'require_budget': True})
    assert response.status_code == 200
    assert response.json()['budget_required'] is False
    assert response.json()['reply'] == 'Hello'


def test_saved_budget_authoritative_and_resume_preserves_goal(api_client, monkeypatch, db_session):
    headers = auth(api_client)
    saved = save_budget(api_client, headers)
    captured = []
    future = '2090-03-31'
    def reply(messages):
        captured.extend(messages)
        return json.dumps({'reply': 'Use your saved budget.', 'action': {'kind': 'income', 'amount': 999999, 'year': 2026, 'month': 10},
                           'planning': {'goal': 'Vacation', 'goal_kind': 'savings', 'target_amount': 50000, 'deadline': future, 'income': 999999, 'expenses': {'Rent': 0}}})
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', reply)
    history = [{'role': 'user', 'content': 'I want to save for a vacation'}, {'role': 'assistant', 'content': 'Please fill out your budget tracker.'}, {'role': 'user', 'content': 'Budget saved. Continue my goal.'}]
    response = api_client.post('/ai/chat', headers=headers, json={'messages': history, 'goal_planning': True, 'resume_budget_goal': True})
    assert response.status_code == 200
    data = response.json()
    assert data['budget_goal']['income'] == 10000
    assert data['budget_goal']['planned_total'] == 9000
    assert data['budget_goal']['availableBefore'] == 1000
    assert Decimal(data['planning_profile']['income']) == 10000
    assert data['planning_profile']['expenses'] == {}
    # The model's deadline was never stated by the user, so no plan is offered or saved.
    assert data['proposal'] is None and data['plan'] is None
    from app.models.financial_plan import FinancialPlan
    assert db_session.query(FinancialPlan).count() == 0
    assert captured[1:] == history
    assert 'School fees' in captured[0]['content']
    assert 'Never substitute transaction totals' in captured[0]['content']
    assert "Never call the budget surplus 'current available funds'" in captured[0]['content']
    assert 'conditional monthly projection' in captured[0]['content']
    assert 'Do not repeat a budget summary' in captured[0]['content']
    assert 'including before budget setup' in captured[0]['content']
    assert 'Use past recorded months as reference' not in captured[0]['content']
    from app.models.budget_plan import BudgetPlan
    assert json.loads(db_session.query(BudgetPlan).first().percentages)['categories'][0]['amount'] == '5000'


def test_stale_choices_cleared_and_cny_projection(api_client, monkeypatch):
    headers = auth(api_client)
    saved = save_budget(api_client, headers)
    captured = []
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda messages: captured.extend(messages) or json.dumps({'reply': 'Advice', 'action': None, 'planning': None}))
    profile = {'goal': 'Vacation', 'goal_kind': 'savings', 'target_amount': 50000, 'current_amount': 0, 'deadline': '2090-01-01'}
    choices = {'targets': {'Entertainment': 2000}, 'protected': ['Rent'], 'fingerprint': fingerprint(saved)}
    body = {'messages': [{'role': 'user', 'content': 'Continue my goal'}], 'goal_planning': True, 'planning_profile': profile, 'budget_choices': choices, 'currency': 'CNY', 'aed_to_cny': 2}
    result = api_client.post('/ai/chat', headers=headers, json=body).json()
    assert result['budget_goal']['availableAfter'] == 2000
    context = json.loads(captured[0]['content'].split('Financial context follows as data:\n')[1])
    assert context['planning']['assessment']['availableAfter'] == 4000
    save_budget(api_client, headers, income=11000)
    result = api_client.post('/ai/chat', headers=headers, json=body).json()
    assert result['budget_goal']['accepted'] == []
    assert result['budget_goal']['availableBefore'] == 2000


def test_plain_model_response_still_returns_budget_metadata(api_client, monkeypatch):
    headers = auth(api_client)
    save_budget(api_client, headers)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: 'What amount and exact deadline are you targeting?')
    result = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'I want to save for a vacation'}]}).json()
    assert result['goal_planning'] and result['budget_goal']['missing'] == ['goal', 'target_amount', 'deadline']

@pytest.mark.parametrize('currency,rate,chosen', [('AED', None, 1000), ('CNY', 2, 2000)])
def test_chosen_monthly_savings_keeps_income_and_generates_reviewable_goal(api_client, monkeypatch, db_session, currency, rate, chosen):
    headers = auth(api_client)
    save_budget(api_client, headers)
    from app.services.budget_goals import deadline_for
    from app.models.financial_plan import FinancialPlan
    from app.models.income import MonthlyIncome
    target = 5000 if currency == 'AED' else 10000
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', lambda _: json.dumps({
        'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': target, 'monthly_contribution': chosen}))
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({
        'reply': f"I have set your monthly income to {chosen} {currency}.",
        'action': {'kind': 'income', 'amount': chosen}, 'planning': {'income': chosen}}))
    body = {'currency': currency, 'goal_planning': True,
        'planning_profile': {'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000},
        'messages': [{'role': 'user', 'content': f'I want to save {target} for an iPhone'},
            {'role': 'assistant', 'content': 'What monthly savings amount would you like?'},
            {'role': 'user', 'content': f'Lets go with {chosen} a month'}]}
    if rate:
        body['aed_to_cny'] = rate
    data = api_client.post('/ai/chat', headers=headers, json=body).json()
    assert data['plan']['monthlyContribution'] == 1000
    assert data['plan']['targetAmount'] == 5000
    assert data['plan']['months'] == 5
    assert Decimal(data['planning_profile']['income']) == 10000
    assert 'income to' not in data['reply']
    assert currency in data['reply']
    assert data['proposal'] is None
    assert db_session.query(MonthlyIncome).first().amount_cents == 1000000
    assert db_session.query(FinancialPlan).count() == 0
    today = datetime.now(timezone(timedelta(hours=4))).date()
    assert data['plan']['deadline'] == deadline_for(today, Decimal(5000), Decimal(1000))


def test_monthly_contribution_is_available_in_both_model_schemas(monkeypatch):
    from app.ai import client
    calls = []
    monkeypatch.setattr(client, 'generate_answer', lambda messages, schema=None, **kwargs: calls.append((messages, schema)) or '{}')
    client.generate_chat_reply([{'role': 'user', 'content': 'Lets go with 1k a month'}])
    client.extract_goal_facts([{'role': 'user', 'content': 'Lets go with 1k a month'}])
    assert 'monthly_contribution' in calls[0][1]['properties']['planning']['anyOf'][1]['properties']
    assert 'monthly_contribution' in calls[1][1]['properties']


def test_chosen_savings_above_surplus_has_no_approved_draft():
    data = assess({'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000, 'monthly_contribution': 1200}, budget(), TODAY)
    assert data['ready'] and data['requiredMonthly'] == 1200
    assert data['unfundedMonthly'] == 200 and not data['feasible']

@pytest.mark.parametrize('bad_reply', ["You already have a goal set to save 5000 AED.",
    "Since your surplus is AED 3013.86 available this month, you could save that entire amount this month."])
def test_unconfirmed_goal_and_projected_cash_are_not_claimed_as_saved(api_client, monkeypatch, bad_reply):
    headers = auth(api_client)
    save_budget(api_client, headers)
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', lambda _: json.dumps({
        'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000}))
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': bad_reply, 'action': None, 'planning': None}))
    data = api_client.post('/ai/chat', headers=headers, json={'goal_planning': True,
        'messages': [{'role': 'user', 'content': 'I want to save 5k for an iPhone'}]}).json()
    assert data['reply'] != bad_reply
    assert 'preferred monthly savings amount or target date' in data['reply']
    assert data['plan'] is None and data['proposal'] is None


def test_monthly_choice_from_main_reply_also_produces_draft(api_client, monkeypatch):
    headers = auth(api_client)
    save_budget(api_client, headers)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({
        'reply': 'We can review that monthly savings amount.', 'action': None,
        'planning': {'monthly_contribution': 1000, 'income': 1000}}))
    data = api_client.post('/ai/chat', headers=headers, json={'goal_planning': True,
        'planning_profile': {'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000},
        'messages': [{'role': 'user', 'content': 'I want to save 5000 for an iPhone'}, {'role': 'assistant', 'content': 'How much per month?'}, {'role': 'user', 'content': 'Lets go with 1k a month'}]}).json()
    assert data['plan']['monthlyContribution'] == 1000
    assert data['plan']['months'] == 5
    assert Decimal(data['planning_profile']['income']) == 10000
