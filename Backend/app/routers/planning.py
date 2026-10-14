import json
from uuid import uuid4
from datetime import date, datetime, timedelta, timezone
from pydantic import BaseModel, ConfigDict, Field
from app.routers.chat import BudgetChoices
from app.routers.budget import ideal_budget
from app.models.income import MonthlyIncome
from decimal import Decimal
from app.services.budget_goals import draft_plan, fingerprint
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.financial_plan import PlanningProfile, FinancialPlan
from app.schemas.planning import PlanningInput
from app.services.planning import planning_context, evaluate

router = APIRouter(prefix="/planning", tags=["Financial plans"])


def calculate(body, db, user_id):
    try:
        return evaluate(body, planning_context(db, user_id))
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


def save_profile(db, user_id, body):
    row = db.get(PlanningProfile, user_id)
    if row is None:
        row = PlanningProfile(user_id=user_id)
        db.add(row)
    row.payload = body.model_dump_json()


@router.get("/context")
def context(current_user: CurrentUser, db: Session = Depends(get_db)):
    return planning_context(db, current_user.id)


@router.put("/profile")
def profile(body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    result = calculate(body, db, current_user.id)
    save_profile(db, current_user.id, body)
    db.commit()
    return result


@router.post("/preview")
def preview(body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return calculate(body, db, current_user.id)


@router.get("/plans")
def plans(current_user: CurrentUser, db: Session = Depends(get_db)):
    return [dict(json.loads(row.payload), id=row.id) for row in db.query(FinancialPlan).filter_by(user_id=current_user.id).order_by(FinancialPlan.id).all()]


def persist(body, db, user_id, row=None):
    result = calculate(body, db, user_id)
    if not result["ready"]:
        raise HTTPException(422, "Complete the household, goal and monthly expenses first")
    result["createdOn"] = date.today().isoformat()
    if row is None:
        row = FinancialPlan(id=str(uuid4()), user_id=user_id)
        db.add(row)
    row.payload = json.dumps(result)
    save_profile(db, user_id, body)
    db.commit()
    return dict(result, id=row.id)


@router.post("/plans", status_code=201)
def create(body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return persist(body, db, current_user.id)


def owned(db, user_id, plan_id):
    row = db.query(FinancialPlan).filter_by(user_id=user_id, id=plan_id).first()
    if not row:
        raise HTTPException(404, "Plan not found")
    return row


@router.put("/plans/{plan_id}")
def update(plan_id: str, body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return persist(body, db, current_user.id, owned(db, current_user.id, plan_id))


@router.delete("/plans/{plan_id}", status_code=204)
def delete(plan_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.delete(owned(db, current_user.id, plan_id))
    db.commit()


class BudgetGoalSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: PlanningInput
    choices: BudgetChoices = Field(default_factory=BudgetChoices)
    budget_fingerprint: str = Field(min_length=64, max_length=64)
    request_key: UUID


def persist_budget_goal(body, user_id, db, existing=None):
    today = datetime.now(timezone(timedelta(hours=4))).date()
    request_key = str(body.request_key)
    facts = json.dumps({"profile": body.profile.model_dump(mode="json"), "choices": body.choices.model_dump(mode="json"), "budget": body.budget_fingerprint}, sort_keys=True)
    def retry(row):
        data = json.loads(row.payload)
        if row.user_id != user_id or data.get("confirmationFacts") != facts:
            raise HTTPException(409, "This confirmation was already used. Review a new draft.")
        return dict(data, id=row.id)
    if existing is None:
        previous = db.get(FinancialPlan, request_key)
        if previous:
            return retry(previous)
    income = db.query(MonthlyIncome).filter_by(user_id=user_id, year=today.year, month=today.month).first()
    amount = Decimal(income.amount_cents) / 100 if income else None
    budget = {"year": today.year, "month": today.month, "income": float(amount) if amount is not None else None,
              "ideal_budget": ideal_budget(db, user_id, today.year, today.month, amount, {})}
    if budget["ideal_budget"] is None or budget["income"] is None:
        raise HTTPException(422, "Save your monthly budget before confirming a plan.")
    if fingerprint(budget) != body.budget_fingerprint:
        raise HTTPException(409, "Your budget changed. Ask AI Chat to refresh the plan before confirming.")
    result = draft_plan(body.profile.model_dump(mode="json"), budget, today, body.choices.model_dump(mode="json"))
    if result is None:
        raise HTTPException(422, "Review the goal, monthly contribution and deadline before confirming.")
    result.update(confirmationKey=request_key, confirmationFacts=facts, createdOn=today.isoformat())
    row = existing or FinancialPlan(id=request_key, user_id=user_id)
    row.payload = json.dumps(result)
    if existing is None:
        db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.get(FinancialPlan, request_key)
        if previous is None:
            raise
        return retry(previous)
    return dict(result, id=row.id)


@router.post("/budget-plans", status_code=201)
def confirm_budget_plan(body: BudgetGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    user_id = current_user.id
    db.commit()
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import text
        db.execute(text("BEGIN IMMEDIATE"))
    return persist_budget_goal(body, user_id, db)


@router.put("/budget-plans/{plan_id}")
def update_budget_goal(plan_id: str, body: BudgetGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    user_id = current_user.id
    db.commit()
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import text
        db.execute(text("BEGIN IMMEDIATE"))
    row = owned(db, user_id, plan_id)
    if not json.loads(row.payload).get("budgetGoalSource"):
        raise HTTPException(422, "Use the regular editor for this plan.")
    return persist_budget_goal(body, user_id, db, row)


@router.post("/budget-plans/preview")
def preview_budget_goal(body: BudgetGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    today = datetime.now(timezone(timedelta(hours=4))).date()
    income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=today.year, month=today.month).first()
    amount = Decimal(income.amount_cents) / 100 if income else None
    budget = {"year": today.year, "month": today.month, "income": float(amount) if amount is not None else None,
              "ideal_budget": ideal_budget(db, current_user.id, today.year, today.month, amount, {})}
    if budget["ideal_budget"] is None or amount is None:
        raise HTTPException(422, "Save your monthly budget before reviewing a plan.")
    choices = body.choices.model_dump(mode="json")
    if body.budget_fingerprint != fingerprint(budget):
        choices["targets"] = {}
    result = draft_plan(body.profile.model_dump(mode="json"), budget, today, choices)
    if result is None:
        raise HTTPException(422, "Choose a complete goal and an affordable monthly amount or future deadline.")
    return result
