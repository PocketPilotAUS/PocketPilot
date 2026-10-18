"""Opt-in real Ollama record cancellation API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_record_cancellation.py --live [--no-think]
Does not confirm proposals or write to production accounts/databases.
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
            cases = [
                ("R4", ["I spent 50 on lunch today.", "Actually, I don't want to record this expense.", "Yes."]),
                ("income cancellation", ["I earned 2k yesterday.", "Actually don't record that income.", "Yes."]),
                ("incomplete expense", ["I just bought groceries for 120.", "Cancel that expense.", "Today."]),
                ("incomplete income", ["I earned 2k", "Never mind, cancel that income.", "Yesterday."]),
            ]
            for name, turns in cases:
                history, state, proposal_id, passed = [], None, None, True
                old_state = None
                for index, text in enumerate(turns):
                    history.append({"role":"user","content":text+"\n[Currency for untagged amounts in this message: AED]"})
                    response = client.post("/ai/chat",headers=headers,json={"messages":history,"record_state":state,"active_proposal_id":proposal_id})
                    data = response.json()
                    print(json.dumps({"case":name,"text":text,"status":response.status_code,"reply":data.get("reply"),"proposal":data.get("proposal"),"updates":data.get("proposal_updates")}),flush=True)
                    passed &= response.status_code == 200
                    if response.status_code != 200:
                        break
                    history.append({"role":"assistant","content":data["reply"]})
                    state = data.get("record_state")
                    if index == 0:
                        proposal_id = (data.get("proposal") or {}).get("id")
                        old_state = state
                        passed &= bool(proposal_id or state)
                    elif index == 1:
                        passed &= "canceled" in data["reply"] and data.get("proposal") is None and state is None
                        if proposal_id:
                            passed &= data.get("proposal_updates") == [{"id":proposal_id,"status":"dismissed"}]
                    else:
                        passed &= data.get("proposal") is None and state is None
                if proposal_id:
                    replay = client.post(f"/ai/proposals/{proposal_id}/confirm",headers=headers)
                    passed &= replay.status_code == 409
                if old_state:
                    replay = client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Today"}],"record_state":old_state})
                    passed &= replay.status_code == 422
                failures += not passed
                print(f"{name}: {'PASS' if passed else 'FAIL'}",flush=True)
            for question in ("What's my income?", "Explain my monthly car loan payment."):
                response = client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":question}]})
                data = response.json()
                passed = response.status_code == 200 and "$" not in data.get("reply","") and data.get("proposal") is None
                failures += not passed
                print(json.dumps({"case":"currency read-only","text":question,"passed":bool(passed),"reply":data.get("reply")}),flush=True)
            with factory() as db:
                income = db.query(MonthlyIncome).filter_by(user_id=1,year=today.year,month=today.month).one().amount_cents
                saved = db.query(Transaction).count()
                print(json.dumps({"unchanged_monthly_income":income/100,"saved_transactions":saved}), flush=True)
                failures += income != 1000000 or saved != 0
    finally:
        app.dependency_overrides.clear(); engine.dispose()
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
