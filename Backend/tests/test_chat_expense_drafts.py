"""Expense proposal regressions. Model interpretation is mocked; API/state/validation are real."""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
import jwt
import pytest
from conftest import register_user, login_user, auth_headers
from app.core.config import JWT_ALGORITHM, get_jwt_secret_key
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction
from app.services.chat_expenses import load_draft

TODAY = date(2026, 10, 18)


@pytest.fixture
def expense_chat(api_client, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 18, 12, tzinfo=tz)
    monkeypatch.setattr("app.routers.chat.datetime", Clock)
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    def no_second_extraction(*args):
        raise AssertionError("Expense proposals must not depend on a second model extraction")
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", no_second_extraction)
    def ask(text, history=(), token=None, **fields):
        return api_client.post("/ai/chat", headers=headers, json={"messages": [*history, {"role": "user", "content": text}],
            "require_budget": True, "record_state": token, **fields})
    return headers, ask


def interpretation(monkeypatch, amount="50", description="lunch", category="Food", **fields):
    value = dict(intent="record", topic="budget", continuation=False, kind="expense", amount_text=amount,
        category_text=description, category=category, clarification=f"When did you pay for {description}?") | fields
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", lambda *_: json.dumps(value))


@pytest.mark.parametrize("text,amount,description,category,day", [
    ("Lunch cost me 50 today.", "50", "lunch", "Food", TODAY),
    ("Spent 75 on transport today.", "75", "transport", "Transport", TODAY),
    ("Lunch cost me 50 yesterday.", "50", "lunch", "Food", TODAY-timedelta(days=1)),
    ("Spent 75 on transport YESTERDAY!", "75", "transport", "Transport", TODAY-timedelta(days=1)),
    ("Lunch was 50.", "50", "lunch", "Food", None),
])
def test_explicit_dates_are_server_resolved_not_model_clarifications(expense_chat, monkeypatch, db_session,
        text, amount, description, category, day):
    _, ask = expense_chat
    interpretation(monkeypatch, amount, description, category)
    response = ask(text)
    assert response.status_code == 200, response.text
    data = response.json()
    if day is None:
        assert data["proposal"] is None and data["record_state"]
        assert data["reply"].startswith("When did you pay")
    else:
        proposal = data["proposal"]
        assert proposal["status"] == "pending"
        assert Decimal(proposal["amount"]) == Decimal(amount)
        assert (proposal["date"], proposal["category"], proposal["description"]) == (day.isoformat(), category, description)
        assert data["record_state"] is None
    assert db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("answer,day", [("Today.", TODAY), ("yesterday!", TODAY-timedelta(days=1)), ("2026-10-17", TODAY-timedelta(days=1))])
def test_e5_real_two_request_conversation_preserves_draft(expense_chat, monkeypatch, db_session, answer, day):
    _, ask = expense_chat
    # Reproduces live Ollama: Food instead of the explicitly named Groceries.
    interpretation(monkeypatch, "120", "groceries", "Food")
    first_text = "I just bought groceries for 120."
    first = ask(first_text).json()
    assert first["proposal"] is None and first["record_state"]
    assert first["reply"] == "When did you pay for groceries? Nothing has been saved."
    draft = load_draft(first["record_state"], 1)
    assert (draft.amount_text, draft.category, draft.category_text) == ("120", "Groceries", "groceries")
    def must_not_reinterpret(*args):
        raise AssertionError("A typed date answer must not depend on the model's continuation flag")
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", must_not_reinterpret)
    second = ask(answer, [{"role": "user", "content": first_text}, {"role": "assistant", "content": first["reply"]}], first["record_state"])
    assert second.status_code == 200, second.text
    data = second.json()
    assert data["proposal"]["status"] == "pending"
    assert Decimal(data["proposal"]["amount"]) == 120
    assert data["proposal"]["category"] == "Groceries"
    assert data["proposal"]["description"] == "groceries"
    assert data["proposal"]["date"] == day.isoformat()
    assert data["record_state"] is None
    assert db_session.query(ChatProposal).count() == 1 and db_session.query(Transaction).count() == 0


def test_draft_survives_trimmed_history_and_confirmation_remains_required(expense_chat, api_client, monkeypatch, db_session):
    headers, ask = expense_chat
    interpretation(monkeypatch, "120", "groceries", "Groceries")
    draft = ask("I just bought groceries for 120.").json()
    proposal = ask("Today.", token=draft["record_state"]).json()["proposal"]
    assert db_session.query(Transaction).count() == 0
    url = f"/ai/proposals/{proposal['id']}/confirm"
    assert api_client.post(url, headers=headers).status_code == 200
    assert api_client.post(url, headers=headers).status_code == 200
    row = db_session.query(Transaction).one()
    assert (row.amount, row.category, row.description, row.date, row.user_id) == (120, "Groceries", "groceries", TODAY, 1)


