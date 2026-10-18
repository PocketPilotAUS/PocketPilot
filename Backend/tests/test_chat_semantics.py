"""Mocked semantic-model contract tests; these do NOT measure live model NLU."""
import json
from datetime import date
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction
from app.routers.chat import Message
from app.routers.proposals import ProposedAction
from app.services.chat_interpretation import ChatInterpretation
from app.services.chat_records import normalize_action


def interpretation(intent="read", topic="general", **values):
    return dict(intent=intent, topic=topic, continuation=False, kind=None,
                amount_text=None, category_text=None, category=None, clarification=None, **{}) | values


@pytest.fixture
def headers(api_client):
    register_user(api_client)
    return auth_headers(login_user(api_client).json()["access_token"])


def mock_models(monkeypatch, semantic, action=None, planning=None, reply="Here is the answer."):
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", lambda *_: json.dumps(semantic))
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda *_: json.dumps(
        dict(reply=reply, action=action, planning=planning)))


@pytest.mark.parametrize("text", [
    "Spent 50 on lunch.", "Lunch was 50.", "Can you add the 50 I paid for lunch?",
    "paid 50 lunch", "lunch cost me 50",
])
def test_expense_paraphrases_missing_date_ask_without_guessing(api_client, monkeypatch, headers, db_session, text):
    semantic = interpretation("record", kind="expense", amount_text="50", category_text="lunch", category="Food",
                              clarification="When did you pay for lunch?")
    mock_models(monkeypatch, semantic, {"kind": "expense", "amount": 50, "category": "Food", "date": "2090-01-01"})
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]}).json()
    assert data["proposal"] is None and "When did you pay" in data["reply"]
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("text,amount,description,category", [
    ("Lunch was 50 today", 50, "Lunch", "Food"),
    ("Spent 50 on lunch yesterday", 50, "lunch", "Food"),
    ("Can you add the 50 I paid for lunch today?", 50, "lunch", "Food"),
    ("I just bought groceries for 120 today", 120, "groceries", "Groceries"),
    ("groceries were 120 yesterday", 120, "groceries", "Groceries"),
])
def test_expense_paraphrases_create_only_pending_proposal(api_client, monkeypatch, headers, db_session, text, amount, description, category):
    mock_models(monkeypatch, interpretation("record", kind="expense", amount_text=str(amount),
        category_text=description, category=category), {"kind": "expense", "amount": amount, "category": category})
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]}).json()
    assert data["proposal"]["status"] == "pending"
    assert data["proposal"]["amount"] == str(amount)
    assert db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("text", ["I earned 2k yesterday.", "got paid 2k yesterday", "my pay came in yesterday 2k"])
def test_income_shorthand_and_relative_date(api_client, monkeypatch, headers, db_session, text):
    mock_models(monkeypatch, interpretation("record", kind="income", amount_text="2k", income_operation="add"), {"kind": "income", "amount": 2000})
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]}).json()
    assert data["proposal"]["kind"] == "income" and data["proposal"]["status"] == "pending"
    assert "one-time income receipt" in data["reply"] and data["proposal"]["income_operation"] == "add"


@pytest.mark.parametrize("text", [
    "How much have I spent on food?", "food spending pls", "What's my income?", "income total pls",
    "Forget the loan for now, how's my budget?", "budget looking ok", "Explain how debt payments work.",
    "What if I spent 500 on groceries?", "How would recording 2,000 income affect my budget?",
    "I might buy a laptop.", "I don't want to record this expense.", "what is compound interest",
])
def test_readonly_and_nonactions_ignore_model_actions(api_client, monkeypatch, headers, db_session, text):
    mock_models(monkeypatch, interpretation(), {"kind": "income", "amount": 2000}, {"goal": "Fake", "target_amount": 1})
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}],
        "require_budget": True, "goal_planning": True, "planning_profile": {"goal": "Old", "target_amount": 5000}}).json()
    assert data["proposal"] is None and data["plan"] is None
    assert data["planning_profile"] is None and not data["goal_planning"]
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("text", ["income", "800", "do it", "something about my money"])
def test_ambiguity_has_targeted_clarification(api_client, monkeypatch, headers, text):
    mock_models(monkeypatch, interpretation("clarify", clarification="Do you want to view income or set this month's income?"))
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]}).json()
    assert data["reply"].startswith("What does" if text == "800" else "Do you want") and data["proposal"] is None


