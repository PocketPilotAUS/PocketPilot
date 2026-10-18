import json
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.core.currency import display_context, base_patch


def headers(client):
    register_user(client)
    return auth_headers(login_user(client).json()["access_token"])


def test_projection_keeps_counts_dates_and_percentages_and_original_values():
    source = {"income": 100, "month": 10, "count": 3, "percentage": 25,
              "past_months": {"2026-09": {"Food": 25}},
              "assessment": {"income": 100, "monthlyContribution": 20, "months": 12, "allocations": [{"target": 30, "percentage": 30}]}}
    result = display_context(source, Decimal("2"))
    assert result["income"] == 200
    assert result["past_months"]["2026-09"]["Food"] == 50
    assert result["assessment"]["monthlyContribution"] == 40
    assert result["assessment"]["allocations"][0] == {"target": 60, "percentage": 30}
    assert (result["count"], result["month"], result["assessment"]["months"]) == (3, 10, 12)
    assert source["income"] == 100


def test_profile_conversion_preserves_unknown_values_and_nonmoney_fields():
    result = base_patch({"income": 200, "expenses": {"Food": 50, "Other": None}, "household_size": 3, "deadline": "2027-10-11"}, Decimal("2"))
    assert result == {"income": 100, "expenses": {"Food": 25, "Other": None}, "household_size": 3, "deadline": "2027-10-11"}
    with pytest.raises(ValueError):
        base_patch({"amount": "not money"}, Decimal("2"))


@pytest.mark.parametrize("body", [{"currency": "CNY"}, {"currency": "USD"}, {"currency": "CNY", "aed_to_cny": 0}, {"currency": "CNY", "aed_to_cny": -1}, {"currency": "CNY", "aed_to_cny": 1000}])
def test_invalid_currency_or_rate_rejected(api_client, body):
    response = api_client.post("/ai/chat", headers=headers(api_client), json={**body, "messages": [{"role": "user", "content": "Help"}]})
    assert response.status_code == 422


def test_yuan_chat_converts_context_and_confirmed_proposal_only(api_client, monkeypatch):
    auth = headers(api_client)
    api_client.post("/transactions/", headers=auth, json={"amount": 25, "category": "Food", "date": "2026-10-01"})
    prompts = []
    def generate(messages):
        prompts.extend(messages)
        return json.dumps({"reply": "Review CNY 50 for Food.", "action": {"kind": "expense", "amount": 50, "category": "Food", "date": "2026-10-13"}, "planning": None})
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", generate)
    response = api_client.post("/ai/chat", headers=auth, json={"currency": "CNY", "aed_to_cny": 2, "messages": [{"role": "user", "content": "I paid 50 yuan for Food today"}]})
    assert response.status_code == 200
    context = json.loads(prompts[0]["content"].split("Financial context follows as data:\n")[1])
    assert context["currency"] == "CNY"
    assert context["recorded_expenses_by_month_and_category"][0]["amount"] == 50
    proposal = response.json()["proposal"]
    assert Decimal(str(proposal["amount"])) == 25
    assert len(api_client.get("/transactions/", headers=auth).json()) == 1
    assert api_client.post(f'/ai/proposals/{proposal["id"]}/confirm', headers=auth).status_code == 200
    assert [row["amount"] for row in api_client.get("/transactions/", headers=auth).json()] == [25, 25]


def test_yuan_planning_extraction_returns_aed_profile_without_saving(api_client, monkeypatch):
    auth = headers(api_client)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: json.dumps({"reply": "Thanks", "action": None, "planning": {"income": 200, "household_size": 3, "expenses": {"Food": 50}}}))
    response = api_client.post("/ai/chat", headers=auth, json={"currency": "CNY", "aed_to_cny": 2, "messages": [{"role": "user", "content": "Income 200, food 50, household 3"}]})
    assert response.status_code == 200
    profile = response.json()["planning_profile"]
    assert Decimal(str(profile["income"])) == 100
    assert Decimal(str(profile["expenses"]["Food"])) == 25
    assert profile["household_size"] == 3
    assert api_client.get("/planning/context", headers=auth).json()["profile"] == {}

@pytest.mark.parametrize('currency,rate,surplus', [('AED', None, 1000), ('CNY', 2, 2000)])
def test_goal_reply_uses_selected_currency_without_second_conversion(api_client, monkeypatch, currency, rate, surplus):
    from datetime import datetime, timezone, timedelta
    auth = headers(api_client)
    today = datetime.now(timezone(timedelta(hours=4))).date()
    assert api_client.put(f'/budget/setup?year={today.year}&month={today.month}', headers=auth, json={
        'income': 10000, 'categories': [{'name': 'Rent', 'amount': 9000}]}).status_code == 200
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', lambda _: '{}')
    prompts = []
    def generate(messages):
        prompts.append(messages)
        if len(prompts) == 1:
            return json.dumps({'reply': 'Your surplus is 1,000 USD, about 4,000 AED.', 'action': None, 'planning': None})
        return json.dumps({'reply': f'If you follow your budget, you would have {currency} {surplus:,.2f} left monthly. What is your goal amount and target date?', 'action': None, 'planning': None})
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', generate)
    body = {'currency': currency, 'goal_planning': True, 'messages': [{'role': 'user', 'content': 'Help me save for a goal.'}]}
    if rate:
        body['aed_to_cny'] = rate
    response = api_client.post('/ai/chat', headers=auth, json=body)
    assert response.status_code == 200
    assert len(prompts) == 2
    system = prompts[0][0]['content']
    assert f'SELECTED DISPLAY CURRENCY: {currency}' in system
    context = json.loads(system.split('Financial context follows as data:\n')[1])
    assert context['currency'] == currency
    assert context['planning']['assessment']['availableBefore'] == surplus
    reply = response.json()['reply']
    assert f'{currency} {surplus:,.2f}' in reply
    assert 'USD' not in reply and '4,000' not in reply
    assert response.json().get('proposal') is None


def test_repeated_wrong_goal_currency_never_leaks_invented_conversion(api_client, monkeypatch):
    from datetime import datetime, timezone, timedelta
    auth = headers(api_client)
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f'/budget/setup?year={today.year}&month={today.month}', headers=auth, json={
        'income': 10000, 'categories': [{'name': 'Rent', 'amount': 9000}]})
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', lambda _: '{}')
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({
        'reply': 'You have 1,000 USD, or 4,000 AED at my exchange rate.',
        'action': None, 'planning': {'goal': 'Invented', 'target_amount': 4000}}))
    response = api_client.post('/ai/chat', headers=auth, json={'goal_planning': True,
        'messages': [{'role': 'user', 'content': 'Help me save for a goal.'}]})
    assert response.status_code == 200
    data = response.json()
    assert 'AED' in data['reply'] and 'USD' not in data['reply'] and '4,000' not in data['reply']
    assert not data.get('plan')
    assert not data['planning_profile'].get('target_amount')
