"""Opt-in real Ollama savings headroom API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_savings_headroom.py --live [--no-think]
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
            from app.models.financial_plan import FinancialPlan
            from app.models.savings import ManualSavings, MonthlySavings
            from app.models.debt_payment import DebtPayment
            loan=client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60})
            assert loan.status_code==201,loan.text
            history=[];carried={}
            for text in ("I want to save 5,000 AED for a laptop.","Let's save 600 AED per month."):
                history.append({"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"})
                response=client.post("/ai/chat",headers=headers,json={"messages":history,"require_budget":True,**carried})
                assert response.status_code==200,response.text
                data=response.json()
                print(json.dumps({"text":text,"reply":data["reply"],"plan":data.get("plan")}),flush=True)
                assert data.get("proposal") is None
                history.append({"role":"assistant","content":data["reply"]})
                carried={key:data.get(key) for key in ("planning_profile","goal_planning","record_state","debt_state")}
            plan=data.get("plan")
            assert plan and plan["targetAmount"]==5000 and plan["monthlyContribution"]==600
            assert plan["months"]==9
            assert plan["baselineSpending"]==6986.14 and plan["availableBefore"]==3013.86
            assert plan["availableAfter"]==3013.86 and plan["remainingAfterSavings"]==2413.86
            request={"profile":plan["profile"],"choices":plan["budgetChoices"],"budget_fingerprint":plan["budgetFingerprint"],"request_key":plan["confirmationKey"]}
            for _ in range(2):
                confirmed=client.post("/planning/budget-plans",headers=headers,json=request)
                assert confirmed.status_code==201,confirmed.text
                assert confirmed.json()["remainingAfterSavings"]==2413.86
            listed=client.get("/planning/plans",headers=headers).json()
            assert len(listed)==1 and listed[0]["monthlyContribution"]==600 and listed[0]["savedAmount"]==0
            with factory() as db:
                counts={model.__name__:db.query(model).count() for model in (FinancialPlan,Transaction,ManualSavings,MonthlySavings,DebtPayment)}
                assert counts=={"FinancialPlan":1,"Transaction":0,"ManualSavings":0,"MonthlySavings":0,"DebtPayment":0},counts
                assert db.query(MonthlyIncome).one().amount_cents==1000000
                print(json.dumps({"C4":"PASS","confirmed_records":counts,"remainingAfterSavings":listed[0]["remainingAfterSavings"]}),flush=True)
    finally:
        app.dependency_overrides.clear();engine.dispose()
    return bool(failures)


if __name__=="__main__":
    raise SystemExit(main())
