"""Validated spending limits for the rest of the current month.

A proposal sets a spending LIMIT per category: the most the user plans to
spend in it by month-end. Every figure is calculated here; AI only chooses
categories, limits and wording.

  - a limit is never below what is already spent plus upcoming bills, and
    never above the projected month-end spending (it must reduce something)
  - stated realism assumption: at most MAX_REDUCTION_SHARE of the spending
    still expected in a category can be avoided; fixed bills can't be cut
  - "avoided" is projected future spending the user can avoid by keeping to
    the limit; it is never money already saved
  - accepting stores the limits and lowers a category budget only where the
    limit is below it; budgets are never raised, so overspending stays visible

Shortfalls are kept separate:
  current_shortfall    goal savings minus money left after recorded spending and bills
  forecast_shortfall   goal savings minus money left after projected spending
  potential_reduction  total avoided future spending from the limits
  remaining_shortfall  forecast shortfall after the limits (never below current)
"""
import math
import re
from decimal import Decimal, ROUND_HALF_UP
from app.services.spending_monitor import CENT, money

MAX_REDUCTION_SHARE = Decimal("0.5")
ASSUMPTION = "Assumes you can avoid up to half of the spending still expected in a category; bills and money already spent can't be reduced."


def currency_text(text):
    """AI wording uses the app's currency, never dollars."""
    return re.sub(r"\$\s?(?=\d)", "AED ", text).replace("USD", "AED")


def realistic_floor(row):
    """Lowest realistic month-end spending for a category."""
    minimum, expected = money(row["minimum"]), money(row.get("forecast", row["minimum"]))
    if row.get("method") in ("fixed", "adjusted") or expected <= minimum:
        return expected
    return (minimum + (expected - minimum) * (1 - MAX_REDUCTION_SHARE)).quantize(CENT, ROUND_HALF_UP)


def spending_gap(status):
    """Low-buffer risk: what the budget still needs this month minus what can be spent."""
    if "low_buffer" not in status.get("risk_reasons", []):
        return None
    return max(Decimal(0), money(status["still_needed"]) - money(status["buffer"]))


def target_amount(status):
    """What limits should cover (levels 2 and 3); nothing at level 1: the forecast
    shortfall, or the spending gap when the buffer is too small, whichever is larger."""
    if status["level"] < 2 or status["available_projected"] is None:
        return Decimal(0)
    forecast = max(Decimal(0), money(status["required_contributions"]) - money(status["available_projected"]))
    return max(forecast, spending_gap(status) or Decimal(0))


def check_changes(status, changes, strict):
    """(limits, notes) checked against this month's figures.

    strict rejects anything outside the realistic range (acceptance);
    otherwise amounts are moved into range and explained (AI drafts).
    """
    rows = {row["category"].casefold(): row for row in status["categories"]}
    checked, notes, seen = [], [], set()
    for change in changes:
        row = rows.get(str(change.get("category", "")).strip().casefold())
        if row is None or row["category"] in seen:
            if strict:
                raise ValueError("Every limit must be for one of this month's budget categories, listed once.")
            continue
        seen.add(row["category"])
        try:
            limit = money(change.get("limit"))
        except ArithmeticError:
            if strict:
                raise ValueError("Enter valid amounts.")
            continue
        expected, floor = money(row.get("forecast", row["minimum"])), realistic_floor(row)
        if expected - floor < CENT:
            if strict:
                raise ValueError(f"{row['category']} can't realistically be reduced this month.")
            continue
        if limit < floor:
            if strict:
                raise ValueError(f"{row['category']} can't be limited below AED {floor:,.2f}: that is already spent, due, or not realistic.")
            notes.append(f"{row['category']}: limit raised to AED {floor:,.2f}, the lowest realistic amount.")
            limit = floor
        if limit > expected - CENT:
            if strict:
                raise ValueError(f"{row['category']}: the limit must be below the projected spending.")
            continue
        spent, upcoming, budget = money(row["spent"]), money(row["upcoming"]), money(row["budget"])
        checked.append({"category": row["category"], "budget": float(budget), "spent": float(spent), "upcoming": float(upcoming),
                        "forecast": float(expected), "limit": float(limit),
                        "remaining_allowance": float(max(Decimal(0), limit - spent - upcoming)),
                        "avoided": float(expected - limit), "budget_after": float(min(budget, limit)),
                        # Amounts come only from these checked figures: AI wording with numbers is dropped
                        "reason": "" if re.search(r"\d", str(change.get("reason") or "")) else str(change.get("reason") or "").strip()[:300]})
    return checked, notes


def affordability(status, avoided=Decimal(0)):
    """Income - expected spending = left; left - savings goals = left after savings."""
    if status["available_projected"] is None:
        return {}
    left = money(status["available_projected"]) + avoided
    required = money(status["required_contributions"])
    return {"income": status["income"], "expected_spending": float(money(status["projected_spending"]) - avoided),
            "left_after_spending": float(left), "required_contributions": float(required),
            "left_after_savings": float(left - required)}


