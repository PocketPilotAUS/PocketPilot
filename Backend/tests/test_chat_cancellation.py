"""Mocked interpretation; real persisted cancellation, replay and financial writes."""
import json
import time
import jwt
import pytest
from conftest import register_user, login_user, auth_headers
from app.core.config import JWT_ALGORITHM, get_jwt_secret_key
from app.core.currency import format_reply_currency
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction
from app.models.income import MonthlyIncome
from app.routers.proposals import ProposedAction, create_proposal
from app.services.chat_record_drafts import RecordDraft, seal_draft
from datetime import date


@pytest.fixture
def cancellation(api_client, monkeypatch):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    decision = [dict(intent="cancel",topic="budget",continuation=True,kind="expense",amount_text=None,
        category_text=None,category=None,clarification=None)]
    contexts = []
    def interpret(messages, context):
        contexts.append(context)
        return json.dumps(decision[0])
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",interpret)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_: json.dumps({"reply":"Do you want to remove it?","action":None,"planning":None}))
    def ask(text="Actually, I don't want to record this expense.", **fields):
        return api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":text}],**fields})
    return headers, decision, contexts, ask


def proposal(db, kind="expense", draft_id=None):
    action = ProposedAction(kind=kind, amount=50 if kind == "expense" else 2000,
        category="Food" if kind == "expense" else None,date=date(2026,10,18), year=2026 if kind=="income" else None,
        month=10 if kind=="income" else None,income_operation="add" if kind=="income" else "replace",
        income_before=None,income_after=2000 if kind=="income" else None)
    return create_proposal(db,1,action,draft_id)


@pytest.mark.parametrize("kind",["expense","income"])
def test_explicit_cancellation_immediate_and_repeated_confirm_rejected(api_client, db_session, cancellation, kind):
    headers, decision, contexts, ask = cancellation
    decision[0]["kind"] = kind
    pending = proposal(db_session,kind)
    data = ask("Don't record that " + kind,active_proposal_id=pending["id"]).json()
    assert data["reply"] == f"Okay, I've canceled that {kind}. Nothing was saved."
    assert data["proposal_updates"] == [{"id":pending["id"],"status":"dismissed"}]
    assert contexts[-1]["pending_proposal"]["amount"] == ("50" if kind=="expense" else "2000")
    assert db_session.get(ChatProposal,pending["id"]).status == "dismissed"
    for _ in range(2):
        assert api_client.post(f"/ai/proposals/{pending['id']}/confirm",headers=headers).status_code == 409
    assert ask("Cancel that " + kind,active_proposal_id=pending["id"]).status_code == 200
    assert db_session.query(Transaction).count() == db_session.query(MonthlyIncome).count() == 0


def test_r4_actual_three_requests_and_yes_does_not_restart(api_client, db_session, cancellation):
    headers, decision, _, ask = cancellation
    decision[0].update(intent="record",continuation=False,amount_text="50",category_text="lunch",category="Food")
    first = ask("I spent 50 on lunch today.").json()
    pending = first["proposal"]
    decision[0].update(intent="cancel",amount_text=None,category_text=None,category=None)
    history = [{"role":"user","content":"I spent 50 on lunch today."},{"role":"assistant","content":first["reply"]},
               {"role":"user","content":"Actually, I don't want to record this expense."}]
    second = api_client.post("/ai/chat",headers=headers,json={"messages":history,"active_proposal_id":pending["id"]}).json()
    history += [{"role":"assistant","content":second["reply"]},{"role":"user","content":"Yes.\n[Currency for untagged amounts in this message: AED]"}]
    # Deliberately wrong model output cannot revive a canceled expense.
    decision[0].update(intent="record",amount_text="50",category_text="lunch",category="Food")
    third = api_client.post("/ai/chat",headers=headers,json={"messages":history,"active_proposal_id":pending["id"]}).json()
    assert "canceled" in third["reply"] and third["proposal"] is None and third["record_state"] is None
    assert api_client.post(f"/ai/proposals/{pending['id']}/confirm",headers=headers).status_code == 409
    assert db_session.query(Transaction).count() == 0


