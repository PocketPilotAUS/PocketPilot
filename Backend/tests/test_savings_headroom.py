"""Authoritative planned headroom, independent of actual spending and deposits."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.financial_plan import FinancialPlan
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction
from app.models.savings import ManualSavings, MonthlySavings
from app.models.debt_payment import DebtPayment
from app.services.budget_goals import draft_plan, assess
from app.core.currency import display_context

GOAL={"goal":"Laptop","goal_kind":"savings","target_amount":"5000","monthly_contribution":"600","current_amount":"0"}


@pytest.fixture
def account(api_client):
    register_user(api_client)
    headers=auth_headers(login_user(api_client).json()["access_token"])
    today=datetime.now(timezone(timedelta(hours=4))).date()
    def budget(income=10000,categories=None,loan=True):
        categories=categories or [{"name":"Rent","amount":5000},{"name":"Food","amount":1420}]
        response=api_client.put(f"/budget/setup?year={today.year}&month={today.month}",headers=headers,json={"income":float(income),"categories":categories})
        assert response.status_code==200,response.text
        if loan:
            response=api_client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60})
            assert response.status_code==201,response.text
        return api_client.get(f"/budget/monthly?year={today.year}&month={today.month}",headers=headers).json()
    return headers,today,budget


@pytest.mark.parametrize("loan,manual_debt,included_in_6420,expected", [
    (True,False,False,2413.86),(False,False,False,2980),
    (True,True,False,2413.86),(False,True,False,2413.86),(True,True,True,2980)])
def test_laptop_600_counts_budget_debt_once(account,loan,manual_debt,included_in_6420,expected):
    _,today,setup=account
    categories=[{"name":"Rent","amount":5000},{"name":"Food","amount":853.86 if included_in_6420 else 1420}]
    if manual_debt:
        categories.append({"name":"Debt","amount":566.14})
    budget=setup(categories=categories,loan=loan)
    plan=draft_plan(GOAL,budget,today)
    assert plan["targetAmount"]==5000 and plan["monthlyContribution"]==600
    assert plan["months"]==9
    assert plan["remainingAfterSavings"]==expected
    assert Decimal(str(plan["availableAfter"]))-600==Decimal(str(expected))
    debt_rows=[row for row in plan["allocations"] if row["category"]=="Debt"]
    assert len(debt_rows)==int(loan or manual_debt)
    if debt_rows:
        assert debt_rows[0]["target"]==566.14
    if loan and not included_in_6420:
        assert plan["baselineSpending"]==6986.14 and plan["availableBefore"]==3013.86


@pytest.mark.parametrize("capacity", [-100,0,500,600])
def test_zero_insufficient_and_exact_headroom(account,capacity):
    _,today,setup=account
    budget=setup(income=Decimal("6986.14")+capacity)
    result=assess(GOAL,budget,today)
    assert result["availableAfter"]==capacity
    assert result["unfundedMonthly"]==max(0,600-capacity)
    plan=draft_plan(GOAL,budget,today)
    if capacity<600:
        assert plan is None
    else:
        assert plan["remainingAfterSavings"]==0


def test_actual_transactions_do_not_reduce_planned_headroom_again(account,api_client):
    headers,today,setup=account
    budget=setup()
    before=draft_plan(GOAL,budget,today)
    assert api_client.post("/transactions/",headers=headers,json={"amount":300,"category":"Food","date":today.isoformat()}).status_code==201
    budget=api_client.get(f"/budget/monthly?year={today.year}&month={today.month}",headers=headers).json()
    after=draft_plan(GOAL,budget,today)
    assert budget["spent"]==300 and budget["remaining"]==9700
    for key in ("baselineSpending","availableAfter","monthlyContribution","remainingAfterSavings"):
        assert before[key]==after[key]


def test_accepted_budget_cuts_precede_contribution_deduction(account):
    _,today,setup=account
    budget=setup()
    plan=draft_plan(GOAL,budget,today,{"targets":{"Food":1320}})
    assert plan["availableBefore"]==3013.86 and plan["availableAfter"]==3113.86
    assert plan["remainingAfterSavings"]==2513.86


def test_acceptance_persists_plan_only_and_is_idempotent(account,api_client,db_session):
    headers,today,setup=account
    budget=setup()
    plan=draft_plan(GOAL,budget,today)
    request={"profile":plan["profile"],"choices":plan["budgetChoices"],"budget_fingerprint":plan["budgetFingerprint"],"request_key":plan["confirmationKey"]}
    reviewed=api_client.post("/planning/budget-plans/preview",headers=headers,json=request)
    assert reviewed.status_code==200,reviewed.text
    plan=reviewed.json()
    request.update(profile=plan["profile"],choices=plan["budgetChoices"],request_key=plan["confirmationKey"])
    for _ in range(2):
        response=api_client.post("/planning/budget-plans",headers=headers,json=request)
        assert response.status_code==201,response.text
        saved=response.json()
        assert saved["monthlyContribution"]==600 and saved["remainingAfterSavings"]==2413.86
        assert saved["savedAmount"]==0 and saved["contributedAmount"]==0
    assert db_session.query(FinancialPlan).count()==1
    assert db_session.query(Transaction).count()==db_session.query(ManualSavings).count()==db_session.query(MonthlySavings).count()==db_session.query(DebtPayment).count()==0
    assert db_session.query(MonthlyIncome).one().amount_cents==1000000
    assert api_client.get(f"/budget/monthly?year={today.year}&month={today.month}",headers=headers).json()["ideal_budget"]==budget["ideal_budget"]


def test_old_saved_snapshot_gets_explicit_headroom_without_new_financial_records(account,api_client,db_session):
    headers,today,setup=account
    plan=draft_plan(GOAL,setup(),today)
    del plan["remainingAfterSavings"]
    row=FinancialPlan(id=plan["confirmationKey"],user_id=1,payload=json.dumps(plan))
    db_session.add(row);db_session.commit()
    listed=api_client.get("/planning/plans",headers=headers).json()[0]
    assert listed["remainingAfterSavings"]==2413.86
    assert "remainingAfterSavings" not in json.loads(db_session.get(FinancialPlan,row.id).payload)
    assert db_session.query(ManualSavings).count()==0


def test_headroom_uses_shared_currency_projection(account):
    _,today,setup=account
    plan=draft_plan(GOAL,setup(),today)
    projected=display_context(plan,Decimal("2"))
    assert projected["remainingAfterSavings"]==4827.72 and projected["availableAfter"]==6027.72


def test_exact_two_message_chat_uses_verified_headroom(account,api_client,monkeypatch):
    headers,_,setup=account
    setup()
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",lambda *_:json.dumps(dict(intent="plan",topic="savings",continuation=True,kind=None,amount_text=None,category_text=None,category=None,clarification=None,savings_operation="goal")))
    monkeypatch.setattr("app.routers.chat.extract_goal_facts",lambda messages:json.dumps(GOAL if len(messages)>1 else {"goal":"Laptop","goal_kind":"savings","target_amount":5000}))
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_:json.dumps({"reply":"Review the plan.","planning":None,"action":None}))
    history=[{"role":"user","content":"I want to save 5,000 AED for a laptop."}]
    first=api_client.post("/ai/chat",headers=headers,json={"messages":history,"require_budget":True}).json()
    assert first["plan"] is None
    history += [{"role":"assistant","content":first["reply"]},{"role":"user","content":"Let's save 600 AED per month."}]
    response=api_client.post("/ai/chat",headers=headers,json={"messages":history,"goal_planning":first["goal_planning"],"planning_profile":first["planning_profile"],"require_budget":True})
    assert response.status_code==200,response.text
    plan=response.json()["plan"]
    assert plan["targetAmount"]==5000 and plan["monthlyContribution"]==600
    assert plan["remainingAfterSavings"]==2413.86
