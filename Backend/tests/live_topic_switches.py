"""Opt-in real Ollama topic-switch API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_topic_switches.py --live [--no-think]
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
            import app.routers.chat as chat
            real = chat.interpret_chat_turn
            def trace(messages, context):
                result = real(messages, context)
                print(json.dumps({"interpretation":json.loads(result),"has_pending_record":bool(context.get("pending_record"))}),flush=True)
                return result
            chat.interpret_chat_turn = trace
            client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60})
            cases = [
                ("T2", ["I wanna pay off my car loan faster.", "How's my budget looking?", "What's my monthly income?", "800"]),
                ("income lookup", ["What's my monthly income?", "2k"]),
                ("expense lookup", ["How much have I spent on food?", "800"]),
                ("debt lookup", ["What's my car loan balance?", "800"]),
                ("budget lookup", ["How's my budget looking?", "800"]),
                ("T3 savings to income", ["I wanna save 5k for a laptop.", "What's my monthly income?", "800"]),
                ("incomplete income switch", ["I earned 2k.", "How's my budget looking?", "800"]),
                ("incomplete expense switch", ["Lunch was 50.", "What's my monthly income?", "800"]),
                ("valid income amount", ["I got paid yesterday.", "800"]),
                ("valid expense amount", ["I paid for lunch today.", "800"]),
                ("valid savings amount", ["I wanna save 5k for a laptop.", "800"]),
            ]
            for name, turns in cases:
                history, carried, passed = [], {}, True
                for index, text in enumerate(turns):
                    history.append({"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"})
                    response = client.post("/ai/chat",headers=headers,json={"messages":history,**carried,"require_budget":True})
                    data = response.json()
                    print(json.dumps({"case":name,"turn":index+1,"text":text,"status":response.status_code,"reply":data.get("reply"),
                        "record_state":bool(data.get("record_state")),"debt_state":bool(data.get("debt_state")),"plan":bool(data.get("plan")),"proposal":data.get("proposal")}),flush=True)
                    passed &= response.status_code == 200
                    if response.status_code != 200:
                        break
                    history.append({"role":"assistant","content":data["reply"]})
                    carried = {key:data.get(key) for key in ("record_state","debt_state","planning_profile","goal_planning")}
                    if name.startswith("valid"):
                        if index == 0:
                            passed &= bool(data.get("record_state")) if "savings" not in name else bool(data.get("goal_planning"))
                        else:
                            if "savings" in name:
                                plan = data.get("plan") or {}
                                passed &= plan.get("targetAmount") == 5000 and plan.get("monthlyContribution") == 800 and data.get("proposal") is None
                            else:
                                proposal = data.get("proposal") or {}
                                passed &= proposal.get("kind") == ("income" if "income" in name else "expense") and Decimal(str(proposal.get("amount", 0))) == 800 and proposal.get("status") == "pending"
                    else:
                        if index and (index == len(turns)-1 or name in ("T2", "T3 savings to income", "incomplete income switch", "incomplete expense switch")):
                            passed &= data.get("proposal") is None and data.get("record_state") is None and data.get("debt_state") is None and data.get("plan") is None
                        if index == len(turns)-1:
                            passed &= "refer" in data["reply"].lower()
                failures += not passed
                print(f"{name}: {'PASS' if passed else 'FAIL'}",flush=True)
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