def test_dismiss_button_is_idempotent_and_revokes_confirmation(api_client, db_session, cancellation):
    headers = cancellation[0]
    pending = proposal(db_session)
    for _ in range(2):
        response = api_client.post(f"/ai/proposals/{pending['id']}/dismiss",headers=headers)
        assert response.status_code == 200 and response.json()["status"] == "dismissed"
    assert api_client.post(f"/ai/proposals/{pending['id']}/confirm",headers=headers).status_code == 409
    assert db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("kind",["expense","income"])
def test_cancel_signed_incomplete_draft_blocks_token_replay(api_client, db_session, cancellation, kind):
    headers, decision, _, ask = cancellation
    decision[0]["kind"] = kind
    draft = RecordDraft(kind=kind,source="paid 50 lunch" if kind=="expense" else "earned 50",
        amount_text="50",category="Food" if kind=="expense" else None,category_text="lunch" if kind=="expense" else None,
        currency="AED",income_operation="add" if kind=="income" else None)
    token = seal_draft(draft,1)
    canceled = ask("Cancel that "+kind,record_state=token)
    assert canceled.status_code == 200 and "canceled" in canceled.json()["reply"]
    replay = ask("Today",record_state=token)
    assert replay.status_code == 422
    assert api_client.post(f"/ai/proposals/{draft.draft_id}/confirm",headers=headers).status_code == 409
    assert db_session.query(Transaction).count() == db_session.query(MonthlyIncome).count() == 0


def test_completed_draft_token_cannot_create_duplicate_after_cancellation(api_client, db_session, cancellation):
    headers, decision, _, ask = cancellation
    draft = RecordDraft(source="paid 50 lunch",amount_text="50",category="Food",category_text="lunch",currency="AED")
    token = seal_draft(draft,1)
    first = ask("Today",record_state=token).json()
    assert first["proposal"]["id"] == draft.draft_id
    assert ask(active_proposal_id=draft.draft_id).status_code == 200
    assert ask("Today",record_state=token).status_code == 422
    assert api_client.post(f"/ai/proposals/{draft.draft_id}/confirm",headers=headers).status_code == 409
    assert db_session.query(Transaction).count() == 0


def test_owner_expiry_and_already_saved_guards(api_client, db_session, cancellation):
    headers, _, _, ask = cancellation
    pending = proposal(db_session)
    register_user(api_client,email="other@example.com")
    other = auth_headers(login_user(api_client,email="other@example.com").json()["access_token"])
    assert api_client.post("/ai/chat",headers=other,json={"messages":[{"role":"user","content":"Cancel it"}],"active_proposal_id":pending["id"]}).status_code == 404
    assert api_client.post(f"/ai/proposals/{pending['id']}/dismiss",headers=other).status_code == 404
    draft = RecordDraft(source="paid 50 lunch",amount_text="50",currency="AED")
    token = seal_draft(draft,1)
    assert api_client.post("/ai/chat",headers=other,json={"messages":[{"role":"user","content":"Today"}],"record_state":token}).status_code == 422
    payload = jwt.decode(token,get_jwt_secret_key(),algorithms=[JWT_ALGORITHM])
    payload["exp"] = int(time.time())-1
    expired = jwt.encode(payload,get_jwt_secret_key(),algorithm=JWT_ALGORITHM)
    assert ask("Today",record_state=expired).status_code == 422
    row = db_session.get(ChatProposal,pending["id"])
    data = json.loads(row.payload); data["_expires_at"] = int(time.time())-1
    row.payload = json.dumps(data); db_session.commit()
    assert api_client.post(f"/ai/proposals/{pending['id']}/confirm",headers=headers).status_code == 409
    assert db_session.query(Transaction).count() == 0
    saved = proposal(db_session)
    path = f"/ai/proposals/{saved['id']}/confirm"
    assert api_client.post(path,headers=headers).status_code == api_client.post(path,headers=headers).status_code == 200
    result = ask(active_proposal_id=saved["id"]).json()
    assert "already saved" in result["reply"] and result["proposal_updates"][0]["status"] == "saved"
    assert db_session.query(Transaction).count() == 1


