"""This month's spending status against the approved budget and savings goals.

Deterministic and fast: no AI is involved in detecting overspending or risk.

Concepts are kept separate:
  - planned budget: this month's approved category amounts (budget_plans)
  - recorded spending: transactions dated this month
  - committed: recorded spending + debt payments made + upcoming recurring
    bills + unpaid debt instalments (things that will happen regardless)
  - projected: committed, plus forecast remaining spending (see forecast());
    never less than committed
  - required: monthly contributions of active savings goals

Levels:
  0  nothing to report
  1  a category is over budget, but goals remain achievable
  2  a credible projection (moderate or high confidence) leaves less than the
     required contributions
  3  committed spending alone leaves less than the required contributions
     (whatever the forecast confidence)
"""
import calendar
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from sqlalchemy import inspect
from app.models.financial_plan import FinancialPlan
from app.models.recurring import RecurringExpense, RecurringOccurrence
from app.models.transaction import Transaction
from app.routers.budget import summary

CENT = Decimal("0.01")


def money(value):
    return Decimal(str(value or 0)).quantize(CENT, ROUND_HALF_UP)


def _has(db, table):
    return inspect(db.get_bind()).has_table(table)


def upcoming_recurring(db, user_id, today):
    """Active schedules still due later this month (not yet recorded)."""
    if not _has(db, "recurring_expenses"):
        return []
    month_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    rows = db.query(RecurringExpense).filter(RecurringExpense.user_id == user_id, RecurringExpense.active.is_(True),
                                             RecurringExpense.next_date > today, RecurringExpense.next_date <= month_end).all()
    return [{"category": row.category, "amount": float(money(row.amount_cents / 100)), "date": row.next_date.isoformat()} for row in rows]


def debt_dues(db, user_id, year, month, paid, budget_names):
    """Unpaid estimated debt instalments this month (Karim's estimate, read only)."""
    if not _has(db, "debts") or any("debt" in name.casefold() or "loan" in name.casefold() for name in budget_names):
        # A budget category for debt already plans these payments
        return Decimal(0)
    from app.models.debt import Debt
    from app.routers.debts import serialize
    expected = sum((money(serialize(row, db)["estimated_monthly_payment"])
                    for row in db.query(Debt).filter_by(user_id=user_id).all() if row.remaining_months > 0), Decimal(0))
    return max(Decimal(0), expected - paid)


def active_goals(db, user_id, year, month):
    """Savings goals with a monthly contribution due this month."""
    goals = []
    first = f"{year:04d}-{month:02d}-01"
    for row in db.query(FinancialPlan).filter_by(user_id=user_id).order_by(FinancialPlan.id).all():
        plan = json.loads(row.payload)
        if plan.get("kind") != "savings":
            continue
        contribution = money(plan.get("monthlyContribution") or plan.get("requiredMonthly") or 0)
        deadline = plan.get("deadline")
        if contribution <= 0 or (deadline and deadline < first):
            continue
        goals.append({"id": row.id, "title": plan.get("title"), "monthlyContribution": float(contribution)})
    return goals


def accepted_limits(db, user_id, year, month):
    """Accepted spending limits this month, by category (latest wins)."""
    from app.models.budget_plan import BudgetPlan
    row = db.query(BudgetPlan).filter_by(user_id=user_id, year=year, month=month).first() if _has(db, "budget_plans") else None
    payload = json.loads(row.percentages) if row else {}
    history = payload.get("adjustments", []) if isinstance(payload, dict) else []
    return {change["category"].casefold(): money(change.get("limit", change.get("proposed")))
            for entry in history for change in entry.get("changes", [])}


# Forecast settings: how much evidence is needed before using it
HISTORY_MONTHS = 3      # previous months considered
TRACKED_MONTH = 5       # transactions needed for a past month to count as tracked
PACE_MIN_DAYS = 7       # days into the month before the current pace is used
PACE_MIN_COUNT = 2      # variable transactions in a category needed for its pace
OUTLIER_FACTOR = 3      # a purchase over 3x the category's typical one is one-off


