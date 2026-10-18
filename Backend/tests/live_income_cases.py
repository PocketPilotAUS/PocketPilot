"""Opt-in real Ollama income API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_income_cases.py --live [--no-think]
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
                ("I1", ["I earned 2k yesterday."], "receipt"),
                ("I2", ["What's my income?"], "lookup"),
                ("I3", ["How would recording 2,000 income affect my budget?"], "scenario"),
                ("got paid", ["got paid 2k yesterday"], "receipt"),
                ("received", ["I received 2000 yesterday"], "receipt"),
                ("follow-up", ["I earned 2k", "Yesterday."], "receipt"),
                ("negative", ["I don't want to record 2k income today"], "negative"),
            ]
            for name, turns, expected in cases:
                history, state, passed = [], None, True
                for index, text in enumerate(turns):
                    history.append({"role":"user","content":text})
                    response = client.post("/ai/chat", headers=headers, json={"messages":history,"record_state":state,"require_budget":True})
                    data = response.json()
                    print(json.dumps({"case":name,"text":text,"status":response.status_code,"reply":data.get("reply",data.get("detail")),
                        "proposal":data.get("proposal"),"has_draft":bool(data.get("record_state"))}), flush=True)
                    if response.status_code != 200:
                        passed = False; break
                    history.append({"role":"assistant","content":data["reply"]}); state = data.get("record_state")
                    if index < len(turns)-1:
                        passed &= data.get("proposal") is None and bool(state)
                    elif expected == "receipt":
                        proposal = data.get("proposal") or {}
                        passed &= (proposal.get("kind") == "income" and proposal.get("income_operation") == "add"
                            and Decimal(str(proposal.get("amount",-1))) == 2000 and proposal.get("status") == "pending"
                            and proposal.get("date") == (today-timedelta(days=1)).isoformat())
                    elif expected == "lookup":
                        passed &= data.get("proposal") is None and "10,000.00" in data["reply"]
                    elif expected == "scenario":
                        passed &= data.get("proposal") is None and all(number in data["reply"] for number in
                            ("10,000.00","6,420.00","3,580.00","12,000.00","5,580.00")) and "one-time" in data["reply"] and "recurr" in data["reply"]
                    else:
                        passed &= data.get("proposal") is None
                failures += not passed
                print(f"{name}: {'PASS' if passed else 'FAIL'}", flush=True)
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
