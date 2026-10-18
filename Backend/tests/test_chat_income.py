"""Mocked semantic interpretation; real shared draft, budget, and confirmation operations."""
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.income import MonthlyIncome
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction
from app.services.chat_record_drafts import load_draft

TODAY = date(2026, 10, 18)


def semantic(**fields):
    return dict(intent="record", topic="budget", continuation=False, kind="income", amount_text="2k",
        category_text=None, category=None, clarification=None, income_operation="add") | fields


@pytest.fixture
def income_chat(api_client, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = cls(2026, 10, 18, 1, tzinfo=timezone(timedelta(hours=4)))
            return instant.astimezone(tz) if tz else instant
    monkeypatch.setattr("app.routers.chat.datetime", Clock)
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    assert api_client.put("/budget/setup?year=2026&month=10", headers=headers, json={
        "income": 10000, "categories": [{"name": "Rent", "amount": 5000}, {"name": "Food", "amount": 1420}]}).status_code == 200
    decision, calls = [semantic()], []
    def interpret(messages, context):
        calls.append((messages, context))
        return json.dumps(decision[0])
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", interpret)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda *_: json.dumps({"reply": "No changes.", "action": {"kind": "income", "amount": 99999}, "planning": None}))
    def ask(text, history=(), token=None, **fields):
        response = api_client.post("/ai/chat", headers=headers, json={"messages": [*history, {"role": "user", "content": text}],
            "record_state": token, "require_budget": True, **fields})
        assert response.status_code == 200, response.text
        return response.json()
    return headers, ask, decision, calls


@pytest.mark.parametrize("text,token,day", [
    ("I earned 2k yesterday.", "2k", date(2026,10,17)),
    ("got paid 2k yesterday", "2k", date(2026,10,17)),
    ("I received 2,000 today", "2,000", TODAY),
    ("my pay came in yesterday 2k", "2k", date(2026,10,17)),
    ("Can you record the 2000 I received today?", "2000", TODAY),
])
def test_i1_paraphrases_create_addition_not_replacement(income_chat, monkeypatch, db_session, text, token, day):
    _, ask, decision, calls = income_chat
    decision[0] = semantic(amount_text=token)
    def forbidden_second_extraction(*args):
        raise AssertionError("A validated income receipt must not depend on a second model output")
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", forbidden_second_extraction)
    data = ask(text)
    proposal = data["proposal"]
    assert proposal["kind"] == "income" and proposal["income_operation"] == "add" and proposal["status"] == "pending"
    assert Decimal(proposal["amount"]) == 2000 and proposal["date"] == day.isoformat()
    assert Decimal(proposal["income_before"]) == 10000 and Decimal(proposal["income_after"]) == 12000
    assert "one-time" in data["reply"] and "other months" in data["reply"]
    assert "expense category" not in data["reply"]
    assert calls[0][1]["today"] == TODAY.isoformat() and calls[0][1]["timezone"] == "Asia/Dubai"
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=10).one().amount_cents == 1000000
    assert db_session.query(Transaction).count() == 0


def test_confirmation_adds_once_and_does_not_modify_other_months(income_chat, api_client, db_session):
    headers, ask, _, _ = income_chat
    db_session.add(MonthlyIncome(user_id=1, year=2026, month=11, amount_cents=1000000)); db_session.commit()
    proposal = ask("I earned 2k yesterday.")["proposal"]
    path = f"/ai/proposals/{proposal['id']}/confirm"
    assert api_client.post(path, headers=headers).status_code == 200
    assert api_client.post(path, headers=headers).status_code == 200
    db_session.expire_all()
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=10).one().amount_cents == 1200000
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=11).one().amount_cents == 1000000


def test_i2_lookup_remains_authoritative_and_readonly(income_chat, db_session):
    _, ask, decision, _ = income_chat
    decision[0] = semantic(intent="read", kind=None, amount_text=None, income_operation=None)
    data = ask("What's my income?")
    assert "10,000.00" in data["reply"] and "99999" not in data["reply"]
    assert data["proposal"] is None and db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("text,token", [("How would recording 2,000 income affect my budget?", "2,000"),
    ("what if I got an extra 2k", "2k"), ("Would another 2000 income help my budget?", "2000")])
def test_i3_scenario_is_conditional_one_time_and_never_saved(income_chat, db_session, text, token):
    _, ask, decision, _ = income_chat
    decision[0] = semantic(intent="read", amount_text=token)
    data = ask(text)
    for value in ("10,000.00", "6,420.00", "3,580.00", "12,000.00", "5,580.00"):
        assert value in data["reply"]
    assert "If" in data["reply"] and "one-time" in data["reply"] and "haven't assumed recurrence" in data["reply"]
    assert data["proposal"] is None and data["plan"] is None
    assert db_session.query(ChatProposal).count() == 0
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=10).one().amount_cents == 1000000


@pytest.mark.parametrize("first,answer,amount", [("I earned 2k", "Yesterday.", "2k"), ("I got paid yesterday", "2k.", None)])
def test_missing_field_followup_retains_income_details(income_chat, first, answer, amount):
    _, ask, decision, calls = income_chat
    decision[0] = semantic(amount_text=amount)
    data = ask(first)
    assert data["proposal"] is None and data["record_state"]
    draft = load_draft(data["record_state"], 1)
    assert draft.kind == "income" and draft.income_operation == "add"
    assert "category" not in data["reply"]
    completed = ask(answer, [{"role": "user", "content": first}, {"role": "assistant", "content": data["reply"]}], data["record_state"])
    assert completed["proposal"]["income_operation"] == "add" and Decimal(completed["proposal"]["amount"]) == 2000
    assert completed["proposal"]["date"] == "2026-10-17" and len(calls) == 1


