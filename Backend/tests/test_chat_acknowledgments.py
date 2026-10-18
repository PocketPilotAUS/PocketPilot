"""Mocked semantic outputs; real proposal persistence, ownership and confirmation."""
import json
import time
from datetime import date
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.chat_proposal import ChatProposal
from app.models.transaction import Transaction
from app.models.income import MonthlyIncome
from app.routers.proposals import ProposedAction, create_proposal


@pytest.fixture
def acknowledgments(api_client, monkeypatch):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    calls = []
    choice = [dict(intent="record", topic="budget", continuation=True, kind="expense",
                   amount_text=None, category_text=None, category=None, clarification=None)]
    def interpret(messages, context):
        calls.append(context)
        return json.dumps(choice[0])
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", interpret)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda *_: json.dumps({
        "reply":"Here is the explanation you requested.", "action":None, "planning":None}))
    def ask(text="Yes.", history=(), **fields):
        return api_client.post("/ai/chat",headers=headers,json={"messages":[*history,
            {"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"}],**fields})
    return headers, choice, calls, ask


def pending(db, kind):
    return create_proposal(db,1,ProposedAction(kind=kind,amount=50,category="Food" if kind=="expense" else None,
        date=date(2026,10,18),year=2026 if kind=="income" else None,month=10 if kind=="income" else None,
        income_operation="add" if kind=="income" else "replace",income_after=50 if kind=="income" else None))


def no_new_record(db, data, expected_proposals=1):
    assert data["proposal"] is None and data["record_state"] is None and data["plan"] is None
    assert db.query(ChatProposal).count() == expected_proposals


@pytest.mark.parametrize("kind", ["expense","income"])
@pytest.mark.parametrize("text", ["Yes.", "yep", "Okay", "sure please"])
def test_pending_acknowledgment_uses_owned_details_without_model_or_writes(acknowledgments,db_session,kind,text):
    _, _, calls, ask = acknowledgments
    proposal = pending(db_session,kind)
    before = db_session.get(ChatProposal,proposal["id"]).payload
    data = ask(text,active_proposal_id=proposal["id"]).json()
    assert "AED 50.00" in data["reply"] and "2026-10-18" in data["reply"]
    assert "still pending" in data["reply"] and "Confirm" in data["reply"] and "Dismiss" in data["reply"]
    if kind=="expense":
        assert "Food" in data["reply"]
    else:
        assert "one-time" in data["reply"]
    assert not calls
    no_new_record(db_session,data)
    assert db_session.get(ChatProposal,proposal["id"]).payload == before
    assert db_session.query(Transaction).count() == db_session.query(MonthlyIncome).count() == 0


@pytest.mark.parametrize("kind", ["expense","income"])
def test_exact_two_message_c1_then_button_confirmation_is_idempotent(acknowledgments,api_client,db_session,kind):
    headers, choice, calls, ask = acknowledgments
    choice[0].update(kind=kind,amount_text="50",category_text="lunch" if kind=="expense" else None,
                     category="Food" if kind=="expense" else None,income_operation="add" if kind=="income" else None)
    text = "I spent 50 on lunch today." if kind=="expense" else "I earned 50 yesterday."
    first = ask(text).json()
    proposal = first["proposal"]
    assert proposal and proposal["status"] == "pending"
    choice[0].update(amount_text=None,category_text=None,category=None)
    data = ask(history=[{"role":"user","content":text},{"role":"assistant","content":first["reply"]}],
               active_proposal_id=proposal["id"]).json()
    no_new_record(db_session,data)
    assert "still pending" in data["reply"] and len(calls)==1
    assert db_session.query(Transaction).count() == db_session.query(MonthlyIncome).count() == 0
    for _ in range(2):
        assert api_client.post(f"/ai/proposals/{proposal['id']}/confirm",headers=headers).status_code==200
    db_session.expire_all()
    assert db_session.query(Transaction).count() == (1 if kind=="expense" else 0)
    assert db_session.query(MonthlyIncome).count() == (1 if kind=="income" else 0)
    after = ask(active_proposal_id=proposal["id"]).json()
    assert "already saved" in after["reply"]
    no_new_record(db_session,after)


