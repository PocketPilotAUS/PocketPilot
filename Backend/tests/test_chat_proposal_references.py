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
@pytest.mark.parametrize("status", ["pending","dismissed","expired","saved"])
@pytest.mark.parametrize("text", ["Can you confirm that expense now?", "Confirm the previous transaction.", "Can you confirm it?"])
def test_reference_uses_persisted_status_after_topic_switch(acknowledgments,api_client,db_session,kind,status,text):
    headers, choice, calls, ask=acknowledgments
    proposal=pending(db_session,kind)
    if status=="expired":
        row=db_session.get(ChatProposal,proposal["id"])
        raw=json.loads(row.payload);raw["_expires_at"]=time.time()-1
        row.payload=json.dumps(raw);db_session.commit()
    elif status!="pending":
        assert api_client.post(f"/ai/proposals/{proposal['id']}/"+("dismiss" if status=="dismissed" else "confirm"),headers=headers).status_code==200
    counts=(db_session.query(Transaction).count(),db_session.query(MonthlyIncome).count())
    # The model identifies the reference, not a fresh incomplete expense.
    text=text.replace("expense","income") if kind=="income" else text
    choice[0].update(intent="proposal",kind=kind,proposal_reference=text)
    history=[{"role":"user","content":"Record a transaction."},{"role":"assistant","content":"Confirm to save."},
             {"role":"user","content":"How is my budget?"},{"role":"assistant","content":"Here is your budget."}]
    data=ask(text,history,proposal_ids=[proposal["id"]]).json()
    assert data["proposal_updates"]==[{"id":proposal["id"],"status":status}]
    assert ("still pending" if status=="pending" else status) in data["reply"]
    if status=="dismissed":
        assert "AED 50.00" in data["reply"] and "can no longer be confirmed" in data["reply"]
    no_new_record(db_session,data)
    db_session.expire_all()
    assert db_session.get(ChatProposal,proposal["id"]).status==status
    assert counts==(db_session.query(Transaction).count(),db_session.query(MonthlyIncome).count())
    assert calls[-1]["proposal_history"][0]["id"]==proposal["id"]


def test_ambiguous_multiple_proposals_are_not_selected_by_model_kind(acknowledgments,db_session):
    _, choice, _, ask=acknowledgments
    expense=pending(db_session,"expense");income=pending(db_session,"income")
    choice[0].update(intent="proposal",kind="expense",proposal_reference="confirm it")
    data=ask("confirm it",proposal_ids=[expense["id"],income["id"]],active_proposal_id=income["id"]).json()
    assert "Which proposal" in data["reply"] and not data["proposal_updates"]
    no_new_record(db_session,data,2)


def test_specific_amount_selects_an_older_proposal(acknowledgments,db_session):
    _, choice, _, ask=acknowledgments
    older=pending(db_session,"expense")
    newer=create_proposal(db_session,1,ProposedAction(kind="expense",amount=75,category="Transport",date=date(2026,10,18)))
    db_session.get(ChatProposal,older["id"]).status="dismissed";db_session.commit()
    choice[0].update(intent="proposal",kind="expense",proposal_reference="confirm the 50 expense",amount_text="50")
    data=ask("confirm the 50 expense",proposal_ids=[older["id"],newer["id"]],active_proposal_id=newer["id"]).json()
    assert data["proposal_updates"]==[{"id":older["id"],"status":"dismissed"}]
    assert "Food" in data["reply"]
    no_new_record(db_session,data,2)


def test_new_chat_does_not_search_account_history(acknowledgments,db_session):
    _, choice, calls, ask=acknowledgments
    pending(db_session,"expense")
    choice[0].update(intent="proposal",proposal_reference="confirm that expense")
    data=ask("confirm that expense").json()
    assert "in this chat" in data["reply"] and "50" not in data["reply"]
    assert calls[-1]["proposal_history"]==[]
    no_new_record(db_session,data)


def test_foreign_history_id_rejected_before_interpretation(acknowledgments,api_client,db_session):
    _, _, calls, _=acknowledgments
    proposal=pending(db_session,"expense")
    register_user(api_client,email="bob@example.com")
    headers=auth_headers(login_user(api_client,email="bob@example.com").json()["access_token"])
    response=api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"confirm it"}],"proposal_ids":[proposal["id"]]})
    assert response.status_code==404 and not calls


def test_invented_reference_cannot_resolve_a_proposal(acknowledgments,db_session):
    _, choice, _, ask=acknowledgments
    proposal=pending(db_session,"expense")
    choice[0].update(intent="proposal",proposal_reference="lunch")
    data=ask("How is my budget?",proposal_ids=[proposal["id"]]).json()
    assert "Which proposal" in data["reply"] and not data["proposal_updates"]
    no_new_record(db_session,data)


def test_new_expense_is_not_treated_as_reference(acknowledgments,db_session):
    _, choice, _, ask=acknowledgments
    old=pending(db_session,"expense")
    choice[0].update(intent="record",amount_text="75",category_text="transport",category="Transport",continuation=False)
    data=ask("Spent 75 on transport today.",proposal_ids=[old["id"]]).json()
    assert data["proposal"]["category"]=="Transport" and Decimal(data["proposal"]["amount"])==75
    assert db_session.query(Transaction).count()==0


@pytest.mark.parametrize("reference", ["Can you confirm that expense now?", "this expense"])
def test_inconsistent_model_fields_cannot_reopen_dismissed_record(acknowledgments,db_session,reference):
    _, choice, _, ask=acknowledgments
    proposal=pending(db_session,"expense")
    db_session.get(ChatProposal,proposal["id"]).status="dismissed";db_session.commit()
    choice[0].update(intent="record",proposal_reference=reference,amount_text="50",category_text="lunch",category="Food")
    data=ask("Can you confirm that expense now?",proposal_ids=[proposal["id"]]).json()
    assert "dismissed" in data["reply"] and "Food" in data["reply"]
    no_new_record(db_session,data)


def test_model_cannot_disambiguate_pronoun_with_invented_category(acknowledgments,db_session):
    _, choice, _, ask=acknowledgments
    one=pending(db_session,"expense")
    two=create_proposal(db_session,1,ProposedAction(kind="expense",amount=75,category="Transport",date=date(2026,10,18)))
    choice[0].update(intent="proposal",proposal_reference="it",category_text="it",category="Food")
    data=ask("confirm it",proposal_ids=[one["id"],two["id"]]).json()
    assert "Which proposal" in data["reply"] and not data["proposal_updates"]
    no_new_record(db_session,data,2)