@pytest.mark.parametrize("amount", ["12000", "0"])
def test_explicit_total_replacement_remains_available(income_chat, api_client, db_session, amount):
    headers, ask, decision, _ = income_chat
    decision[0] = semantic(amount_text=amount, income_operation="replace")
    data = ask(f"Set my monthly income to {amount} this month")
    proposal = data["proposal"]
    assert proposal["income_operation"] == "replace" and "replaces any saved income" in data["reply"]
    assert api_client.post(f"/ai/proposals/{proposal['id']}/confirm", headers=headers).status_code == 200
    db_session.expire_all()
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=10).one().amount_cents == int(amount)*100


@pytest.mark.parametrize("text", ["What if I earned 2k yesterday?", "I might receive 2k tomorrow",
    "I don't want to record 2k income today", "I save 2k today"])
def test_nonactions_cannot_propose_income_even_if_model_misclassifies(income_chat, db_session, text):
    _, ask, _, _ = income_chat
    data = ask(text)
    assert data["proposal"] is None and db_session.query(ChatProposal).count() == 0
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=10).one().amount_cents == 1000000


def test_lookup_followup_and_yes_cannot_record_income(income_chat, db_session):
    _, ask, decision, _ = income_chat
    decision[0] = semantic(continuation=True)
    data = ask("2k", [{"role": "user", "content": "What's my income?"}, {"role": "assistant", "content": "AED 10000"}])
    assert data["proposal"] is None
    data = ask("yes", [{"role": "user", "content": "I earned 2k yesterday"}, {"role": "assistant", "content": "Please confirm in the app"}])
    assert data["proposal"] is None and db_session.query(ChatProposal).count() == 0


def test_income_snapshot_rejects_stale_confirmation(income_chat, api_client, db_session):
    headers, ask, _, _ = income_chat
    proposal = ask("I earned 2k yesterday")["proposal"]
    api_client.put("/budget/income?year=2026&month=10", headers=headers, json={"amount":10500})
    response = api_client.post(f"/ai/proposals/{proposal['id']}/confirm", headers=headers)
    assert response.status_code == 409
    db_session.expire_all()
    assert db_session.query(MonthlyIncome).filter_by(user_id=1, year=2026, month=10).one().amount_cents == 1050000
    assert db_session.query(ChatProposal).filter_by(id=proposal["id"]).one().status == "pending"


def test_other_account_cannot_use_draft_or_confirm_proposal(income_chat, api_client, db_session):
    _, ask, _, _ = income_chat
    pending = ask("I earned 2k")
    proposal = ask("Yesterday.", token=pending["record_state"])["proposal"]
    register_user(api_client, email="bob-income@example.com")
    bob = auth_headers(login_user(api_client, email="bob-income@example.com").json()["access_token"])
    assert api_client.post("/ai/chat", headers=bob, json={"messages":[{"role":"user","content":"Yesterday."}],"record_state":pending["record_state"]}).status_code == 422
    assert api_client.post(f"/ai/proposals/{proposal['id']}/confirm", headers=bob).status_code == 404
    assert db_session.query(MonthlyIncome).filter_by(user_id=2).count() == 0


def test_currency_and_default_currency_are_not_double_converted(income_chat):
    _, ask, _, _ = income_chat
    pending = ask("I earned 2k", currency="CNY", aed_to_cny=2)
    data = ask("Yesterday.", token=pending["record_state"], currency="AED")
    assert Decimal(data["proposal"]["amount"]) == 1000
    assert Decimal(data["proposal"]["income_after"]) == 11000 and "AED 1,000.00" in data["reply"]


def test_yesterday_crosses_year_boundary_without_using_model_date(income_chat, monkeypatch, db_session):
    _, ask, _, _ = income_chat
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2027,1,1,0,30,tzinfo=tz)
    monkeypatch.setattr("app.routers.chat.datetime", Clock)
    db_session.add(MonthlyIncome(user_id=1, year=2026, month=12, amount_cents=1000000)); db_session.commit()
    proposal = ask("I earned 2k yesterday")["proposal"]
    assert proposal["date"] == "2026-12-31" and (proposal["year"], proposal["month"]) == (2026,12)


def test_operation_clarification_preserves_known_amount_and_date(income_chat):
    _, ask, decision, _ = income_chat
    decision[0] = semantic(income_operation=None)
    first = ask("Record 2k income yesterday")
    assert first["proposal"] is None and first["record_state"]
    decision[0] = semantic(income_operation="add", continuation=False)
    completed = ask("One-time.", [{"role":"user","content":"Record 2k income yesterday"},
        {"role":"assistant","content":first["reply"]}], first["record_state"])
    assert completed["proposal"]["income_operation"] == "add"
    assert Decimal(completed["proposal"]["amount"]) == 2000 and completed["proposal"]["date"] == "2026-10-17"


@pytest.mark.parametrize("text,token", [("I earned 2k yesterday", "2000"), ("I received 2,000 yesterday", "2000")])
def test_normalized_model_numbers_still_require_matching_literal_user_value(income_chat, text, token):
    _, ask, decision, _ = income_chat
    decision[0] = semantic(amount_text=token)
    proposal = ask(text)["proposal"]
    assert Decimal(proposal["amount"]) == 2000 and proposal["income_operation"] == "add"


def test_hypothetical_model_can_normalize_thousands_separator(income_chat):
    _, ask, decision, _ = income_chat
    decision[0] = semantic(intent="read", amount_text="2000")
    result = ask("How would recording 2,000 income affect my budget?")
    assert "5,580.00" in result["reply"] and "one-time" in result["reply"] and result["proposal"] is None