def advice(status, tips):
    """Level 1: the goal is affordable, so only advice; no budget or savings changes."""
    return {"mode": "advice", "fingerprint": status["fingerprint"], "level": status["level"], "days_left": status["days_left"],
            "changes": [], "notes": [], "tips": [currency_text(tip) for tip in tips], "covers": True, "options": [],
            "required_contributions": status["required_contributions"], "over_budget": status["over_budget"],
            "forecast_confidence": status["forecast_confidence"], "affordability": affordability(status)}


def plan_options(plan, can_save, today):
    """Options for one savings goal when this month's contribution can't be met.

    can_save is the most this goal can realistically receive this month.
    Simple arithmetic on the saved plan; nothing is changed here. The user
    applies an option in the plan editor, which recalculates the plan.
    """
    from app.services.goal_dates import deadline_from_months
    contribution = money(plan.get("monthlyContribution"))
    remaining = money(plan.get("targetAmount")) - money(plan.get("savedAmount"))
    deadline = plan.get("deadline")
    if contribution <= 0 or remaining <= 0 or not deadline or can_save >= contribution:
        return []
    months_left = (int(deadline[:4]) - today.year) * 12 + int(deadline[5:7]) - today.month + 1
    after_this_month = remaining - can_save
    options = []
    if months_left > 1:
        # Same deadline: save what is possible now, spread the rest over the remaining months
        options.append({"kind": "catch_up", "this_month": float(can_save), "deadline": deadline, "months": months_left - 1,
                        "monthly": float((after_this_month / (months_left - 1)).quantize(CENT, ROUND_HALF_UP))})
    # Same monthly amount: the months still needed after this one move the deadline.
    # plan_monthly is what the plan editor (which counts this month too) will
    # need for that date: the remaining amount spread evenly, rounded up to the cent.
    total_months = math.ceil(after_this_month / contribution) + 1
    extended = deadline_from_months(today, total_months)
    if extended is not None and extended.isoformat() > deadline:
        plan_monthly = Decimal(math.ceil(remaining * 100 / total_months)) / 100
        options.append({"kind": "extend", "this_month": float(can_save), "monthly": float(contribution), "deadline": extended.isoformat(),
                        "months": total_months, "plan_monthly": float(plan_monthly)})
    return options


def summarize(status, changes, notes, plan=None, today=None):
    """Effect of the limits on this month's projection and goals, with labelled shortfalls."""
    avoided = sum((money(change["avoided"]) for change in changes), Decimal(0))
    required = money(status["required_contributions"])
    result = {"mode": "recovery" if status["level"] >= 3 else "adjust", "fingerprint": status["fingerprint"],
              "level": status["level"], "days_left": status["days_left"], "changes": changes, "notes": notes, "tips": [],
              "required_contributions": float(required), "forecast_confidence": status["forecast_confidence"],
              "forecast_reliable": status["forecast_confidence"] != "low", "assumption": ASSUMPTION,
              "potential_reduction": float(avoided), "affordability": affordability(status, avoided), "options": [],
              "risk_reasons": status.get("risk_reasons", []), "buffer": status.get("buffer"),
              "still_needed": status.get("still_needed"), "daily_allowance": status.get("daily_allowance")}
    if status["available_projected"] is None:
        return dict(result, covers=False)
    left = money(status["available_projected"]) + avoided
    remaining = max(Decimal(0), required - left)
    can_save = max(Decimal(0), min(left, required))
    gap = spending_gap(status)
    if gap is not None and "projection" not in status["risk_reasons"]:
        # Low buffer: the limits must make the rest of the month fit within what can be spent
        remaining = max(Decimal(0), gap - avoided)
    result.update(current_shortfall=float(max(Decimal(0), required - money(status["available_committed"]))),
                  forecast_shortfall=float(max(Decimal(0), required - money(status["available_projected"]))),
                  spending_gap=float(gap) if gap is not None else None,
                  remaining_shortfall=float(remaining), covers=remaining < CENT / 2, max_this_month=float(can_save))
    if remaining >= CENT / 2 and plan is not None and today is not None and required > 0:
        # This goal's share of what can be saved, in proportion to its contribution
        share = (can_save * money(plan.get("monthlyContribution")) / required).quantize(CENT, ROUND_HALF_UP)
        result["options"] = plan_options(plan, share, today)
    return result


def apply_changes(categories, changes):
    """Category budgets after accepting: lowered only where the limit is below the budget."""
    amounts = {change["category"].casefold(): money(change["budget_after"]) for change in changes}
    return [dict(row, amount=str(min(Decimal(row["amount"]), amounts.get(row["name"].casefold(), Decimal(row["amount"])))))
            for row in categories]