@pytest.mark.parametrize("kind", ["expense","income"])
@pytest.mark.parametrize("status", ["dismissed","expired","saved"])
def test_terminal_proposals_cannot_be_revived(acknowledgments,api_client,db_session,kind,status):
    headers, _, calls, ask = acknowledgments
    proposal = pending(db_session,kind)
    if status=="expired":
        row=db_session.get(ChatProposal,proposal["id"])
        payload=json.loads(row.payload); payload["_expires_at"]=time.time()-1
        row.payload=json.dumps(payload); db_session.commit()
    else:
        endpoint="confirm" if status=="saved" else "dismiss"
        assert api_client.post(f"/ai/proposals/{proposal['id']}/{endpoint}",headers=headers).status_code==200
    counts=(db_session.query(Transaction).count(),db_session.query(MonthlyIncome).count())
    for _ in range(2):
        data=ask(active_proposal_id=proposal["id"]).json()
        assert status in data["reply"]
        assert "still pending" not in data["reply"]
        assert data["proposal_updates"]==[{"id":proposal["id"],"status":status}]
        no_new_record(db_session,data)
    assert not calls
    db_session.expire_all()
    assert db_session.get(ChatProposal,proposal["id"]).status==status
    assert counts==(db_session.query(Transaction).count(),db_session.query(MonthlyIncome).count())
    assert api_client.post(f"/ai/proposals/{proposal['id']}/confirm",headers=headers).status_code==(200 if status=="saved" else 409)


def test_acknowledgment_without_proposal_or_question_is_neutral(acknowledgments,db_session):
    _, _, calls, ask=acknowledgments
    data=ask(history=[{"role":"user","content":"What's my income?"},{"role":"assistant","content":"Your income is AED 10000."}]).json()
    assert "What would you like" in data["reply"] and not calls
    no_new_record(db_session,data,0)


@pytest.mark.parametrize("with_proposal", [False,True])
def test_yes_to_explicit_explanation_question_still_works(acknowledgments,db_session,with_proposal):
    _, choice, calls, ask=acknowledgments
    choice[0].update(intent="read",kind=None)
    proposal=pending(db_session,"expense") if with_proposal else None
    data=ask(history=[{"role":"user","content":"Explain interest."},
                     {"role":"assistant","content":"Would you like me to explain how interest is calculated?"}],
             active_proposal_id=proposal["id"] if proposal else None).json()
    assert "explanation" in data["reply"] and len(calls)==1
    no_new_record(db_session,data,1 if with_proposal else 0)


def test_model_cannot_turn_explicit_question_answer_into_new_expense(acknowledgments,db_session):
    _, _, calls, ask=acknowledgments
    proposal=pending(db_session,"expense")
    data=ask(history=[{"role":"user","content":"Explain this."},{"role":"assistant","content":"Would you like an explanation?"}],
             active_proposal_id=proposal["id"]).json()
    assert "still pending" in data["reply"] and len(calls)==1
    no_new_record(db_session,data)


def test_pending_reminder_uses_selected_currency_conversion(acknowledgments,db_session):
    _, _, _, ask=acknowledgments
    proposal=pending(db_session,"expense")
    data=ask(active_proposal_id=proposal["id"],currency="CNY",aed_to_cny=2).json()
    assert "CNY 100.00" in data["reply"] and "AED" not in data["reply"]
    no_new_record(db_session,data)


def test_other_account_proposal_is_not_disclosed(acknowledgments,api_client,db_session):
    _, _, calls, _=acknowledgments
    proposal=pending(db_session,"expense")
    register_user(api_client,email="other@example.com")
    headers=auth_headers(login_user(api_client,email="other@example.com").json()["access_token"])
    result=api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Yes."}],
                 "active_proposal_id":proposal["id"]})
    assert result.status_code==404 and not calls
    assert db_session.query(Transaction).count()==0
