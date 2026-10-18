"""Opt-in real Ollama confirmation acknowledgment API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_chat_acknowledgments.py --live [--no-think]
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
            from app.models.transaction import Transaction
            import time
            import app.routers.chat as chat
            real_interpret = chat.interpret_chat_turn
            interpretations = []
            def trace(messages, context):
                raw = real_interpret(messages, context)
                interpretations.append(json.loads(raw))
                print(json.dumps({"interpretation": interpretations[-1]}),flush=True)
                return raw
            chat.interpret_chat_turn = trace
            def ask(text, history=(), **fields):
                response = client.post("/ai/chat",headers=headers,json={"messages":[*history,
                    {"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"}],**fields})
                assert response.status_code == 200, response.text
                return response.json()
            for kind, text in (("expense","I spent 50 on lunch today."),("income","I earned 50 yesterday.")):
                first = ask(text)
                proposal = first.get("proposal")
                passed = bool(proposal and proposal["kind"]==kind and proposal["status"]=="pending")
                if not passed:
                    failures += 1
                    print(json.dumps({"case":kind+" initial proposal","passed":False,"data":first}),flush=True)
                    continue
                history=[{"role":"user","content":text},{"role":"assistant","content":first["reply"]}]
                before_calls=len(interpretations)
                reply=ask("Yes.",history,active_proposal_id=proposal["id"])
                passed &= "still pending" in reply["reply"] and "Confirm" in reply["reply"] and "Dismiss" in reply["reply"]
                passed &= reply.get("proposal") is None and reply.get("record_state") is None and len(interpretations)==before_calls
                with factory() as db:
                    passed &= db.query(Transaction).count()==0
                    passed &= db.query(MonthlyIncome).filter_by(year=today.year,month=today.month).one().amount_cents==1000000
                failures += not passed
                print(json.dumps({"case":"C1 "+kind,"passed":bool(passed),"reply":reply["reply"]}),flush=True)
                endpoint="dismiss" if kind=="expense" else "confirm"
                assert client.post(f"/ai/proposals/{proposal['id']}/{endpoint}",headers=headers).status_code==200
                reply=ask("Yes.",history,active_proposal_id=proposal["id"])
                expected="dismissed" if kind=="expense" else "already saved"
                passed=expected in reply["reply"] and reply.get("proposal") is None and reply.get("record_state") is None
                repeat=client.post(f"/ai/proposals/{proposal['id']}/confirm",headers=headers)
                passed &= repeat.status_code==(409 if kind=="expense" else 200)
                failures += not passed
                print(json.dumps({"case":kind+" "+endpoint+" then Yes","passed":bool(passed),"reply":reply["reply"]}),flush=True)
            first=ask("I spent 50 on lunch today.")
            proposal=first.get("proposal")
            passed=bool(proposal)
            if proposal:
                with factory() as db:
                    row=db.get(ChatProposal,proposal["id"])
                    payload=json.loads(row.payload);payload["_expires_at"]=time.time()-1
                    row.payload=json.dumps(payload);db.commit()
                reply=ask("Yes.",active_proposal_id=proposal["id"])
                passed &= "expired" in reply["reply"] and reply.get("proposal") is None and reply.get("record_state") is None
                passed &= client.post(f"/ai/proposals/{proposal['id']}/confirm",headers=headers).status_code==409
                print(json.dumps({"case":"expired Yes","passed":bool(passed),"reply":reply["reply"]}),flush=True)
            failures += not passed
            reply=ask("Yes.")
            passed="What would you like" in reply["reply"] and reply.get("proposal") is None and reply.get("record_state") is None
            failures += not passed
            print(json.dumps({"case":"neutral Yes","passed":bool(passed),"reply":reply["reply"]}),flush=True)
            reply=ask("Yes.",history=[{"role":"user","content":"Explain interest."},
                {"role":"assistant","content":"Would you like me to explain how interest is calculated?"}])
            passed=reply.get("proposal") is None and reply.get("record_state") is None and "interest" in reply["reply"].lower() and "What would you like" not in reply["reply"]
            failures += not passed
            print(json.dumps({"case":"explicit explanation question Yes","passed":bool(passed),"reply":reply["reply"]}),flush=True)
            with factory() as db:
                income=db.query(MonthlyIncome).filter_by(year=today.year,month=today.month).one().amount_cents
                transactions=db.query(Transaction).count()
                passed=transactions==0 and income==1005000
                failures += not passed
                print(json.dumps({"only_button_confirmed_income":income/100,"expense_records":transactions,"passed":passed}),flush=True)
    finally:
        app.dependency_overrides.clear(); engine.dispose()
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
