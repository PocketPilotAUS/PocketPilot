"""Opt-in real Ollama debt API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_debt_cases.py --live [--no-think]
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
            from app.services.debt_planning import unseal, snapshot, scenario
            from app.routers.budget import summary
            from app.models.debt_payment import DebtPayment
            from app.models.financial_plan import FinancialPlan
            import app.routers.chat as chat
            import app.services.debt_planning as debt_planning
            real_route, real_debt = chat.interpret_chat_turn, debt_planning.interpret_debt_turn
            def route(*args):
                raw = real_route(*args)
                print(json.dumps({"routing":json.loads(raw)}), flush=True)
                return raw
            def debt(*args):
                raw = real_debt(*args)
                print(json.dumps({"debt_interpretation":json.loads(raw),"interpreter_debts":args[1].get("debts")}), flush=True)
                return raw
            chat.interpret_chat_turn, debt_planning.interpret_debt_turn = route, debt
            loan_response = client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60})
            assert loan_response.status_code == 201, loan_response.text
            loan = loan_response.json()
            print(json.dumps({"saved_loan":loan}), flush=True)
            turns = ["I wanna pay off my car loan faster.", "Could I finish it in two years?", "Actually, let's do three."]
            history, state = [], None
            for index, text in enumerate(turns):
                history.append({"role":"user","content":text+"\n[Currency for untagged amounts in this message: AED]"})
                response = client.post("/ai/chat",headers=headers,json={"messages":history,"debt_state":state,"require_budget":True})
                data = response.json()
                state = data.get("debt_state")
                details = unseal(state,1,"debt_conversation") if state else {}
                calculated = None
                if state:
                    with factory() as db:
                        budget = summary(db,1,today.year,today.month,include_debt=True)
                        saved = snapshot(db,1,budget,today,details.get("debt_ids"))
                        calculated = scenario(saved,details.get("deadline"),details.get("chosen"),today)
                passed = response.status_code == 200 and state and details.get("debt_ids") == [loan["id"]] and data.get("proposal") is None and data.get("plan") is None
                if index:
                    passed = passed and calculated and calculated["months"] == (24 if index == 1 else 36)
                failures += not passed
                print(json.dumps({"case":f"D1.{index+1}","passed":bool(passed),"text":text,"reply":data.get("reply"),"state":details,"scenario":calculated}),flush=True)
                history.append({"role":"assistant","content":data.get("reply", "No response")})
            for name, text in [
                ("lookup", "What's my car loan balance?"),
                ("education", "Explain how debt payments work."),
                ("payment boundary", "Record the 600 I paid to my car loan today"),
            ]:
                response = client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":text}],"require_budget":True})
                data = response.json()
                passed = response.status_code == 200 and data.get("plan") is None and data.get("proposal") is None and data.get("debt_state") is None
                if name == "lookup":
                    passed &= "30,000" in data.get("reply","") or "30000" in data.get("reply","")
                if name == "payment boundary":
                    passed &= "debt" in data.get("reply","").lower()
                failures += not passed
                print(json.dumps({"case":name,"passed":bool(passed),"reply":data.get("reply")}),flush=True)
            client.post("/debts",headers=headers,json={"name":"Car Loan - Honda","balance":20000,"annual_rate":4,"remaining_months":48})
            response = client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"I wanna pay off my car loan faster."}],"require_budget":True})
            data = response.json()
            selected = unseal(data["debt_state"],1,"debt_conversation") if data.get("debt_state") else {}
            passed = response.status_code == 200 and selected.get("debt_ids") == [] and "Which saved loan" in data.get("reply","") and data.get("plan") is None
            failures += not passed
            print(json.dumps({"case":"ambiguous car loans","passed":bool(passed),"reply":data.get("reply")}),flush=True)
            client.post("/auth/register",json={"name":"Empty debts","email":"no-debt@example.com","password":"live-test-2026"})
            other_token = client.post("/auth/login",json={"email":"no-debt@example.com","password":"live-test-2026"}).json()["access_token"]
            other_headers = {"Authorization":"Bearer "+other_token}
            client.put(f"/budget/setup?year={today.year}&month={today.month}",headers=other_headers,json={"income":10000,"categories":[{"name":"Rent","amount":5000}]})
            response = client.post("/ai/chat",headers=other_headers,json={"messages":[{"role":"user","content":"I wanna pay off my car loan faster."}],"require_budget":True})
            data = response.json()
            passed = response.status_code == 200 and "don't have a saved debt" in data.get("reply","") and data.get("plan") is None and "30,000" not in data.get("reply","")
            failures += not passed
            print(json.dumps({"case":"no saved debt / account isolation","passed":bool(passed),"reply":data.get("reply")}),flush=True)
            with factory() as db:
                income = db.query(MonthlyIncome).filter_by(user_id=1,year=today.year,month=today.month).one().amount_cents
                saved = db.query(Transaction).count()
                payments = db.query(DebtPayment).count()
                plans = db.query(FinancialPlan).count()
                print(json.dumps({"unchanged_monthly_income":income/100,"saved_transactions":saved,"debt_payments":payments,"saved_plans":plans}), flush=True)
                failures += income != 1000000 or saved != 0 or payments != 0 or plans != 0
    finally:
        app.dependency_overrides.clear(); engine.dispose()
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
