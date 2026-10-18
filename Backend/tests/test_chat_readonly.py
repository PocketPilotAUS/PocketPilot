import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.chat_proposal import ChatProposal
from app.models.financial_plan import FinancialPlan
from app.models.savings import ManualSavings, MonthlySavings
from app.models.user import User


def account(client, email="alice@example.com"):
    assert register_user(client, email=email).status_code == 201
    return auth_headers(login_user(client, email=email).json()["access_token"])


def setup(client, headers):
    now = datetime.now(timezone(timedelta(hours=4))).date()
    response = client.put(f"/budget/setup?year={now.year}&month={now.month}", headers=headers, json={
        "income": 10000, "categories": [{"name": "Rent", "amount": 5000}, {"name": "Food", "amount": 1220}]})
    assert response.status_code == 200
    return now


def mock_reply(monkeypatch, action, answer="Your recorded spending is AED 25.00.", planning=None):
    captured = []
    def reply(messages):
        captured.extend(messages)
        return json.dumps({"reply": answer, "action": action, "planning": planning})
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", reply)
    return captured


def ask(client, headers, text, **extra):
    response = client.post("/ai/chat", headers=headers, json={
        "messages": [{"role": "user", "content": text}], "require_budget": True, **extra})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("text", [
    "What is my monthly income and how much have I budgeted for expenses?",
    "Show my saved monthly income and my planned expense budget.",
])
@pytest.mark.parametrize("action", [None, {"kind": "income", "amount": 99999},
    {"kind": "income", "amount": 99999, "year": 2026, "month": 10}])
def test_verified_income_budget_lookup(api_client, monkeypatch, db_session, text, action):
    headers = account(api_client)
    setup(api_client, headers)
    mock_reply(monkeypatch, action, "Your income is AED 99999.")
    result = ask(api_client, headers, text)
    assert "10,000.00" in result["reply"] and "6,220.00" in result["reply"]
    assert "99999" not in result["reply"]
    assert result["proposal"] is None and result["plan"] is None
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("text", [
    "How much have I spent this month?", "What are my debts?",
    "How much have I saved?", "What are my savings goals?",
    "What income did I record?", "Can you show my recorded expenses?",
    "What did I pay for Food today?",
])
@pytest.mark.parametrize("action", [None, {"kind": "expense", "amount": 25},
    {"kind": "expense", "amount": 25, "category": "Food", "date": "2026-10-17"}])
def test_readonly_preserves_answer_and_ignores_actions(api_client, monkeypatch, db_session, text, action):
    headers = account(api_client)
    setup(api_client, headers)
    answer = "Here are your verified records."
    mock_reply(monkeypatch, action, answer, planning={"goal": "Invented", "target_amount": 1})
    result = ask(api_client, headers, text, goal_planning=True)
    if "income" in text.lower():
        assert "10,000.00" in result["reply"]
    else:
        assert result["reply"] == answer
    assert result["proposal"] is None and result["plan"] is None
    assert db_session.query(ChatProposal).count() == 0


def test_missing_records_are_unknown_not_zero(api_client, monkeypatch):
    headers = account(api_client)
    mock_reply(monkeypatch, None)
    result = ask(api_client, headers, "What is my monthly income and expense budget?")
    assert "No monthly income is saved" in result["reply"]
    assert "No complete expense budget is saved" in result["reply"]
    assert result["budget_required"] is False


@pytest.mark.parametrize("text,action", [
    ("Record my income as AED 8000 this month", {"kind": "income", "amount": 8000, "year": 2026, "month": 10}),
    ("I paid AED 25 for Food today", {"kind": "expense", "amount": 25, "category": "Food", "date": "2026-10-17"}),
])
def test_recording_still_requires_confirmation(api_client, monkeypatch, db_session, text, action):
    headers = account(api_client)
    setup(api_client, headers)
    mock_reply(monkeypatch, action, "Please confirm.")
    result = ask(api_client, headers, text)
    assert result["proposal"]["status"] == "pending"
    assert db_session.query(ChatProposal).count() == 1
    # Applying it still requires the existing confirmation endpoint.


