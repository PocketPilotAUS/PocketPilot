"""Savings fact grounding and read-only affordability using saved budget targets."""
import re
from decimal import Decimal
from datetime import date
from types import SimpleNamespace
from app.services.chat_context import _user_text
from app.services.chat_interpretation import stated_amounts
from app.services.chat_record_drafts import amount_value, currency_problem

# Monetary rates cannot also serve as total-target evidence. This is a unit
# validation, not an intent classifier; semantic routing remains the model's job.
RATE = re.compile(r"(?<![\w.,])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?\s*k?\s*(?:aed|cny)?\s*(?:(?:a|per|each|every)\s+month|monthly|/\s*mo(?:nth)?)\b", re.I)


def grounded(raw, messages, today=None):
    """Reject invented names and money; total targets need non-rate evidence."""
    raw = dict(raw)
    texts = [_user_text(m.content) for m in messages if m.role == "user"]
    text = " ".join(texts).casefold()
    if raw.get("goal") and str(raw["goal"]).strip().casefold() not in text:
        raw.pop("goal", None)
    amounts = stated_amounts(messages)
    rate_amounts = stated_amounts([SimpleNamespace(role="user", content=m.group()) for t in texts for m in RATE.finditer(t)])
    # An elliptical adjustment may inherit the unit from the active conversation,
    # but an initial total target cannot silently become a chosen monthly rate.
    monthly_context = len(messages) >= 3 and re.search(r"\b(?:monthly|month)\b", messages[-2].content + " " + messages[-3].content, re.I)
    if raw.get("monthly_contribution") is not None:
        try:
            monthly_evidence = rate_amounts | (stated_amounts(messages[-1:]) if monthly_context else set())
            if Decimal(str(raw["monthly_contribution"])) not in monthly_evidence:
                raw.pop("monthly_contribution", None)
        except (ValueError, TypeError, ArithmeticError):
            raw.pop("monthly_contribution", None)
    totals = stated_amounts([SimpleNamespace(role="user", content=RATE.sub("", t)) for t in texts])
    for key in ("target_amount", "current_amount", "monthly_contribution"):
        try:
            if raw.get(key) is not None and Decimal(str(raw[key])) not in (totals if key == "target_amount" else amounts):
                raw.pop(key, None)
        except (ValueError, TypeError, ArithmeticError):
            raw.pop(key, None)
    # Dates must be supported by actual date/timeframe language, not a model's
    # matching year or a number accidentally shared with a money amount.
    if raw.get("deadline") is not None or raw.get("deadline_in_months") is not None:
        from app.services.goal_dates import resolve_deadline
        value, _ = resolve_deadline(texts, today or date.today())
        if value is None:
            raw.pop("deadline", None); raw.pop("deadline_in_months", None)
    return raw


def pending_period(messages):
    """Recognize our immediately preceding period question, not a user command.

    The amount still comes exclusively from the preceding user message. This
    pending read-only question cannot authorize recording or plan confirmation.
    """
    if len(messages) < 3:
        return False
    question = messages[-2].content
    return question.startswith("Do you mean saving ") and question.endswith(" each month, or a one-time amount?")


def affordability(semantic, messages, budget, currency, rate, today):
    source = _user_text(messages[-1].content)
    continuing = semantic.continuation or pending_period(messages)
    if continuing and len(messages) >= 3:
        source = _user_text(messages[-3].content) + " " + source
    token = semantic.amount_text
    if token is None and continuing:
        amounts = stated_amounts(messages[-3:])
        if len(amounts) == 1:
            token = str(next(iter(amounts)))
    value = amount_value(token, source)
    if currency_problem(source, currency):
        return {"reply": "Which supported currency is the savings amount in?"}
    if value is not None and not re.search(r"\b(?:monthly|month)\b|/mo\b", source, re.I):
        return {"reply": f"Do you mean saving {currency} {value:,.2f} each month, or a one-time amount?"}
    targets = budget.get("ideal_budget")
    if budget["income"] is None or not targets or any(row["target"] is None for row in targets["allocations"]):
        return {"reply": "Please complete your saved income and planned expenses so I can check affordability."}
    income = Decimal(str(budget["income"]))
    expenses = sum((Decimal(str(row["target"])) for row in targets["allocations"]), Decimal(0))
    headroom = income - expenses
    base = value / rate if currency == "CNY" and value is not None else value
    factor = rate if currency == "CNY" else Decimal(1)
    def money(n):
        return f"{currency} {n * factor:,.2f}"
    if value is None:
        names = {name.casefold() for name in semantic.protected_categories if name.casefold() in source.casefold()}
        protected = [row["category"] for row in targets["allocations"] if row["category"].casefold() in names]
        profile = {"income": float(income), "expenses": {row["category"]: row["target"] for row in targets["allocations"]}, "protected_categories": protected}
        from app.services.budget_goals import assess
        reply = f"Your saved monthly income is {money(income)} and planned expenses are {money(expenses)}, leaving {money(headroom)} of planned monthly headroom before any additional obligations or unlisted costs. "
        if protected:
            reply += "I will keep " + ", ".join(protected) + " unchanged. "
        return {"reply": reply + "How much more would you like to save each month? Nothing has been changed.",
                "planning_profile": profile, "goal_planning": True, "budget_goal": assess(profile, budget, today)}
    outcome = (f"Saving {money(base)} monthly would leave {money(headroom-base)} in planned monthly headroom."
               if headroom >= base else f"Saving {money(base)} monthly would exceed planned headroom by {money(base-headroom)}.")
    return {"reply": f"Your saved monthly income is {money(income)} and planned expenses are {money(expenses)}, leaving {money(headroom)}. {outcome} This assumes no additional obligations or unlisted costs. Would you like to create a savings goal? Nothing has been changed."}