def _month_start(year, month, back=0):
    index = year * 12 + month - 1 - back
    return date(index // 12, index % 12 + 1, 1)


def _usual(amounts, pool):
    """amounts without one-off purchases: far above the category's usual size
    (compared with every other amount in pool), they are not repeated daily."""
    kept = []
    for amount in amounts:
        others = list(pool)
        others.remove(amount)
        if not (len(others) >= 3 and amount > OUTLIER_FACTOR * median(others)):
            kept.append(amount)
    return kept


def forecast(db, user_id, today, budget_rows, upcoming):
    """Expected end-of-month spending per category, with its basis and confidence.

    Each category is recorded spending + its upcoming recurring bills + an
    estimate of remaining spending:
      - fixed categories (an active recurring schedule, or paid exactly once in
        every tracked past month) are never extrapolated; a habitual monthly
        payment not yet made this month is expected once, at its usual amount
      - variable categories use the current daily pace (one-off purchases and
        recurring payments excluded) and the typical month from tracked
        history, averaged when both exist, spread over the days left
      - with too little data (low confidence) the remaining planned budget is
        used, as before, and no risk is escalated from it
    Budgets are targets: forecasts are not capped at them.
    """
    start = _month_start(today.year, today.month, HISTORY_MONTHS)
    current_start = _month_start(today.year, today.month)
    next_start = _month_start(today.year + (today.month == 12), today.month % 12 + 1)
    rows = db.query(Transaction).filter(Transaction.user_id == user_id, Transaction.date >= start, Transaction.date < next_start).all()
    generated = set()
    if _has(db, "recurring_occurrences"):
        generated = {item for (item,) in db.query(RecurringOccurrence.transaction_id).join(
            RecurringExpense, RecurringExpense.id == RecurringOccurrence.schedule_id).filter(RecurringExpense.user_id == user_id).all()}
    scheduled = set()
    if _has(db, "recurring_expenses"):
        scheduled = {row.category.casefold() for row in db.query(RecurringExpense).filter_by(user_id=user_id, active=True).all()}
    names = {row["category"].casefold(): row["category"] for row in budget_rows}

    def key(category):
        return names.get(category.strip().casefold(), category.strip())

    current, history, counts = {}, {}, {}
    for row in rows:
        month = (row.date.year, row.date.month)
        counts[month] = counts.get(month, 0) + 1
        item = (money(row.amount), row.id in generated)
        if row.date >= current_start:
            current.setdefault(key(row.category), []).append(item)
        else:
            history.setdefault(key(row.category), {}).setdefault(month, []).append(item)
    tracked = [month for month in sorted(counts) if month < (today.year, today.month) and counts[month] >= TRACKED_MONTH]
    elapsed = today.day
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - elapsed
    variable_count = sum(1 for items in current.values() for amount, auto in items if not auto)
    if len(tracked) >= 2 and elapsed >= 10:
        confidence = "high"
    elif tracked or (elapsed >= 10 and variable_count >= 8):
        confidence = "moderate"
    else:
        confidence = "low"

    results = {}
    categories = (set(names.values()) | set(current) | {key(item["category"]) for item in upcoming}
                  | {name for name, months in history.items() if any(month in tracked for month in months)})
    budgets = {row["category"]: money(row["target"]) for row in budget_rows}
    for category in categories:
        items = current.get(category, [])
        actual = sum((amount for amount, _ in items), Decimal(0))
        bills = sum((money(item["amount"]) for item in upcoming if key(item["category"]) == category), Decimal(0))
        past = {month: [amount for amount, auto in history.get(category, {}).get(month, []) if not auto] for month in tracked}
        habitual = len(tracked) >= 2 and all(len(amounts) == 1 for amounts in past.values())
        if category.casefold() in scheduled or habitual:
            # Fixed: paid once a month, never extrapolated daily
            due = Decimal(0) if items or not habitual or category.casefold() in scheduled else money(median([amounts[0] for amounts in past.values()]))
            results[category] = {"forecast": actual + bills + due, "method": "fixed", "count": len(items)}
            continue
        variable = [amount for amount, auto in items if not auto]
        everything = variable + [amount for amounts in past.values() for amount in amounts]
        usual = _usual(variable, everything)
        estimates = []
        if confidence != "low" and elapsed >= PACE_MIN_DAYS and len(usual) >= PACE_MIN_COUNT:
            estimates.append(sum(usual, Decimal(0)) / elapsed * days_left)
        if tracked:
            # A tracked month without this category counts as zero spending in it
            totals = [sum(_usual(amounts, everything), Decimal(0)) for amounts in past.values()]
            estimates.append(Decimal(str(median(totals))) * days_left / days_in_month)
        if confidence != "low" and estimates:
            remaining, method = sum(estimates, Decimal(0)) / len(estimates), "pace+history" if len(estimates) == 2 else ("history" if tracked else "pace")
        else:
            # Not enough evidence: assume the remaining planned budget, if any
            remaining, method = max(Decimal(0), budgets.get(category, actual) - actual), "budget"
        results[category] = {"forecast": actual + bills + money(remaining), "method": method, "count": len(items)}
    return results, confidence, len(tracked)


def spending_status(db, user_id, today):
    from app.services.debt_payments import monthly_cents
    year, month = today.year, today.month
    data = summary(db, user_id, year, month)
    budget = data["ideal_budget"]
    income = money(data["income"]) if data["income"] is not None else None
    recorded = money(data["spent"])
    paid_debt = money(monthly_cents(db, user_id, year, month) / 100) if _has(db, "debt_payments") else Decimal(0)
    upcoming = upcoming_recurring(db, user_id, today)
    budget_rows = budget["allocations"] if budget and budget.get("mode") == "amounts" else []
    names = [row["category"] for row in budget_rows]
    dues = debt_dues(db, user_id, year, month, paid_debt, names)

    def upcoming_for(name):
        return sum((money(item["amount"]) for item in upcoming if item["category"].casefold() == name.casefold()), Decimal(0))

    forecasts, confidence, history_months = forecast(db, user_id, today, budget_rows, upcoming)
    days_in_month = calendar.monthrange(year, month)[1]
    limits = accepted_limits(db, user_id, year, month)
    categories, over = [], []
    for row in budget_rows:
        target, actual, bills = money(row["target"]), money(row["spent"]), upcoming_for(row["category"])
        floor = actual + bills
        expected = dict(forecasts.get(row["category"], {"forecast": floor, "method": "budget", "count": 0}))
        # What this category still needs this month, by the user's own budget: nothing for fixed
        # bills (counted as paid or upcoming) or a single payment that settled its budget; otherwise
        # the remaining budget, and at least a day-by-day share for the days left (everyday spending
        # continues even when the category is over budget)
        if expected["method"] == "fixed" or (expected["count"] == 1 and actual >= target):
            needed = Decimal(0)
        else:
            needed = max(target - actual - bills, (target * (days_in_month - today.day) / days_in_month).quantize(CENT, ROUND_HALF_UP), Decimal(0))
        if row["category"].casefold() in limits:
            # The user accepted a spending limit for this category: assume they keep to it,
            # never below what is already spent or due
            expected = {"forecast": max(floor, min(expected["forecast"], limits[row["category"].casefold()])), "method": "adjusted"}
            forecasts[row["category"]] = expected
        categories.append({"category": row["category"], "budget": float(target), "spent": float(actual),
                           "upcoming": float(bills), "minimum": float(floor), "remaining": float(target - actual),
                           "forecast": float(max(floor, expected["forecast"])), "method": expected["method"], "still_needed": float(needed)})
        if actual - target * Decimal("1.05") > CENT / 2:
            over.append({"category": row["category"], "budget": float(target), "spent": float(actual), "over": float(actual - target)})
    upcoming_total = sum((money(item["amount"]) for item in upcoming), Decimal(0))

    committed = recorded + paid_debt + upcoming_total + dues
    # Forecasts cover budgeted and unbudgeted categories; known commitments are a floor
    projected = max(committed, sum((item["forecast"] for item in forecasts.values()), Decimal(0)) + paid_debt + dues)
    goals = active_goals(db, user_id, year, month)
    required = sum((money(goal["monthlyContribution"]) for goal in goals), Decimal(0))

    result = {"year": year, "month": month, "days_left": days_in_month - today.day, "days_in_month": days_in_month,
              "income": float(income) if income is not None else None, "has_budget": bool(budget_rows),
              "recorded_spending": float(recorded), "debt_paid": float(paid_debt), "upcoming_bills": upcoming,
              "unpaid_debt_due": float(dues), "committed": float(committed), "projected_spending": float(projected),
              "required_contributions": float(required), "goals": goals, "over_budget": over, "categories": categories,
              "forecast_confidence": confidence, "history_months": history_months}
    if income is None:
        # Without income there is no basis for a risk assessment
        result.update(level=1 if over else 0, available_committed=None, available_projected=None, shortfall=0.0, income_missing=True,
                      risk_reasons=[], buffer=None, still_needed=None, daily_allowance=None)
    else:
        available_committed, available_projected = income - committed, income - projected
        # Buffer: what can still be spent before the goal savings become unaffordable
        buffer = available_committed - required
        still_needed = sum((money(row["still_needed"]) for row in categories), Decimal(0))
        projection_risk = available_projected < required and confidence != "low"
        buffer_risk = still_needed > 0 and buffer < still_needed
        reasons = []
        if available_committed < required:
            # Recorded spending and unavoidable bills already leave too little
            level, shortfall = 3, required - available_committed
        elif projection_risk or buffer_risk:
            # A credible projection, or a buffer smaller than what the budget still needs this month
            level = 2
            reasons = [reason for reason, applies in (("projection", projection_risk), ("low_buffer", buffer_risk)) if applies]
            shortfall = required - available_projected if projection_risk else still_needed - buffer
        else:
            level, shortfall = (1 if over else 0), Decimal(0)
        days_left = days_in_month - today.day
        result.update(level=level, available_committed=float(available_committed), available_projected=float(available_projected),
                      shortfall=float(shortfall), income_missing=False, risk_reasons=reasons,
                      buffer=float(buffer), still_needed=float(still_needed),
                      daily_allowance=float((max(buffer, Decimal(0)) / days_left).quantize(CENT, ROUND_HALF_UP)) if days_left else None)
    result["fingerprint"] = hashlib.sha256(json.dumps(
        {key: result[key] for key in ("year", "month", "income", "recorded_spending", "debt_paid", "upcoming_bills",
                                       "unpaid_debt_due", "required_contributions", "categories")}, sort_keys=True).encode()).hexdigest()
    return result
