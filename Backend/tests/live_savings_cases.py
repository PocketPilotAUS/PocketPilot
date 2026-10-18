"""Opt-in real Ollama savings API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_savings_cases.py --live [--no-think]
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
            client.post("/auth/register", json={"name":"Savings live","email":"income-live@example.com","password":"income-live-test-2026"})
            token = client.post("/auth/login", json={"email":"income-live@example.com","password":"income-live-test-2026"}).json()["access_token"]
            headers = {"Authorization":"Bearer " + token}
            today = datetime.now(timezone(timedelta(hours=4))).date()
            client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers, json={"income":10000,
                "categories":[{"name":"Rent","amount":5000},{"name":"Food","amount":1420}]})
            cases = [
                ("S1", ["I wanna save 5k for a laptop.", "Let's do 800 a month.", "Actually make it 600 instead."], "goal"),
                ("S2", ["I want to save more, but don't change my rent."], "protected"),
                ("S3", ["Can I save 1k a month?"], "affordability"),
                ("put away", ["Could I put away 800 every month?"], "affordability"),
                ("realistic", ["Would saving 1,500 monthly be realistic?"], "affordability"),
                ("unspecified period", ["Can I afford to save 2k?", "Monthly."], "affordability"),
            ]
            for name, turns, expected in cases:
                history, profile, goal_mode, passed = [], None, False, True
                for index, text in enumerate(turns):
                    history.append({"role":"user","content":text + " [Currency for untagged amounts in this message: AED]"})
                    response = client.post("/ai/chat", headers=headers, json={"messages":history,
                        "planning_profile":profile,"goal_planning":goal_mode,"require_budget":True})
                    data = response.json()
                    print(json.dumps({"case":name,"text":text,"status":response.status_code,"reply":data.get("reply",data.get("detail")),
                        "plan":{key:data["plan"].get(key) for key in ("title","targetAmount","monthlyContribution","months","deadline")} if data.get("plan") else None,"profile":data.get("planning_profile")}), flush=True)
                    if response.status_code != 200:
                        passed = False; break
                    history.append({"role":"assistant","content":data["reply"]})
                    profile = data.get("planning_profile"); goal_mode = data.get("goal_planning",False)
                    passed &= data.get("proposal") is None
                    if expected == "goal":
                        passed &= bool(profile) and "laptop" in str(profile.get("goal", "")).lower() and Decimal(str(profile.get("target_amount", -1))) == 5000
                        if index:
                            plan = data.get("plan") or {}
                            passed &= plan.get("monthlyContribution") == (800 if index == 1 else 600)
                        else:
                            passed &= data.get("plan") is None
                    elif expected == "protected":
                        passed &= data.get("plan") is None and "Rent" in (data.get("budget_goal") or {}).get("protected",[])
                    else:
                        passed &= data.get("plan") is None and profile is None
                        if index == len(turns)-1:
                            expected_left = {"S3":"2,580.00","put away":"2,780.00","realistic":"2,080.00","unspecified period":"1,580.00"}[name]
                            passed &= all(n in data["reply"] for n in ("10,000.00","6,420.00","3,580.00",expected_left))
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
