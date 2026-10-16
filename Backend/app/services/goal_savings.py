"""Manual savings entries assigned to savings-goal plans.

A plan's stored savedAmount is the progress the user entered when the plan
was created. Entries the user assigns to the plan are added on read, so each
entry counts once, toward at most one goal, and edits or deletions are
reflected everywhere without rewriting the saved plan.
"""
import json
from sqlalchemy import func, inspect
from app.models.financial_plan import FinancialPlan
from app.models.savings import ManualSavings


def is_savings_goal(plan):
    return plan.get("kind") == "savings"


def savings_goal(db, user_id, goal_id):
    """The user's own savings-goal plan, or None."""
    row = db.query(FinancialPlan).filter_by(user_id=user_id, id=goal_id).first()
    return row if row is not None and is_savings_goal(json.loads(row.payload)) else None


def assignable(db):
    """False until migrate_savings_goals.py has added the goal_id column."""
    bind = inspect(db.get_bind())
    return bind.has_table("manual_savings") and "goal_id" in {column["name"] for column in bind.get_columns("manual_savings")}


def contributions(db, user_id):
    """Assigned manual savings in cents, by goal id."""
    if not assignable(db):
        return {}
    rows = db.query(ManualSavings.goal_id, func.sum(ManualSavings.amount_cents)).filter(
        ManualSavings.user_id == user_id, ManualSavings.goal_id.isnot(None)).group_by(ManualSavings.goal_id).all()
    return {goal_id: total for goal_id, total in rows}


def with_progress(plan, contributed_cents):
    """Plan with assigned savings added to its progress (savings goals only)."""
    if not is_savings_goal(plan):
        return plan
    base = round(float(plan.get("savedAmount") or 0), 2)
    contributed = (contributed_cents or 0) / 100
    return dict(plan, enteredSavedAmount=base, contributedAmount=contributed, savedAmount=round(base + contributed, 2))


def goal_summaries(db, user_id):
    """Savings goals with their current progress, for assigning savings."""
    totals = contributions(db, user_id)
    goals = []
    for row in db.query(FinancialPlan).filter_by(user_id=user_id).order_by(FinancialPlan.id).all():
        plan = json.loads(row.payload)
        if not is_savings_goal(plan):
            continue
        plan = with_progress(plan, totals.get(row.id))
        target = round(float(plan.get("targetAmount") or 0), 2)
        goals.append({"id": row.id, "title": plan.get("title"), "target": target, "saved": plan["savedAmount"],
                      "remaining": round(max(0.0, target - plan["savedAmount"]), 2)})
    return goals
