import json
from sqlalchemy import inspect
from app.models.budget_plan import BudgetPlan
from app.routers.recurring import sync_recurring
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction
from app.services.debt_payments import monthly_cents

router = APIRouter(prefix="/budget", tags=["Monthly budget"])


class IncomeInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(ge=0, le=1000000000, max_digits=12, decimal_places=2, allow_inf_nan=False)


def summary(db, user_id, year, month, *, include_debt=False):
    from app.services.debt_schedule import sync
    sync(db, user_id)
    sync_recurring(db, user_id)
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    rows = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date < end).all()
    categories = {}
    for row in rows:
        categories[row.category] = categories.get(row.category, Decimal(0)) + Decimal(str(row.amount))
    # Savings and spending-monitor callers account for debt separately. Only
    # dashboard responses opt into the combined cash-outflow totals.
    if include_debt:
        debt_paid = Decimal(monthly_cents(db, user_id, year, month)) / 100
        debt_categories = [key for key in categories if key.strip().casefold() == "debt"]
        debt_total = debt_paid + sum((categories.pop(key) for key in debt_categories), Decimal(0))
        if debt_total:
            categories["Debt"] = debt_total
    spent = sum(categories.values(), Decimal(0)).quantize(Decimal("0.01"))
    income = db.query(MonthlyIncome).filter_by(user_id=user_id, year=year, month=month).first()
    amount = Decimal(income.amount_cents) / 100 if income else None
    return {"year": year, "month": month, "income": float(amount) if amount is not None else None,
            "spent": float(spent), "remaining": float(amount - spent) if amount is not None else None,
            "spent_percentage": float(spent / amount * 100) if amount else None,
            "ideal_budget": ideal_budget(db, user_id, year, month, amount, categories, automatic_debt=include_debt),
            "category_spending": {key: float(value) for key, value in categories.items()},
            "category_percentages": {key: round(float(value / spent * 100), 2) for key, value in categories.items()} if spent else {}}