@pytest.mark.parametrize("text,patch", [
    ("What can I afford to save?", {}), ("I wanna save 5k for a laptop.", {"goal": "Laptop", "target_amount": 5000}),
    ("Can I do 800 monthly?", {"monthly_contribution": 800}), ("What about 600 instead?", {"monthly_contribution": 600}),
    ("Can I save more without changing my rent budget?", {})])
def test_savings_paraphrases_reach_budget_goal_flow(api_client, monkeypatch, headers, text, patch):
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers,
        json={"income": 10000, "categories": [{"name": "Rent", "amount": 4000}]})
    mock_models(monkeypatch, interpretation("plan", "savings", continuation=True),
        {"kind": "income", "amount": 800}, {**patch, "protected_categories": ["Rent"]})
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}],
        "planning_profile": {"goal": "Laptop", "goal_kind": "savings", "target_amount": 5000}}).json()
    assert data["goal_planning"] and data["proposal"] is None
    assert "Rent" in data["budget_goal"]["protected"]


@pytest.mark.parametrize("text", ["I need to clear my car loan sooner.", "Could I finish paying it in two years?", "Actually, let's do three."])
def test_debt_paraphrases_reach_verified_calculator(api_client, monkeypatch, headers, text):
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers,
        json={"income": 10000, "categories": [{"name": "Rent", "amount": 4000}]})
    mock_models(monkeypatch, interpretation("plan", "debt", continuation=True))
    calls = []
    def debt_turn(*args):
        calls.append(args)
        return {"reply": "Verified debt discussion", "debt_state": "signed"}
    monkeypatch.setattr("app.services.debt_planning.turn", debt_turn)
    data = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]}).json()
    assert len(calls) == 1 and data["reply"] == "Verified debt discussion"
    assert data["proposal"] is None


@pytest.mark.parametrize("text,token,amount", [
    ("Lunch was 50 today", "50", 500), ("Lunch was 50 today", "500", 500),
    ("Lunch on 2026-10-18", "2026", 2026), ("Lunch 50 or 25 today", "50", 50),
    ("What if I spent 500 on lunch today", "500", 500),
    ("I don't want to record 50 lunch today", "50", 50),
    ("yes", "50", 50),
])
def test_bad_semantic_evidence_fails_closed(text, token, amount):
    semantic = ChatInterpretation.model_validate(interpretation("record", kind="expense", amount_text=token,
        category_text="Lunch", category="Food", continuation=True))
    messages = [Message(role="user", content="Lunch was 50 today"), Message(role="assistant", content="Confirm?"), Message(role="user", content=text)]
    assert not semantic.supports(messages, ProposedAction(kind="expense", amount=amount, category="Food", date=date(2026,10,18)))


def test_income_yesterday_at_month_boundary():
    result = normalize_action({"kind": "income", "amount": 2000}, [Message(role="user", content="earned 2k yesterday")], date(2026,1,1))
    assert (result["year"], result["month"]) == (2025,12)


def test_invented_semantic_description_is_clarified_before_reply_generation(api_client, monkeypatch, headers, db_session):
    mock_models(monkeypatch, interpretation("record", kind="expense", amount_text="800", category_text="lunch",
        category="Food", clarification="When did you pay for lunch?"))
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": "800"}]}).json()
    assert "lunch" not in result["reply"] and "refer to" in result["reply"]
    assert result["proposal"] is None and db_session.query(ChatProposal).count() == 0


def test_model_cannot_invent_goal_amount(api_client, monkeypatch, headers):
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers,
        json={"income": 10000, "categories": [{"name": "Rent", "amount": 4000}]})
    mock_models(monkeypatch, interpretation("plan", "savings"), planning={"goal": "Laptop", "target_amount": 98765, "monthly_contribution": 4321})
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": "I want to save for a laptop"}]}).json()
    assert result["plan"] is None
    assert result["planning_profile"]["target_amount"] is None
    assert result["planning_profile"]["monthly_contribution"] is None


