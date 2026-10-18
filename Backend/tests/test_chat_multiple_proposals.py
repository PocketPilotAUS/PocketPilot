"""Mocked semantic interpretation; actual multi-turn API, drafts and persistence."""
import json
from decimal import Decimal
import pytest
from test_chat_proposal_references import acknowledgments
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction


def conversation(ask, text, history, ids):
    response = ask(text, history, proposal_ids=ids, **({"active_proposal_id": ids[-1]} if ids else {}))
    assert response.status_code == 200, response.text
    data = response.json()
    history.extend([{"role": "user", "content": text}, {"role": "assistant", "content": data["reply"]}])
    if data.get("proposal"):
        ids.append(data["proposal"]["id"])
    return data


@pytest.mark.parametrize("second", [
    "I also spent 25 AED on transport today.",
    "Another expense: 25 AED for transport today.",
    "Plus 25 for transport today.",
])
def test_new_expenses_are_separate_even_when_model_says_continuation(acknowledgments, db_session, second):
    _, choice, _, ask = acknowledgments
    history, ids = [], []
    choice[0].update(amount_text="40", category_text="groceries", category="Groceries", continuation=False)
    first = conversation(ask, "I spent 40 AED on groceries today.", history, ids)
    choice[0].update(amount_text="25", category_text="transport", category="Transport", continuation=True)
    second_data = conversation(ask, second, history, ids)
    assert second_data["proposal"], second_data
    assert len(set(ids)) == 2
    assert Decimal(second_data["proposal"]["amount"]) == 25
    assert second_data["proposal"]["category"] == "Transport"
    assert second_data["proposal"]["date"] == first["proposal"]["date"]
    assert db_session.get(ChatProposal, ids[0]).status == "pending"
    assert db_session.query(Transaction).count() == 0

    text = "Can you confirm the 40 AED groceries expense?"
    choice[0].update(intent="proposal", proposal_reference=text, amount_text="40", category_text="groceries", category="Groceries")
    reference = conversation(ask, text, history, ids)
    assert reference["proposal"] is None
    assert reference["proposal_updates"] == [{"id": ids[0], "status": "pending"}]
    assert "use Confirm" in reference["reply"]

    text = "Actually, cancel the 40 AED groceries expense."
    choice[0].update(intent="cancel", proposal_reference=None)
    canceled = conversation(ask, text, history, ids)
    assert canceled["proposal_updates"] == [{"id": ids[0], "status": "dismissed"}]
    db_session.expire_all()
    assert db_session.get(ChatProposal, ids[0]).status == "dismissed"
    assert db_session.get(ChatProposal, ids[1]).status == "pending"
    assert db_session.query(Transaction).count() == 0


def test_ambiguous_cancellation_does_not_choose_latest(acknowledgments, db_session):
    _, choice, _, ask = acknowledgments
    history, ids = [], []
    for amount in ("40", "25"):
        choice[0].update(amount_text=amount, category_text="groceries", category="Groceries", continuation=False)
        assert conversation(ask, f"Spent {amount} on groceries today.", history, ids)["proposal"]
    choice[0].update(intent="cancel", amount_text=None, category_text=None, category=None)
    data = conversation(ask, "Cancel that expense.", history, ids)
    assert "Which" in data["reply"] and not data["proposal_updates"]
    assert all(db_session.get(ChatProposal, key).status == "pending" for key in ids)


@pytest.mark.parametrize("first_status", ["pending", "saved", "dismissed", "expired"])
@pytest.mark.parametrize("buttons", [("confirm", "dismiss"), ("dismiss", "confirm")])
def test_independent_buttons_and_new_records_after_terminal_states(acknowledgments, api_client, db_session, first_status, buttons):
    import time
    headers, choice, _, ask = acknowledgments
    history, ids = [], []
    choice[0].update(amount_text="40", category_text="groceries", category="Groceries", continuation=False)
    assert conversation(ask, "Spent 40 on groceries today.", history, ids)["proposal"]
    original_payload = db_session.get(ChatProposal, ids[0]).payload
    if first_status in ("saved", "dismissed"):
        endpoint = "confirm" if first_status == "saved" else "dismiss"
        assert api_client.post(f"/ai/proposals/{ids[0]}/{endpoint}", headers=headers).status_code == 200
    elif first_status == "expired":
        row = db_session.get(ChatProposal, ids[0])
        raw = json.loads(row.payload)
        raw["_expires_at"] = time.time() - 1
        row.payload = json.dumps(raw)
        db_session.commit()
        original_payload = row.payload
    before = db_session.query(Transaction).count()
    choice[0].update(amount_text="25", category_text="transport", category="Transport", continuation=True)
    assert conversation(ask, "I also spent 25 on transport today.", history, ids)["proposal"]
    assert db_session.query(Transaction).count() == before
    db_session.expire_all()
    assert db_session.get(ChatProposal, ids[0]).payload == original_payload
    if first_status == "pending":
        for index, endpoint in enumerate(buttons):
            assert api_client.post(f"/ai/proposals/{ids[index]}/{endpoint}", headers=headers).status_code == 200
        db_session.expire_all()
        assert [db_session.get(ChatProposal, key).status for key in ids] == [
            "saved" if endpoint == "confirm" else "dismissed" for endpoint in buttons]
        assert db_session.query(Transaction).count() == 1
        saved_id = ids[buttons.index("confirm")]
        assert api_client.post(f"/ai/proposals/{saved_id}/confirm", headers=headers).status_code == 200
        assert db_session.query(Transaction).count() == 1


