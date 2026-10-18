"""Mocked-model contracts for financial workflow boundaries; real API and database."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction
from app.models.income import MonthlyIncome
from app.models.debt_payment import DebtPayment
from app.models.financial_plan import FinancialPlan
from app.services.chat_record_drafts import RecordDraft, seal_draft
from app.services.debt_planning import seal, unseal
from app.services.chat_followups import standalone_amount


def decision(intent="read", topic="budget", **fields):
    return dict(intent=intent,topic=topic,continuation=False,kind=None,amount_text=None,
        category_text=None,category=None,clarification=None) | fields


@pytest.fixture
def topics(api_client, monkeypatch):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}",headers=headers,json={"income":10000,
        "categories":[{"name":"Rent","amount":5000},{"name":"Food","amount":1420}]})
    loan = api_client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60}).json()
    selected, calls = [decision()], []
    def interpret(messages, context):
        calls.append((messages,context))
        return json.dumps(selected[0])
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",interpret)
    monkeypatch.setattr("app.services.debt_planning.interpret_debt_turn",lambda *_: json.dumps({"intent":"discuss"}))
    monkeypatch.setattr("app.services.debt_planning.generate_chat_reply",lambda *_: json.dumps({"reply":"What total monthly payment would you like to check?","action":None,"planning":None}))
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_: json.dumps({"reply":"Here is the read-only answer.","action":None,"planning":None}))
    def ask(text, history=(), **fields):
        response = api_client.post("/ai/chat",headers=headers,json={"messages":[*history,
            {"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"}],**fields})
        assert response.status_code == 200, response.text
        return response.json()
    return headers, today, loan, selected, calls, ask


def assert_no_action(data):
    assert data["record_state"] is None and data["debt_state"] is None
    assert data["planning_profile"] is None and not data["goal_planning"]
    assert data["proposal"] is None and data["plan"] is None


def test_exact_four_turn_t2_does_not_create_income_state(topics, db_session):
    _, _, _, selected, calls, ask = topics
    history, carried = [], {}
    for index,text in enumerate(["I wanna pay off my car loan faster.","How's my budget looking?","What's my monthly income?","800"]):
        selected[0] = decision("plan","debt") if index == 0 else decision("read",continuation=True)
        if index == 3:
            selected[0] = decision("record",kind="income",income_operation="add",amount_text="800")
        data = ask(text,history,**carried)
        if index == 0:
            assert data["debt_state"]
        else:
            assert_no_action(data)
        history.extend([{"role":"user","content":text},{"role":"assistant","content":data["reply"]}])
        carried = {key:data.get(key) for key in ("record_state","debt_state","planning_profile","goal_planning")}
    assert "AED 800.00 refer to" in data["reply"]
    assert len(calls) == 3  # The unsafe numeric turn does not reach the model.
    assert db_session.query(ChatProposal).count() == db_session.query(Transaction).count() == db_session.query(DebtPayment).count() == db_session.query(FinancialPlan).count() == 0
    assert db_session.query(MonthlyIncome).filter_by(user_id=1).one().amount_cents == 1000000


@pytest.mark.parametrize("lookup", ["What's my monthly income?","How much have I spent on food?","What's my car loan balance?","How's my budget looking?"])
@pytest.mark.parametrize("text", ["800","2k","1,500.50","AED 800","800 CNY"])
@pytest.mark.parametrize("continuation", [True,False])
def test_numeric_turn_after_lookup_is_ambiguous_even_if_model_would_record(topics, lookup, text, continuation):
    _, _, _, selected, calls, ask = topics
    first = ask(lookup)
    selected[0] = decision("record",kind="income",income_operation="add",amount_text="800",continuation=continuation)
    data = ask(text,[{"role":"user","content":lookup},{"role":"assistant","content":first["reply"]}])
    assert "refer to" in data["reply"] and len(calls) == 1
    assert_no_action(data)


@pytest.mark.parametrize("kind", ["expense","income"])
def test_numeric_answer_completes_explicit_record_amount_question(topics, kind, db_session):
    _, _, _, selected, calls, ask = topics
    selected[0] = decision("record",kind=kind,category_text="lunch" if kind=="expense" else None,
        category="Food" if kind=="expense" else None,income_operation="add" if kind=="income" else None)
    text = "I paid for lunch today." if kind=="expense" else "I got paid yesterday."
    first = ask(text)
    assert first["record_state"] and "How much" in first["reply"]
    selected[0] = decision("record",kind="income",amount_text="999",income_operation="add")
    data = ask("800",[{"role":"user","content":text},{"role":"assistant","content":first["reply"]}],record_state=first["record_state"])
    assert data["proposal"]["kind"] == kind and Decimal(data["proposal"]["amount"]) == 800
    assert data["proposal"]["status"] == "pending" and len(calls) == 1
    assert db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("kind", ["expense","income"])
def test_lookup_retires_incomplete_record_and_ignores_numeric_followup(topics, db_session, api_client, kind):
    headers, _, _, selected, _, ask = topics
    draft = RecordDraft(kind=kind,source="I paid 50 Food" if kind=="expense" else "I earned 50",
        amount_text="50",category="Food" if kind=="expense" else None,category_text="Food" if kind=="expense" else None,
        income_operation="add" if kind=="income" else None,currency="AED")
    token = seal_draft(draft,1)
    selected[0] = decision("read",continuation=True)
    data = ask("What's my monthly income?",record_state=token)
    assert_no_action(data)
    history=[{"role":"user","content":"What's my monthly income?"},{"role":"assistant","content":data["reply"]}]
    assert_no_action(ask("800",history))
    replay = api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Today"}],"record_state":token})
    assert replay.status_code == 422 and db_session.query(Transaction).count() == 0


def test_valid_numeric_savings_answer_retains_target_and_cannot_become_income(topics, monkeypatch):
    _, _, _, selected, _, ask = topics
    selected[0] = decision("record",kind="income",income_operation="add",amount_text="800")
    monkeypatch.setattr("app.routers.chat.extract_goal_facts",lambda *_: json.dumps({"goal":"iPhone","target_amount":800,"monthly_contribution":800}))
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_: json.dumps({"reply":"Review","action":None,
        "planning":{"goal":"Laptop","target_amount":800,"monthly_contribution":800}}))
    data = ask("800",history=[{"role":"user","content":"I wanna save 5k for a laptop."},
        {"role":"assistant","content":"How much would you like to save each month?"}],
        goal_planning=True,planning_profile={"goal":"Laptop","goal_kind":"savings","target_amount":5000})
    assert data["proposal"] is None and data["plan"]["targetAmount"] == 5000 and data["plan"]["monthlyContribution"] == 800


def test_valid_numeric_debt_payment_answer_uses_signed_context(topics):
    _, _, loan, selected, _, ask = topics
    selected[0] = decision("record",kind="income",income_operation="add",amount_text="800")
    token = seal({"debt_ids":[loan["id"]],"phase":"discuss"},1,"debt_conversation")
    data = ask("800",history=[{"role":"user","content":"I wanna pay off my car loan faster."},
        {"role":"assistant","content":"What total monthly payment would you like to check?"}],debt_state=token)
    state = unseal(data["debt_state"],1,"debt_conversation")
    assert state["chosen"] == 800 and state["debt_ids"] == [loan["id"]]
    assert data["proposal"] is None and data["plan"] is None and data["record_state"] is None


def test_read_lookup_clears_stale_goal_even_when_model_marks_continuation(topics):
    _, _, _, selected, _, ask = topics
    selected[0] = decision("read",continuation=True)
    data = ask("What's my income?",goal_planning=True,planning_profile={"goal":"Laptop","target_amount":5000})
    assert_no_action(data)


def test_foreign_debt_state_cannot_supply_numeric_meaning(topics, api_client, db_session):
    _, _, loan, _, _, _ = topics
    token = seal({"debt_ids":[loan["id"]],"phase":"discuss"},1,"debt_conversation")
    register_user(api_client,email="other@example.com")
    other = auth_headers(login_user(api_client,email="other@example.com").json()["access_token"])
    response = api_client.post("/ai/chat",headers=other,json={"messages":[
        {"role":"user","content":"Help with my loan"},{"role":"assistant","content":"What monthly payment?"},
        {"role":"user","content":"800"}],"debt_state":token})
    assert response.status_code == 422 and db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("text", ["800","2k","AED 800","800 CNY","1,500.50"])
def test_amount_only_detection_ignores_mobile_metadata(text):
    assert standalone_amount(text+chr(10)+"[Currency for untagged amounts in this message: AED]") is not None


@pytest.mark.parametrize("text", ["0", "800 CNY"])
def test_amount_cannot_supply_invalid_or_different_currency_plan_field(topics, text):
    _, _, loan, _, calls, ask = topics
    token = seal({"debt_ids":[loan["id"]],"phase":"discuss"},1,"debt_conversation")
    data = ask(text,history=[{"role":"user","content":"Help me pay my car loan faster"},
        {"role":"assistant","content":"What total monthly payment would you like to check?"}],debt_state=token)
    assert_no_action(data)
    assert "refer to" in data["reply"] and not calls
    if "CNY" in text:
        assert "CNY 800" in data["reply"]


def test_expired_debt_state_cannot_supply_amount_meaning(topics, api_client):
    import jwt
    from app.core.config import get_jwt_secret_key, JWT_ALGORITHM
    headers, _, loan, _, _, _ = topics
    token = seal({"debt_ids":[loan["id"]],"phase":"discuss"},1,"debt_conversation")
    payload = jwt.decode(token,get_jwt_secret_key(),algorithms=[JWT_ALGORITHM])
    payload["exp"] = 1
    token = jwt.encode(payload,get_jwt_secret_key(),algorithm=JWT_ALGORITHM)
    result = api_client.post("/ai/chat",headers=headers,json={"messages":[
        {"role":"user","content":"Help with my car loan"},{"role":"assistant","content":"What monthly payment?"},
        {"role":"user","content":"800"}],"debt_state":token})
    assert result.status_code == 422