@pytest.mark.parametrize("text,currency,expected", [
    ("$566.14 (AED)","AED","AED 566.14"), ("$566.14","AED","AED 566.14"),
    ("AED $566.14 (AED)","AED","AED 566.14"), ("$566.14 AED","AED","AED 566.14"),
    ("$1,000.00","CNY","CNY 1,000.00"), ("USD $50","AED","USD 50"),
    ("$50 (USD)","AED","USD 50"), ("AED 50 (AED)","AED","AED 50"),
    ("5% annual, 24 months; AED 566.14","AED","5% annual, 24 months; AED 566.14"),
])
def test_currency_normalization_preserves_amounts_and_explicit_labels(text,currency,expected):
    assert format_reply_currency(text,currency) == expected


@pytest.mark.parametrize("currency,rate", [("AED",None),("CNY",7)])
def test_readonly_currency_uses_shared_response_boundary(cancellation, monkeypatch, currency, rate):
    _, decision, _, ask = cancellation
    decision[0].update(intent="read",continuation=False)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_: json.dumps({"reply":"Payment is $566.14 ("+currency+").","action":None,"planning":None}))
    response = ask("Explain loan payments",currency=currency,**({"aed_to_cny":rate} if rate else {}))
    assert response.json()["reply"] == f"Payment is {currency} 566.14."


def test_explicit_usd_source_is_not_relabelled_as_aed():
    assert format_reply_currency("It costs $50.", "AED", "Explain a USD 50 purchase") == "It costs USD 50."


def test_current_incomplete_record_cancels_before_an_older_proposal(db_session, cancellation):
    _, decision, _, ask = cancellation
    old = proposal(db_session)
    draft = RecordDraft(kind="income",source="earned 2000",amount_text="2000",income_operation="add",currency="AED")
    token = seal_draft(draft,1)
    decision[0]["kind"] = "income"
    result = ask("Cancel that income",record_state=token,active_proposal_id=old["id"]).json()
    assert "canceled that income" in result["reply"]
    assert db_session.get(ChatProposal,old["id"]).status == "pending"


@pytest.mark.parametrize("answer", ["Today.", "Yesterday.", "Yes."])
def test_canceled_field_answers_never_start_a_new_record(cancellation, monkeypatch, answer, api_client):
    headers, _, _, _ = cancellation
    def forbidden(*args):
        raise AssertionError("A field-only reply cannot resume a canceled record")
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",forbidden)
    # Exercise real mobile metadata as well as the two-sided history.
    data = api_client.post("/ai/chat",headers=headers,json={"messages":[
        {"role":"user","content":"Cancel that income"},
        {"role":"assistant","content":"Okay, I've canceled that income. Nothing was saved."},
        {"role":"user","content":answer+"\n[Currency for untagged amounts in this message: AED]"}]}).json()
    assert "canceled" in data["reply"] and data["record_state"] is None and data["proposal"] is None


def test_legacy_model_fallback_consumes_the_same_draft_identity(db_session, cancellation, monkeypatch):
    _, _, _, ask = cancellation
    draft = RecordDraft(source="paid 50 Food",amount_text="50",category="Food",category_text="Food",currency="AED")
    token = seal_draft(draft,1)
    def unavailable(*args):
        raise ValueError("Offline semantic interpreter")
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",unavailable)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_: json.dumps({"reply":"Review","action":{"kind":"expense","amount":50,"category":"Food","date":"today"},"planning":None}))
    completed = ask("Record AED 50 for Food today",record_state=token).json()
    assert completed["proposal"]["id"] == draft.draft_id
    assert ask("Today",record_state=token).status_code == 422


def test_successful_completed_draft_confirmation_remains_idempotent(api_client, db_session, cancellation):
    headers, _, _, ask = cancellation
    draft = RecordDraft(source="paid 50 lunch",amount_text="50",category="Food",category_text="lunch",currency="AED")
    token = seal_draft(draft,1)
    data = ask("Today",record_state=token).json()
    path = f"/ai/proposals/{data['proposal']['id']}/confirm"
    assert api_client.post(path,headers=headers).status_code == 200
    assert api_client.post(path,headers=headers).status_code == 200
    assert ask("Today",record_state=token).status_code == 422
    assert db_session.query(Transaction).count() == 1