@router.get("/monthly")
def monthly(current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    return summary(db, current_user.id, year, month, include_debt=True)


@router.put("/income")
def save_income(body: IncomeInput, current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=year, month=month).first()
    if income is None:
        income = MonthlyIncome(user_id=current_user.id, year=year, month=month)
        db.add(income)
    income.amount_cents = int(body.amount * 100)
    db.commit()
    return summary(db, current_user.id, year, month, include_debt=True)

DEFAULT_PERCENTAGES = {"Rent": 30, "Food": 10, "Transport": 5, "Bills": 5, "Shopping": 10, "Entertainment": 10, "Subscriptions": 5, "Other": 5, "Savings / debt": 20}

class PlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    percentages: dict[str, StrictInt]

    @classmethod
    def validate_percentages(cls, values):
        if set(values) != set(DEFAULT_PERCENTAGES) or any(type(value) is not int or value < 0 or value > 100 for value in values.values()) or sum(values.values()) != 100:
            raise ValueError("Allocations must include all categories and total 100%")


def with_debt_budget(db, user_id, year, month, income, categories, budget):
    # Derive the target from loans on every read; never create paid transactions
    # or save a stale copy of the automatically managed category.
    from app.models.debt import Debt
    from app.routers.debts import estimate
    debts = db.query(Debt).filter_by(user_id=user_id).all() if inspect(db.get_bind()).has_table("debts") else []
    if not debts:
        return budget
    from app.models.debt_payment import DebtPayment
    from sqlalchemy import func
    from app.services.debt_schedule import totals
    target = Decimal(0)
    for debt in debts:
        remaining, fixed = totals(db, debt)
        # Keep this month's target after its payment is made, including payoff.
        # Only payments from earlier months reduce the opening monthly balance.
        baseline = debt.total_due_cents
        if baseline is None:
            baseline = round((Decimal(str(debt.balance)) + Decimal(str(estimate(debt.balance, debt.annual_rate, debt.remaining_months)[1]))) * 100)
        earlier = db.query(func.coalesce(func.sum(DebtPayment.applied_cents), 0)).filter(
            DebtPayment.user_id == user_id, DebtPayment.debt_id == debt.id,
            DebtPayment.paid_on < date(year, month, 1)).scalar()
        target += Decimal(min(fixed, max(0, baseline - earlier))) / 100
    result = dict(budget or {"customized": False, "mode": "amounts", "allocations": []})
    allocations = [dict(row) for row in result["allocations"] if row["category"].strip().casefold() != "debt"]
    actual = sum((value for key, value in categories.items() if key.strip().casefold() == "debt"), Decimal(0))
    allocations.append({"category": "Debt", "target": float(target), "spent": float(actual),
                        "percentage": float(target / income * 100) if income else 0, "automatic": True})
    result["allocations"] = allocations
    result["unbudgeted"] = [row for row in result.get("unbudgeted", []) if row["category"].strip().casefold() != "debt"]
    total = sum((Decimal(str(row["target"])) for row in allocations if row["target"] is not None), Decimal(0))
    result.update(planned_total=float(total), planned_remaining=float(income - total) if income is not None else None)
    return result


def ideal_budget(db, user_id, year, month, income, categories, *, automatic_debt=True):
    budget = saved_ideal_budget(db, user_id, year, month, income, categories)
    return with_debt_budget(db, user_id, year, month, income, categories, budget) if automatic_debt else budget


def saved_ideal_budget(db, user_id, year, month, income, categories):
    plan = db.query(BudgetPlan).filter_by(user_id=user_id, year=year, month=month).first() if inspect(db.get_bind()).has_table("budget_plans") else None
    if plan is None:
        return None
    payload = json.loads(plan.percentages)
    if payload.get("version") == 2:
        configured = payload["categories"]
        targets = {row["name"]: Decimal(row["amount"]) for row in configured}
        actuals = {key: Decimal(0) for key in targets}
        unbudgeted = {}
        for key, value in categories.items():
            match = next((name for name in targets if name.casefold() == key.strip().casefold()), None)
            if match is None:
                unbudgeted[key] = unbudgeted.get(key, Decimal(0)) + value
            else:
                actuals[match] += value
        total = sum(targets.values(), Decimal(0))
        return {"customized": True, "mode": "amounts", "planned_total": float(total),
                "planned_remaining": float(income - total) if income is not None else None,
                "unbudgeted": [{"category": key, "spent": float(value)} for key, value in unbudgeted.items()],
                "allocations": [{"category": key, "percentage": float(target / income * 100) if income else 0,
                                  "target": float(target), "spent": float(actuals[key])} for key, target in targets.items()]}
    # Preserve explicitly saved older budgets; never generate a default for new users.
    percentages = payload
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


class CategoryBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=40)
    amount: Decimal = Field(ge=0, le=1000000000, decimal_places=2, max_digits=12, allow_inf_nan=False)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value or not value.isprintable():
            raise ValueError("Enter a valid category name.")
        return value


class BudgetSetup(BaseModel):
    model_config = ConfigDict(extra="forbid")
    income: Decimal = Field(ge=0, le=1000000000, decimal_places=2, max_digits=12, allow_inf_nan=False)
    categories: list[CategoryBudget] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def unique_categories(self):
        names = [category.name.casefold() for category in self.categories]
        if len(names) != len(set(names)):
            raise ValueError("Each category must have a different name.")
        return self


@router.put("/setup")
def setup(body: BudgetSetup, current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    # Income and budget are saved together; no paid transactions are created.
    income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=year, month=month).first()
    if income is None:
        income = MonthlyIncome(user_id=current_user.id, year=year, month=month)
        db.add(income)
    income.amount_cents = int(body.income * 100)
    plan = db.query(BudgetPlan).filter_by(user_id=current_user.id, year=year, month=month).first()
    if plan is None:
        plan = BudgetPlan(user_id=current_user.id, year=year, month=month)
        db.add(plan)
    # Keep the month's accepted AI adjustment history when the budget is edited
    history = json.loads(plan.percentages).get("adjustments") if plan.percentages else None
    from app.models.debt import Debt
    automatic_debt = inspect(db.get_bind()).has_table("debts") and db.query(Debt).filter_by(user_id=current_user.id).first() is not None
    plan.percentages = json.dumps({"version": 2, "categories": [{"name": category.name, "amount": str(category.amount)} for category in body.categories
                                                             if not (automatic_debt and category.name.casefold() == "debt")],
                                   **({"adjustments": history} if history else {})})
    db.commit()
    return summary(db, current_user.id, year, month, include_debt=True)


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
    return summary(db, current_user.id, year, month, include_debt=True)
