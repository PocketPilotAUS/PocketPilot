"""Opt-in real Ollama confirmation acknowledgment API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_proposal_references.py --live [--no-think]
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
            for status in ("pending","dismissed","expired","saved"):
                first=client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"I spent 50 on lunch today."}]}).json()
                proposal=first.get("proposal")
                assert proposal,first
                if status in ("dismissed","saved"):
                    assert client.post(f"/ai/proposals/{proposal['id']}/"+("dismiss" if status=="dismissed" else "confirm"),headers=headers).status_code==200
                elif status=="expired":
                    with factory() as db:
                        row=db.get(ChatProposal,proposal["id"]);raw=json.loads(row.payload)
                        raw["_expires_at"]=time.time()-1;row.payload=json.dumps(raw);db.commit()
                budget_messages=[{"role":"user","content":"I spent 50 on lunch today."},{"role":"assistant","content":first["reply"]},
                    {"role":"user","content":"How is my budget?"}]
                budget_response=client.post("/ai/chat",headers=headers,json={"messages":budget_messages,"proposal_ids":[proposal["id"]],"active_proposal_id":proposal["id"]})
                assert budget_response.status_code==200,budget_response.text
                budget_reply=budget_response.json()["reply"]
                for text in ("Can you confirm that expense now?","Confirm the previous transaction.","Can you confirm it?"):
                    history=[{"role":"user","content":"I spent 50 on lunch today."},{"role":"assistant","content":first["reply"]},
                        {"role":"user","content":"How is my budget?"},{"role":"assistant","content":budget_reply},
                        {"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"}]
                    response=client.post("/ai/chat",headers=headers,json={"messages":history,"proposal_ids":[proposal["id"]],"active_proposal_id":proposal["id"]})
                    data=response.json()
                    passed=response.status_code==200 and data.get("proposal") is None and data.get("record_state") is None and data.get("plan") is None
                    passed &= ("still pending" if status=="pending" else status) in data.get("reply","")
                    passed &= data.get("proposal_updates")==[{"id":proposal["id"],"status":status}]
                    failures+=not passed
                    print(json.dumps({"case":status,"text":text,"passed":bool(passed),"reply":data.get("reply")}),flush=True)
                if status in ("dismissed","expired"):
                    assert client.post(f"/ai/proposals/{proposal['id']}/confirm",headers=headers).status_code==409
            other=client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Spent 75 on transport today."}]}).json()["proposal"]
            for name,ids in (("new chat",[]),("ambiguous",[proposal["id"],other["id"]])):
                response=client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Can you confirm it?"}],"proposal_ids":ids})
                data=response.json()
                passed=response.status_code==200 and data.get("proposal") is None and data.get("record_state") is None and not data.get("proposal_updates")
                passed &= ("in this chat" in data.get("reply","")) if not ids else ("Which proposal" in data.get("reply",""))
                failures+=not passed
                print(json.dumps({"case":name,"passed":bool(passed),"reply":data.get("reply")}),flush=True)
            with factory() as db:
                count=db.query(Transaction).count()
                print(json.dumps({"only_button_confirmed_transactions":count}),flush=True)
                failures+=count!=1
    finally:
        app.dependency_overrides.clear();engine.dispose()
    return bool(failures)


if __name__=="__main__":
    raise SystemExit(main())