@pytest.mark.parametrize("same_amount", [True, False])
def test_similar_records_require_grounded_selectors(acknowledgments, db_session, same_amount):
    _, choice, _, ask = acknowledgments
    history, ids = [], []
    for amount, category in [("40", "Groceries"), ("40" if same_amount else "25", "Transport" if same_amount else "Groceries")]:
        choice[0].update(amount_text=amount, category_text=category.lower(), category=category, continuation=True)
        assert conversation(ask, f"Spent {amount} on {category.lower()} today.", history, ids)["proposal"]
    # The model can omit all slots: literal persisted labels/amounts still resolve.
    choice[0].update(intent="cancel", amount_text=None, category_text=None, category=None)
    text = "Cancel the groceries expense." if same_amount else "Cancel the 40 expense."
    data = conversation(ask, text, history, ids)
    assert data["proposal_updates"] == [{"id": ids[0], "status": "dismissed"}]
    assert db_session.get(ChatProposal, ids[1]).status == "pending"


def test_identical_proposals_are_ambiguous_and_correction_does_not_duplicate(acknowledgments, db_session):
    _, choice, _, ask = acknowledgments
    history, ids = [], []
    choice[0].update(amount_text="40", category_text="groceries", category="Groceries", continuation=True)
    for _ in range(2):
        assert conversation(ask, "Spent 40 on groceries today.", history, ids)["proposal"]
    choice[0].update(intent="cancel", amount_text=None, category_text=None, category=None)
    data = conversation(ask, "Cancel the 40 groceries expense.", history, ids)
    assert "Which" in data["reply"] and not data["proposal_updates"]
    choice[0].update(intent="proposal", proposal_reference="that expense")
    data = conversation(ask, "Actually change that expense to 30.", history, ids)
    assert data["proposal"] is None and data["record_state"] is None and db_session.query(ChatProposal).count() == 2
    assert all(db_session.get(ChatProposal, key).status == "pending" for key in ids)
    assert db_session.query(Transaction).count() == 0


def test_new_chat_cannot_reuse_old_details_and_foreign_history_is_rejected(acknowledgments, api_client, db_session):
    from conftest import register_user, login_user, auth_headers
    _, choice, _, ask = acknowledgments
    history, ids = [], []
    choice[0].update(amount_text="40", category_text="groceries", category="Groceries", continuation=False)
    assert conversation(ask, "Spent 40 on groceries today.", history, ids)["proposal"]
    choice[0].update(amount_text="25", category_text="transport", category="Transport", continuation=True)
    # No history IDs in New Chat. No reuse of the old amount or category.
    data = ask("I also spent 25 on transport today.").json()
    assert data["proposal"]["id"] != ids[0] and Decimal(data["proposal"]["amount"]) == 25
    assert data["proposal"]["category"] == "Transport"
    register_user(api_client, email="other-multiple@example.com")
    headers = auth_headers(login_user(api_client, email="other-multiple@example.com").json()["access_token"])
    response = api_client.post("/ai/chat", headers=headers, json={"messages":[{"role":"user","content":"Spent 25 on transport today."}], "proposal_ids":ids})
    assert response.status_code == 404
    assert api_client.post(f"/ai/proposals/{ids[0]}/confirm", headers=headers).status_code == 404
    assert db_session.query(Transaction).count() == 0


def test_second_incomplete_expense_retains_its_own_details(acknowledgments, db_session):
    _, choice, _, ask = acknowledgments
    history, ids = [], []
    choice[0].update(amount_text="40", category_text="groceries", category="Groceries", continuation=False)
    assert conversation(ask, "Spent 40 on groceries today.", history, ids)["proposal"]
    choice[0].update(amount_text="25", category_text="transport", category="Transport", continuation=True)
    missing = conversation(ask, "I also spent 25 on transport.", history, ids)
    assert missing["record_state"] and "When" in missing["reply"]
    data = ask("Today.", history, proposal_ids=ids, active_proposal_id=ids[0], record_state=missing["record_state"]).json()
    assert Decimal(data["proposal"]["amount"]) == 25 and data["proposal"]["category"] == "Transport"
    assert db_session.get(ChatProposal, ids[0]).status == "pending"
    assert db_session.query(Transaction).count() == 0


def test_missing_model_kind_does_not_cancel_income_when_user_says_expense(acknowledgments, db_session):
    from test_chat_proposal_references import pending
    _, choice, _, ask = acknowledgments
    income = pending(db_session, "income")
    choice[0].update(intent="cancel", kind=None, amount_text=None, category_text=None, category=None)
    data = ask("Cancel that expense.", proposal_ids=[income["id"]], active_proposal_id=income["id"]).json()
    assert not data["proposal_updates"]
    assert db_session.get(ChatProposal, income["id"]).status == "pending"


@pytest.mark.parametrize("text", [
    "Plus 25 and 50 for transport today.",
    "Spent 25 or 50 on transport today.",
    "Spent 25 plus 50 on transport today.",
])
def test_multiple_amounts_still_require_clarification(acknowledgments, db_session, text):
    _, choice, _, ask = acknowledgments
    choice[0].update(amount_text="25", category_text="transport", category="Transport", continuation=False)
    data = ask(text).json()
    assert data["proposal"] is None
    assert db_session.query(ChatProposal).count() == 0
    assert db_session.query(Transaction).count() == 0