@pytest.mark.parametrize("text,action", [
    ("Income", {"kind": "income", "amount": 8000, "year": 2026, "month": 10}),
    ("Record income", {"kind": "income", "amount": 8000, "year": 2026, "month": 10}),
    ("Record an expense of AED 25 for Food", {"kind": "expense", "amount": 25}),
    ("If I paid 25 for Food, what would happen?", {"kind": "expense", "amount": 25, "category": "Food", "date": "2026-10-17"}),
])
def test_ambiguous_or_incomplete_actions_require_clarification(api_client, monkeypatch, db_session, text, action):
    headers = account(api_client)
    setup(api_client, headers)
    mock_reply(monkeypatch, action, "An answer.")
    result = ask(api_client, headers, text)
    assert result["proposal"] is None
    assert db_session.query(ChatProposal).count() == 0
    assert "clarify" in result["reply"] or "specify" in result["reply"] or "asking" in result["reply"] or text.endswith("?")


def test_financial_context_is_scoped_and_distinguishes_contributions(api_client, monkeypatch, db_session):
    alice = account(api_client)
    bob = account(api_client, "bob@example.com")
    for headers, name, balance in [(alice, "Alice car", 12000), (bob, "PrivateBob", 90000)]:
        setup(api_client, headers)
        assert api_client.post("/debts", headers=headers, json={
            "name": name, "balance": balance, "annual_rate": 0, "remaining_months": 12}).status_code == 201
    for email, title, amount in [("alice@example.com", "Alice goal", 200), ("bob@example.com", "PrivateBobGoal", 999)]:
        user = db_session.query(User).filter_by(email=email).one()
        plan_id = str(uuid4())
        db_session.add(FinancialPlan(id=plan_id, user_id=user.id, payload=json.dumps({
            "kind": "savings", "title": title, "targetAmount": 5000, "savedAmount": 100,
            "monthlyContribution": 500, "deadline": "2090-01-01"})))
        db_session.add(ManualSavings(user_id=user.id, label="Contribution", amount_cents=amount * 100,
            request_key=str(uuid4()), goal_id=plan_id))
        db_session.add(MonthlySavings(user_id=user.id, year=2020, month=1,
            income_cents=100000, spent_cents=90000, extra_debt_cents=0, saved_cents=10000))
    db_session.commit()
    captured = mock_reply(monkeypatch, {"kind": "income", "amount": 1}, "Here are your debts and goals.")
    result = ask(api_client, alice, "Show my debts and savings goals")
    assert result["proposal"] is None
    context = json.loads(captured[0]["content"].split("Financial context follows as data:\n")[1])
    records = context["financial_records"]
    assert records["debts"] == [{"name": "Alice car", "amount": 12000, "monthlyContribution": 1000, "next_due": None}]
    assert records["savings"]["total_recorded"]["amount"] == 300
    goal = records["savings"]["goals"][0]
    assert goal["savedAmount"] == 300 and goal["current_amount"] == 100 and goal["amount"] == 200
    assert goal["monthlyContribution"] == 500
    assert context["saved_monthly_budget"]["budget"]["planned_total"] == 7220
    assert "PrivateBob" not in captured[0]["content"]
    assert "Not stored by the app" not in captured[0]["content"]
    assert "not a live bank balance" in records["meaning"]
    assert "read-only" in captured[0]["content"]


def test_cny_context_converts_new_financial_amounts(api_client, monkeypatch):
    headers = account(api_client)
    setup(api_client, headers)
    api_client.post("/debts", headers=headers, json={
        "name": "Car", "balance": 12000, "annual_rate": 0, "remaining_months": 12})
    captured = mock_reply(monkeypatch, None, "Your debt is CNY 24000.")
    ask(api_client, headers, "Show my debts", currency="CNY", aed_to_cny=2)
    context = json.loads(captured[0]["content"].split("Financial context follows as data:\n")[1])
    assert context["financial_records"]["debts"][0]["amount"] == 24000
    assert context["financial_records"]["debts"][0]["monthlyContribution"] == 2000


def test_recording_clarification_followup(api_client, monkeypatch, db_session):
    headers = account(api_client)
    setup(api_client, headers)
    mock_reply(monkeypatch, {"kind": "expense", "amount": 25, "category": "Food", "date": "2026-10-17"})
    response = api_client.post("/ai/chat", headers=headers, json={"messages": [
        {"role": "user", "content": "Record a Food expense"},
        {"role": "assistant", "content": "How much did you pay and when?"},
        {"role": "user", "content": "25 today"},
    ]})
    assert response.status_code == 200
    assert response.json()["proposal"]["kind"] == "expense"
    assert db_session.query(ChatProposal).count() == 1


