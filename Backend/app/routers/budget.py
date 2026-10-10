import json
from sqlalchemy import inspect
from app.models.budget_plan import BudgetPlan
from app.routers.recurring import sync_recurring
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction

router = APIRouter(prefix="/budget", tags=["Monthly budget"])


class IncomeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(ge=0, le=1000000000, max_digits=12, decimal_places=2, allow_inf_nan=False)


def summary(db, user_id, year, month):
    sync_recurring(db, user_id)
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    rows = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date < end).all()
    categories = {}
    for row in rows:
        categories[row.category] = categories.get(row.category, Decimal(0)) + Decimal(str(row.amount))
    spent = sum(categories.values(), Decimal(0)).quantize(Decimal("0.01"))
    income = db.query(MonthlyIncome).filter_by(user_id=user_id, year=year, month=month).first()
    amount = Decimal(income.amount_cents) / 100 if income else None
    return {"year": year, "month": month, "income": float(amount) if amount is not None else None,
            "spent": float(spent), "remaining": float(amount - spent) if amount is not None else None,
            "spent_percentage": float(spent / amount * 100) if amount else None,
            "ideal_budget": ideal_budget(db, user_id, year, month, amount, categories),
            "category_spending": {key: float(value) for key, value in categories.items()},
            "category_percentages": {key: round(float(value / spent * 100), 2) for key, value in categories.items()} if spent else {}}


@router.get("/monthly")
def monthly(current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    return summary(db, current_user.id, year, month)


@router.put("/income")
def save_income(body: IncomeInput, current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=year, month=month).first()
    if income is None:
        income = MonthlyIncome(user_id=current_user.id, year=year, month=month)
        db.add(income)
    income.amount_cents = int(body.amount * 100)
    db.commit()
    return summary(db, current_user.id, year, month)

DEFAULT_PERCENTAGES = {"Rent": 30, "Food": 10, "Transport": 5, "Bills": 5, "Shopping": 10, "Entertainment": 10, "Subscriptions": 5, "Other": 5, "Savings / debt": 20}

class PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    percentages: dict[str, StrictInt]

    @classmethod
    def validate_percentages(cls, values):
        if set(values) != set(DEFAULT_PERCENTAGES) or any(type(value) is not int or value < 0 or value > 100 for value in values.values()) or sum(values.values()) != 100:
            raise ValueError("Allocations must include all categories and total 100%")


def ideal_budget(db, user_id, year, month, income, categories):
    plan = db.query(BudgetPlan).filter_by(user_id=user_id, year=year, month=month).first() if inspect(db.get_bind()).has_table("budget_plans") else None
    percentages = json.loads(plan.percentages) if plan else DEFAULT_PERCENTAGES
    actuals = {key: Decimal(0) for key in percentages}
    aliases = {"groceries": "Food", "transportation": "Transport", "utilities": "Bills", "housing": "Rent"}
    for key, value in categories.items():
        category = aliases.get(key.strip().lower()) or next((name for name in percentages if name.lower() == key.strip().lower()), "Other")
        actuals[category] += value
    targets = {key: (income * Decimal(value) / 100).quantize(Decimal("0.01")) if income is not None else None for key, value in percentages.items()}
    if income is not None:
        # Allocate rounding remainder so targets sum exactly to income.
        remainder = income - sum(targets.values())
        largest = max(targets, key=targets.get)
        targets[largest] += remainder
    return {"customized": plan is not None, "allocations": [{"category": key, "percentage": value, "target": float(targets[key]) if targets[key] is not None else None, "spent": float(actuals[key])} for key, value in percentages.items()]}


@router.put("/plan")
def save_plan(body: PlanInput, current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    from fastapi import HTTPException
    try:
        PlanInput.validate_percentages(body.percentages)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    plan = db.query(BudgetPlan).filter_by(user_id=current_user.id, year=year, month=month).first()
    if plan is None:
        plan = BudgetPlan(user_id=current_user.id, year=year, month=month)
        db.add(plan)
    plan.percentages = json.dumps(body.percentages)
    db.commit()
    return summary(db, current_user.id, year, month)