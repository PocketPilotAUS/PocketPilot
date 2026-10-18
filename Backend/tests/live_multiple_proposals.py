"""Opt-in real Ollama C7 multiple-proposal API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_multiple_proposals.py --live [--no-think]
Uses only an isolated in-memory account; confirmation tests never touch production data.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--no-think", action="store_true")
    args = parser.parse_args()
    if args.no_think:
        os.environ["OLLAMA_THINK"] = "false"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import Base, get_db
    from app.models.income import MonthlyIncome
    from app.models.transaction import Transaction
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine); factory = sessionmaker(bind=engine, autoflush=False)
    def isolated():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = isolated
    failures = 0
    try:
        with TestClient(app) as client:
            client.post("/auth/register", json={"name":"Income live","email":"income-live@example.com","password":"income-live-test-2026"})
            token = client.post("/auth/login", json={"email":"income-live@example.com","password":"income-live-test-2026"}).json()["access_token"]
            headers = {"Authorization":"Bearer " + token}
            today = datetime.now(timezone(timedelta(hours=4))).date()
            client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers, json={"income":10000,
                "categories":[{"name":"Rent","amount":5000},{"name":"Food","amount":1420}]})
            from app.models.chat_proposal import ChatProposal
            import time
            import app.routers.chat as chat
            real=chat.interpret_chat_turn
            def trace(messages,context):
                result=real(messages,context)
                print(json.dumps({"interpretation":json.loads(result)}),flush=True)
                return result
            chat.interpret_chat_turn=trace
            from app.models.chat_proposal import ChatProposal
            from app.models.transaction import Transaction
            for wording in ("I also spent 25 AED on transport today.", "Another expense: 25 AED for transport today.", "Plus 25 for transport today."):
                history, ids = [], []
                def ask(text):
                    response=client.post("/ai/chat",headers=headers,json={"messages":[*history,{"role":"user","content":text}],
                        "proposal_ids":ids, **({"active_proposal_id":ids[-1]} if ids else {})})
                    assert response.status_code==200,response.text
                    data=response.json()
                    history.extend([{"role":"user","content":text},{"role":"assistant","content":data["reply"]}])
                    if data.get("proposal"):
                        ids.append(data["proposal"]["id"])
                    print(json.dumps({"text":text,"reply":data["reply"],"proposal":data.get("proposal"),"updates":data["proposal_updates"]}),flush=True)
                    return data
                first=ask("I spent 40 AED on groceries today.")
                assert first.get("proposal"),first
                second=ask(wording)
                passed=bool(second.get("proposal")) and Decimal(second["proposal"]["amount"])==25 and second["proposal"]["category"]=="Transport" and second["proposal"]["date"]==today.isoformat() and len(set(ids))==2
                print(json.dumps({"case":wording,"passed":passed}),flush=True)
                failures+=not passed
                if not passed:
                    continue
                reference=ask("Can you confirm the 40 AED groceries expense?")
                assert not reference.get("proposal") and reference["proposal_updates"]==[{"id":ids[0],"status":"pending"}],reference
                canceled=ask("Actually, cancel the 40 AED groceries expense.")
                assert canceled["proposal_updates"]==[{"id":ids[0],"status":"dismissed"}],canceled
                with factory() as db:
                    assert db.get(ChatProposal,ids[1]).status=="pending"
                    assert db.query(Transaction).count()==0
                assert client.post(f"/ai/proposals/{ids[0]}/confirm",headers=headers).status_code==409
            # Terminal proposals must not contaminate a subsequent fresh expense.
            for state in ("dismissed", "saved", "expired"):
                history, ids = [], []
                first=ask("I spent 40 AED on groceries today.")
                assert first.get("proposal"),first
                if state=="expired":
                    with factory() as db:
                        row=db.get(ChatProposal,ids[0]);raw=json.loads(row.payload)
                        raw["_expires_at"]=time.time()-1;row.payload=json.dumps(raw);db.commit()
                    assert client.post(f"/ai/proposals/{ids[0]}/confirm",headers=headers).status_code==409
                else:
                    endpoint="confirm" if state=="saved" else "dismiss"
                    assert client.post(f"/ai/proposals/{ids[0]}/{endpoint}",headers=headers).status_code==200
                second=ask("I also spent 25 AED on transport today.")
                passed=bool(second.get("proposal")) and len(set(ids))==2 and Decimal(second["proposal"]["amount"])==25
                with factory() as db:
                    passed=passed and db.get(ChatProposal,ids[0]).status==state and db.get(ChatProposal,ids[-1]).status=="pending"
                failures+=not passed
                print(json.dumps({"case":"new expense after "+state,"passed":bool(passed)}),flush=True)
            history, ids = [], []
            assert ask("I spent 40 AED on groceries today.").get("proposal")
            assert ask("I also spent 25 AED on transport today.").get("proposal")
            correction=ask("Actually change the transport expense to 30 AED.")
            with factory() as db:
                passed=not correction.get("proposal") and not correction.get("record_state") and len(ids)==2 and all(db.get(ChatProposal,key).status=="pending" for key in ids)
            failures+=not passed
            print(json.dumps({"case":"correction is not a separate expense","passed":bool(passed)}),flush=True)
            with factory() as db:
                assert db.query(Transaction).count()==1  # Only the explicit Confirm above.
            print(json.dumps({"failures":failures}),flush=True)
    finally:
        app.dependency_overrides.clear();engine.dispose()
    return bool(failures)


if __name__=="__main__":
    raise SystemExit(main())