def test_query_followup_cannot_turn_into_recording(api_client, monkeypatch, db_session):
    headers = account(api_client)
    setup(api_client, headers)
    mock_reply(monkeypatch, {"kind": "expense", "amount": 25, "category": "Food", "date": "2026-10-17"})
    response = api_client.post("/ai/chat", headers=headers, json={"messages": [
        {"role": "user", "content": "What did I pay for Food?"},
        {"role": "assistant", "content": "Which day?"},
        {"role": "user", "content": "25 today"},
    ]})
    assert response.status_code == 200
    assert response.json()["proposal"] is None
    assert db_session.query(ChatProposal).count() == 0


def test_readonly_after_reject_does_not_save_or_recreate_plan(api_client, monkeypatch, db_session):
    headers = account(api_client)
    setup(api_client, headers)
    mock_reply(monkeypatch, {"kind": "income", "amount": 10000, "year": 2026, "month": 10},
               "Here are your savings goals.", planning={"goal": "Vacation", "goal_kind": "savings",
                   "target_amount": 5000, "deadline": "2090-01-01"})
    result = ask(api_client, headers, "What are my savings goals?", goal_planning=True,
                 budget_draft_status="declined")
    assert result["proposal"] is None and result["plan"] is None
    assert db_session.query(FinancialPlan).count() == 0


def test_direct_lookup_includes_debt_and_converts_currency(api_client, monkeypatch):
    headers = account(api_client)
    setup(api_client, headers)
    api_client.post("/debts", headers=headers, json={
        "name": "Car", "balance": 12000, "annual_rate": 0, "remaining_months": 12})
    mock_reply(monkeypatch, {"kind": "income", "amount": 1}, "Wrong amounts.")
    result = ask(api_client, headers, "What is my monthly income and budget?", currency="CNY", aed_to_cny=2)
    assert "20,000.00" in result["reply"] and "14,440.00" in result["reply"]
    assert result["proposal"] is None


@pytest.mark.parametrize("text,expected", [
    ("What did I pay for Food today?", "read"),
    ("Can you record AED 25 for Food today?", "record"),
    ("Could you add AED 25 for Food today?", "record"),
    ("How can I create a financial plan?", "plan"),
    ("Please help me save for a vacation", "plan"),
    ("If I paid AED 25 for Food, what would happen?", "read"),
    ("Do not record anything, show my income", "read"),
    ("Something about income", "ambiguous"),
])
def test_intent_boundaries(text, expected):
    from app.routers.chat import Message
    from app.services.chat_context import intent
    assert intent([Message(role="user", content=text)]) == expected


@pytest.mark.parametrize("action", [None, {"kind": "expense", "amount": 566.14},
    {"kind": "expense", "amount": 566.14, "category": "Debt", "date": "2026-10-18"}])
def test_debt_plan_keeps_advice_and_ignores_transaction_action(api_client, monkeypatch, db_session, action):
    headers = account(api_client)
    setup(api_client, headers)
    created = api_client.post("/debts", headers=headers, json={
        "name": "Car loan", "balance": 12000, "annual_rate": 0, "remaining_months": 12})
    assert created.status_code == 201
    monkeypatch.setattr("app.routers.chat.extract_goal_facts", lambda _: "{}")
    monkeypatch.setattr('app.services.debt_planning.interpret_debt_turn', lambda *_: json.dumps({'intent':'discuss'}))
    monkeypatch.setattr('app.services.debt_planning.generate_chat_reply', lambda *_: (_ for _ in ()).throw(ValueError('Exercise fallback')))
    answer = "Your Car loan has AED 12,000 left and a monthly payment of AED 1,000. How much extra could you comfortably pay each month?"
    captured = mock_reply(monkeypatch, action, answer)
    result = ask(api_client, headers, "Help me make a plan to pay off my debt faster.")
    assert "saved budget" in result["reply"]
    assert "AED 12,000.00" in result["reply"]
    assert "AED 1,000.00" in result["reply"]
    assert result["proposal"] is None and result["plan"] is None
    assert db_session.query(ChatProposal).count() == 0
    assert db_session.query(FinancialPlan).count() == 0
    assert captured == []
    assert api_client.get("/transactions/", headers=headers).json() == []