@pytest.mark.parametrize("text,token,category_text", [
    ("Record Food and Shopping 50 today", "50", "Food"),
    ("Food on October 17, 2026", "17", "Food"),
])
def test_semantic_evidence_rejects_category_conflicts_and_natural_date_numbers(text, token, category_text):
    semantic = ChatInterpretation.model_validate(interpretation("record", kind="expense", amount_text=token,
        category_text=category_text, category="Food"))
    assert not semantic.supports([Message(role="user", content=text)],
        ProposedAction(kind="expense", amount=int(token), category="Food", date=date(2026,10,18)))


def test_monthly_savings_cannot_be_proposed_as_income(api_client, monkeypatch, headers):
    mock_models(monkeypatch, interpretation("record", kind="income", amount_text="800", continuation=True),
                {"kind": "income", "amount": 800})
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [
        {"role": "user", "content": "I want to save for a laptop"},
        {"role": "assistant", "content": "How much would you like to save monthly?"},
        {"role": "user", "content": "800 monthly"}], "goal_planning": True}).json()
    assert result["proposal"] is None and "savings contribution" in result["reply"]


def test_goal_narrative_cannot_invent_a_monthly_contribution(api_client, monkeypatch, headers):
    from datetime import datetime, timedelta, timezone
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers,
        json={"income": 10000, "categories": [{"name": "Rent", "amount": 4000}]})
    mock_models(monkeypatch, interpretation("plan", "savings"), planning={"goal": "Laptop", "target_amount": 5000},
                reply="You should save AED 777 each month.")
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": "I wanna save 5k for a laptop"}]}).json()
    assert "777" not in result["reply"]
    assert result["plan"] is None and result["proposal"] is None


def test_live_discovered_numeric_followup_to_income_lookup_is_not_recording(api_client, monkeypatch, headers, db_session):
    mock_models(monkeypatch, interpretation("record", kind="income", amount_text="800", continuation=True),
                {"kind": "income", "amount": 800})
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [
        {"role": "user", "content": "Forget the laptop for now, what's my income?"},
        {"role": "assistant", "content": "Your saved income is AED 10000."},
        {"role": "user", "content": "800"}]}).json()
    assert result["proposal"] is None and "refer to" in result["reply"]
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("text", ["put 200 into my laptop savings", "erase that purchase please"])
def test_unsupported_actions_offer_relevant_app_guidance(api_client, monkeypatch, headers, db_session, text):
    mock_models(monkeypatch, interpretation("unsupported", clarification="Use Savings or Transactions to make that change. Nothing has been saved."))
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": text}]}).json()
    assert "Use Savings or Transactions" in result["reply"]
    assert result["proposal"] is None and result["plan"] is None
    assert db_session.query(ChatProposal).count() == 0


def test_semantic_date_followup_keeps_only_current_expense(api_client, monkeypatch, headers):
    mock_models(monkeypatch, interpretation("record", kind="expense", amount_text="50", category_text="lunch", category="Food", continuation=True),
                {"kind": "expense", "amount": 50, "category": "Food"})
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [
        {"role": "user", "content": "lunch was 50"}, {"role": "assistant", "content": "When did you pay?"},
        {"role": "user", "content": "today"}]}).json()
    assert result["proposal"]["status"] == "pending" and result["proposal"]["category"] == "Food"


def test_semantic_currency_is_converted_only_after_evidence_validation(api_client, monkeypatch, headers):
    mock_models(monkeypatch, interpretation("record", kind="expense", amount_text="50", category_text="lunch", category="Food"),
                {"kind": "expense", "amount": 50, "category": "Food"})
    result = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": "lunch was 50 today"}],
        "currency": "CNY", "aed_to_cny": 2}).json()
    assert Decimal(result["proposal"]["amount"]) == Decimal("25")
    assert "CNY 50.00" in result["reply"]
