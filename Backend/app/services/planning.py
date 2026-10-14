import json
from app.routers.budget import ideal_budget
from datetime import date
from decimal import Decimal, ROUND_UP
from sqlalchemy import inspect
from app.models.financial_plan import PlanningProfile
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction
from app.models.recurring import RecurringExpense
from app.schemas.planning import PlanningInput, CATEGORIES

ALIASES = {"groceries": "Food", "food and groceries": "Food", "housing": "Rent", "transportation": "Transport", "fuel": "Transport", "utilities": "Bills", "internet": "Bills", "loans": "Debt payments"}


def category_name(value):
    key = value.strip().lower()
    return ALIASES.get(key) or next((x for x in CATEGORIES if x.lower() == key), "Other")


def profile_data(db, user_id):
    if not inspect(db.get_bind()).has_table("planning_profiles"):
        return {}
    row = db.get(PlanningProfile, user_id)
    return json.loads(row.payload) if row else {}


def planning_context(db, user_id, today=None):
    today = today or date.today()
    current_month = today.strftime("%Y-%m")
    history = {}
    for row in db.query(Transaction).filter_by(user_id=user_id).all():
        month = row.date.strftime("%Y-%m")
        if month >= current_month:
            continue
        bucket = history.setdefault(month, {})
        name = category_name(row.category)
        bucket[name] = bucket.get(name, Decimal(0)) + Decimal(str(row.amount))
    history = {month: {key: float(value) for key, value in history[month].items()} for month in sorted(history, reverse=True)[:12]}
    income = db.query(MonthlyIncome).filter_by(user_id=user_id, year=today.year, month=today.month).first()
    monthly_income = (
        Decimal(income.amount_cents) / 100
        if income
        else None
    )

    budget = ideal_budget(
        db,
        user_id,
        today.year,
        today.month,
        monthly_income,
        {},
    )

    saved_budget = None

    if budget is not None:
        saved_budget = {
            "year": today.year,
            "month": today.month,
            "income": (
                float(monthly_income)
                if monthly_income is not None
                else None
            ),
            "expenses": {
                row["category"]: row["target"]
                for row in budget["allocations"]
                if row["target"] is not None
                and row["category"] != "Savings / debt"
            },
        }
    recurring = {}
    if inspect(db.get_bind()).has_table("recurring_expenses"):
        for row in db.query(RecurringExpense).filter_by(user_id=user_id, active=True).all():
            key = category_name(row.category)
            recurring[key] = round(recurring.get(key, 0) + row.amount_cents / 100, 2)
    return {
    "profile": profile_data(db, user_id),
    "current_income": (
        income.amount_cents / 100 if income else None
    ),
    "saved_budget": saved_budget,
    "past_months": history,
    "recurring_obligations": recurring,
    "note": (
        "Recorded months may be incomplete. "
        "Recurring obligations are estimates of commitments, "
        "not extra spending to add to transaction totals."
    ),
}


def baseline(profile, context):
    expenses = {}
    sources = {}

    categories = list(dict.fromkeys([
        *CATEGORIES,
        *profile.expenses.keys(),
    ]))

    for key in categories:
        supplied = profile.expenses.get(key)

        if supplied is not None:
            expenses[key] = supplied
            sources[key] = "user estimate"

        elif profile.typical_months:
            expenses[key] = (
                sum(
                    (
                        Decimal(
                            str(context["past_months"][month].get(key, 0))
                        )
                        for month in profile.typical_months
                    ),
                    Decimal(0),
                ) / len(profile.typical_months)
            ).quantize(Decimal("0.01"))

            sources[key] = "average of confirmed typical months"

        else:
            expenses[key] = None
            sources[key] = "unknown"

    return expenses, sources


def evaluate(profile, context, today=None):
    from app.algorithms.budget_engine import calculate_plan
    today = today or date.today()
    if any(month not in context["past_months"] for month in profile.typical_months):
        raise ValueError("Select recorded past months from the history list")
    expenses, sources = baseline(profile, context)
    missing = [key for key in ("income", "other_income", "household_size", "goal", "goal_kind", "target_amount") if getattr(profile, key) is None]
    missing += [f"monthly {key}" for key, value in expenses.items() if value is None]
    if profile.goal_kind in ("savings", "debt") and profile.current_amount is None:
        missing.append("current_amount")
    if profile.goal_kind in ("savings", "debt") and profile.deadline is None:
        missing.append("deadline")
    if missing:
        return {"ready": False, "missing": missing, "profile": json.loads(profile.model_dump_json()), "history": context["past_months"]}
    return calculate_plan(profile, expenses, sources, context, today)