def test_known_date_and_category_survive_missing_amount(expense_chat, monkeypatch):
    _, ask = expense_chat
    interpretation(monkeypatch, None, "lunch", "Food")
    first = ask("Lunch today.").json()
    assert first["reply"] == "How much did you pay? Nothing has been saved."
    second = ask("50.", token=first["record_state"]).json()
    assert Decimal(second["proposal"]["amount"]) == 50 and second["proposal"]["date"] == TODAY.isoformat()


@pytest.mark.parametrize("failure", ["tampered", "expired", "other_account"])
def test_pending_state_is_owner_bound_and_expires(expense_chat, api_client, monkeypatch, db_session, failure):
    _, ask = expense_chat
    interpretation(monkeypatch, "120", "groceries", "Groceries")
    token = ask("I just bought groceries for 120.").json()["record_state"]
    if failure == "tampered":
        token = "broken." + token
    else:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
        payload["exp"] = 1 if failure == "expired" else payload["exp"]
        payload["sub"] = "999" if failure == "other_account" else payload["sub"]
        token = jwt.encode(payload, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    response = ask("Today.", token=token)
    assert response.status_code == 422 and db_session.query(ChatProposal).count() == 0
    assert db_session.query(Transaction).count() == 0


def test_non_field_topic_switch_does_not_reuse_pending_expense(expense_chat, monkeypatch, db_session):
    _, ask = expense_chat
    interpretation(monkeypatch, "120", "groceries", "Groceries")
    token = ask("I just bought groceries for 120.").json()["record_state"]
    captured = []
    def model(messages, context):
        captured.append(context)
        return json.dumps(dict(intent="clarify", topic="general", continuation=False, kind=None,
            amount_text=None, category_text=None, category=None, clarification="What would you like to do next?"))
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", model)
    result = ask("Forget that expense", token=token).json()
    assert captured[0]["pending_expense"]["category"] == "Groceries"
    assert captured[0]["today"] == TODAY.isoformat()
    assert result["record_state"] is None and result["proposal"] is None
    assert db_session.query(ChatProposal).count() == 0


def test_date_in_new_financial_request_is_not_a_field_answer(expense_chat, monkeypatch):
    _, ask = expense_chat
    interpretation(monkeypatch, "120", "groceries", "Groceries")
    token = ask("I just bought groceries for 120.").json()["record_state"]
    interpretation(monkeypatch, "75", "transport", "Transport")
    result = ask("Spent 75 on transport today.", token=token).json()
    assert Decimal(result["proposal"]["amount"]) == 75 and result["proposal"]["category"] == "Transport"


def test_yes_cannot_recreate_a_completed_expense(expense_chat, monkeypatch, db_session):
    _, ask = expense_chat
    interpretation(monkeypatch)
    text = "Lunch cost me 50 today."
    first = ask(text).json()
    interpretation(monkeypatch, continuation=True)
    response = ask("yes", [{"role": "user", "content": text}, {"role": "assistant", "content": first["reply"]}]).json()
    assert response["proposal"] is None
    assert db_session.query(ChatProposal).count() == 1 and db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("text,token", [("Lunch was -50 today", "50"), ("Lunch was 50.25 today", "50"),
    ("Lunch was 1,250 today", "250"), ("Lunch was 1,250 today", "1")])
def test_amount_grounding_does_not_accept_partial_or_negated_numbers(expense_chat, monkeypatch, text, token):
    _, ask = expense_chat
    interpretation(monkeypatch, token)
    result = ask(text).json()
    assert result["proposal"] is None


def test_pending_cny_amount_keeps_original_currency_when_display_changes(expense_chat, monkeypatch):
    _, ask = expense_chat
    interpretation(monkeypatch, "120", "groceries", "Groceries")
    first = ask("I just bought groceries for CNY 120.", currency="CNY", aed_to_cny=2).json()
    second = ask("Today.", token=first["record_state"], currency="AED").json()
    assert Decimal(second["proposal"]["amount"]) == 60 and "AED 60.00" in second["reply"]


@pytest.mark.parametrize("unit", ["USD", "CNY"])
def test_direct_expense_path_does_not_guess_unsupported_or_unselected_currency(expense_chat, monkeypatch, unit):
    _, ask = expense_chat
    interpretation(monkeypatch)
    result = ask(f"Lunch cost me {unit} 50 today.").json()
    assert result["proposal"] is None and "currency" in result["reply"]


def test_known_amount_and_date_survive_missing_category(expense_chat, monkeypatch):
    _, ask = expense_chat
    interpretation(monkeypatch, "50", None, None)
    first = ask("Spent 50 today.").json()
    assert first["reply"] == "What was the expense for? Nothing has been saved."
    second = ask("Groceries.", token=first["record_state"]).json()
    assert Decimal(second["proposal"]["amount"]) == 50
    assert second["proposal"]["category"] == "Groceries" and second["proposal"]["date"] == TODAY.isoformat()
