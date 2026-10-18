"""Opt-in real Ollama Financial Plan rejection and status API regressions in an isolated in-memory account.
From Backend: venv/Scripts/python.exe tests/live_plan_rejection.py --live [--no-think]
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
            from app.models.plan_review import PlanReview
            from app.models.savings import ManualSavings
            from uuid import uuid4
            from app.services.budget_goals import fingerprint
            history=[];carried={}
            for text in ("I want to save 3,000 AED for a vacation.","Let's save 300 AED per month."):
                history.append({"role":"user","content":text+chr(10)+"[Currency for untagged amounts in this message: AED]"})
                response=client.post("/ai/chat",headers=headers,json={"messages":history,"require_budget":True,**carried})
                assert response.status_code==200,response.text
                data=response.json();print(json.dumps({"text":text,"reply":data["reply"],"review":(data.get("plan") or {}).get("reviewId")}),flush=True)
                history.append({"role":"assistant","content":data["reply"]})
                carried={key:data.get(key) for key in ("planning_profile","goal_planning","record_state","debt_state")}
            plan=data["plan"];assert plan and plan["targetAmount"]==3000 and plan["monthlyContribution"]==300
            key=plan["reviewId"]
            for _ in range(2):
                rejected=client.post(f"/planning/reviews/{key}/reject",headers=headers)
                assert rejected.status_code==200 and rejected.json()["status"]=="rejected",rejected.text
            original={"profile":plan["profile"],"choices":plan["budgetChoices"],"budget_fingerprint":plan["budgetFingerprint"],"request_key":plan["confirmationKey"]}
            assert client.post("/planning/budget-plans",headers=headers,json=original).status_code==409
            text="Actually, can you accept that vacation savings plan now?"
            for switched in (False,True):
                if switched:
                    history.append({"role":"user","content":"How is my budget?"})
                    result=client.post("/ai/chat",headers=headers,json={"messages":history,"plan_review_ids":[key],"require_budget":True})
                    assert result.status_code==200,result.text
                    history.append({"role":"assistant","content":result.json()["reply"]})
                history.append({"role":"user","content":text})
                result=client.post("/ai/chat",headers=headers,json={"messages":history,"plan_review_ids":[key],"require_budget":True})
                assert result.status_code==200,result.text
                data=result.json();print(json.dumps({"case":"C5 switched" if switched else "C5 exact","reply":data["reply"],"updates":data.get("plan_updates")}),flush=True)
                assert "rejected" in data["reply"] and "transaction" not in data["reply"].lower()
                assert data.get("plan") is None and data.get("proposal") is None and data.get("record_state") is None
                history.append({"role":"assistant","content":data["reply"]})
                assert client.post(f"/planning/reviews/{key}/accept",headers=headers,json={}).status_code==409
            budget=client.get(f"/budget/monthly?year={today.year}&month={today.month}",headers=headers).json()
            for state in ("pending","saved","expired"):
                response=client.post("/planning/budget-plans/preview",headers=headers,json={"profile":plan["profile"],
                    "choices":{},"budget_fingerprint":fingerprint(budget),"request_key":str(uuid4())})
                assert response.status_code==200,response.text
                current=response.json();review=current["reviewId"]
                if state=="saved":
                    for _ in range(2):
                        accepted=client.post(f"/planning/reviews/{review}/accept",headers=headers,json={})
                        assert accepted.status_code==200,accepted.text
                elif state=="expired":
                    with factory() as db:
                        row=db.get(PlanReview,review);payload=json.loads(row.payload);payload["expires_at"]=1
                        row.payload=json.dumps(payload);db.commit()
                response=client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Can you accept that vacation savings plan now?"}],
                    "plan_review_ids":[review]})
                assert response.status_code==200,response.text
                data=response.json()
                assert ("already accepted" if state=="saved" else state) in data["reply"],data
                assert data.get("plan") is None and data.get("proposal") is None
                print(json.dumps({"case":state,"reply":data["reply"]}),flush=True)
            with factory() as db:
                counts={"plans":db.query(FinancialPlan).count(),"expenses":db.query(Transaction).count(),"deposits":db.query(ManualSavings).count()}
                assert counts=={"plans":1,"expenses":0,"deposits":0},counts
                assert db.query(MonthlyIncome).one().amount_cents==1000000
                print(json.dumps({"C5":"PASS","records":counts}),flush=True)
    finally:
        app.dependency_overrides.clear();engine.dispose()
    return bool(failures)


if __name__=="__main__":
    raise SystemExit(main())
