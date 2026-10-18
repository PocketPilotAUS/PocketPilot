"""Read-only chat intent gates and user-scoped financial context."""
import json
import re
from decimal import Decimal
from sqlalchemy import inspect
from app.models.debt import Debt
from app.models.savings import ManualSavings, MonthlySavings
from app.models.financial_plan import FinancialPlan
from app.routers.debts import serialize
from app.services.goal_savings import assignable, contributions, with_progress

WRITE = re.compile(
    r"^(?:(?:please|can you|could you|would you)\s+)?(?:record|log|add|save|set|update|change)\b"
    r"|\bI\s+(?:just\s+)?(?:paid|spent|earned|received)\b"
    r"|^(?:my\s+)?(?:monthly\s+)?(?:income|salary)\s+is\b", re.I)
QUESTION = re.compile(
    r"^(?:what|how|which|when|where|why|do I|did I|have I|am I|is my|are my|"
    r"show|tell|list|summari[sz]e|give me|can you (?:show|tell|list|explain))\b", re.I)


def intent(messages):
    text = re.sub(r"\n\[Currency for untagged amounts[^\n]*\]", "", messages[-1].content).strip()
    if re.search(r"\b(?:do not|don't|never)\s+(?:record|log|add|save|set|update|change)\b", text, re.I):
        return "read"
    if re.search(r"\b(?:create|make|build|adjust|update|revise|edit|change)\b.{0,35}\bplan\b|\b(?:want to save|help me save|save for)\b", text, re.I):
        return "plan"
    if re.match(r"^(?:please\s+)?save\b", text, re.I) and not re.search(r"\b(?:income|expense|transaction|contribution|into|to)\b", text, re.I):
        return "plan"
    if len(messages) >= 3 and not WRITE.search(text):
        from app.services.goal_dates import PATTERNS
        lookup = QUESTION.search(text) and re.search(
            r"\b(?:income|salary|spent|recorded|transactions|debts)\b", text, re.I) and not re.search(
            r"\b(?:plan|feasible|afford(?:able)?|pay off|repay)\b", text, re.I)
        continuation = (any(pattern.search(text) for pattern, _ in PATTERNS) or re.search(
            r"\b(?:feasible|afford(?:able|ability)?|extra|per month|each month|continue|that plan|this plan)\b", text, re.I))
        if continuation and not lookup and intent(messages[:-2]) == "plan":
            return "plan"
    if QUESTION.search(text):
        return "read"
    if WRITE.search(text) and not re.search(r"\b(?:if|hypothetically|would have)\b", text, re.I):
        return "record"
    if "?" in text or re.search(r"\u0645\u0627|\u0643\u0645|\u0647\u0644|\u591a\u5c11|\u4ec0\u4e48|\u54ea\u4e9b", text):
        return "read"
    # A short answer may finish a genuine recording request, never an old query.
    if len(messages) >= 3 and intent(messages[:-2]) == "record" and re.fullmatch(
        r"(?:[\d., /:-]+|(?:AED|CNY|yuan|today|yesterday|in|on|for|this|month|"
        r"january|february|march|april|may|june|july|august|september|october|november|december)\s*)+",
        text, re.I):
        return "record"
    return "ambiguous"


def _user_text(value):
    return re.sub(r"\n\[Currency for untagged amounts[^\n]*\]", "", value).strip()


def _requested_amount(text):
    """Only currency-tagged or recording-bound amounts are money, never dates."""
    from app.services.chat_records import MONTHS
    text = _user_text(text)
    # Mask dates before inspecting numeric tokens (including natural dates).
    text = re.sub(r"\b\d{4}-\d{1,2}(?:-\d{1,2})?\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", " ", text)
    names = "|".join(sorted(MONTHS, key=len, reverse=True))
    text = re.sub(rf"\b(?:{names})\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}}\b|"
                  rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{names})[,]?\s+\d{{4}}\b|"
                  rf"\b(?:{names})\s+\d{{4}}\b", " ", text, flags=re.I)
    number = r"(?<![\w.\-])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?(?![\w.,])"
    unit = r"(?:AED|CNY|yuan|dirhams?)"
    tagged = list(re.finditer(rf"\b{unit}\s+(?P<prefix>{number})|(?P<suffix>{number})\s+{unit}\b", text, re.I))
    if tagged:
        # Multiple monetary values require clarification; don't choose one.
        if len(tagged) != 1:
            return None
        match = tagged[0]
        amount = Decimal((match.group("prefix") or match.group("suffix")).replace(",", ""))
        # Also reject a second untagged amount attached to a payment instruction.
        rest = text[:match.start()] + " MONEY " + text[match.end():]
        if re.search(rf"\b(?:and|or|plus|another|instead of|was)\s+{number}", rest, re.I):
            return None
        return amount
    bound = list(re.finditer(
        rf"(?:^\s*|\b(?:paid|spent|earned|received|record|log|add)\s+|"
        rf"\bexpense\s+(?:of\s+)?|\b(?:income|salary)\s+(?:is|as|to)\s+)(?P<value>{number})",
        text, re.I))
    if len(bound) != 1:
        return None
    if re.search(rf"\b(?:and|or|plus|another|instead of|was)\s+{number}", text, re.I):
        return None
    return Decimal(bound[0].group("value").replace(",", ""))


def _requested_category(text):
    """Keep custom labels explicit; reuse planning aliases without its Other fallback."""
    from app.services.planning import ALIASES
    from app.schemas.planning import CATEGORIES
    aliases = {name.casefold(): name for name in CATEGORIES}
    aliases.update(ALIASES)
    def canonical(value):
        value = " ".join(value.strip().split()).casefold()
        return aliases.get(value, value)
    text = _user_text(text)
    quoted = re.search(r"""\b(?:for|on|category(?:\s+is)?[:=]?)\s+["']([^"']+)["']""", text, re.I)
    if quoted:
        # A quoted custom label is valid only when no alternative follows it.
        tail = text[quoted.end():]
        if re.match(r"\s*(?:and|or|plus)\b", tail, re.I):
            return None
        return canonical(quoted.group(1))
    mentioned = {canonical(name) for name in aliases
                 if re.search(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text, re.I)}
    if len(mentioned) > 1:
        return None
    label = re.search(r"\b(?:for|on|category(?:\s+is)?[:=]?)\s+(.+)", text, re.I)
    if label:
        value = re.split(
            r"\s+(?:today|yesterday|tomorrow|on|dated|at|with|by|for)\b|[.!?](?:\s|$)",
            label.group(1), maxsplit=1, flags=re.I)[0].strip()
        if re.search(r"\b(?:and|or|plus)\b", value, re.I) and value.casefold() not in aliases:
            return None
        if value and not re.search(r"\b\d{4}-|\d{1,2}/", value):
            category = canonical(value)
            if mentioned and category not in mentioned:
                return None
            return category
    return next(iter(mentioned)) if len(mentioned) == 1 else None


def supports_action(messages, action):
    """Require one user-requested monetary value and, for expenses, one category."""
    text = _user_text(messages[-1].content)
    previous = next((_user_text(m.content) for m in reversed(messages[:-1]) if m.role == "user"), "")
    followup = not WRITE.search(text) and len(messages) >= 3 and intent(messages) == "record"
    evidence = previous + " " + text if followup else text
    amount = _requested_amount(text)
    if amount is None and followup:
        # A date-only clarification may complete the prior amount, never replace it.
        from app.services.chat_records import explicit_dates
        if re.fullmatch(r"(?:today|yesterday|tomorrow)", text, re.I) or explicit_dates(text):
            amount = _requested_amount(previous)
    if amount is None or amount != action.amount:
        return False
    if action.kind == "income":
        return bool(re.search(r"\b(?:income|salary|earned|received)\b", evidence, re.I))
    if re.search(r"\b(?:income|salary)\b", evidence, re.I) and not re.search(r"\b(?:paid|spent|expense)\b", evidence, re.I):
        return False
    category = _requested_category(evidence)
    from app.services.planning import ALIASES
    from app.schemas.planning import CATEGORIES
    proposed = " ".join((action.category or "").strip().split()).casefold()
    canonical = {name.casefold(): name for name in CATEGORIES}
    canonical.update(ALIASES)
    return category is not None and category == canonical.get(proposed, proposed)


def financial_context(db, user_id):
    tables = inspect(db.get_bind())
    debt_rows = db.query(Debt).filter_by(user_id=user_id).all() if tables.has_table("debts") else None
    debts = None if debt_rows is None else [
        {"id": row.id, "name": row.name, "balance": data["balance"],
         "annual_rate": data["annual_rate"], "remaining_months": data["remaining_months"],
         "amount": data["total_left_to_pay"], "monthlyContribution": data["estimated_monthly_payment"],
         "next_due": data["next_due"]}
        for row in debt_rows for data in [serialize(row, db)]]
    manual = (db.query(ManualSavings).filter_by(user_id=user_id).all() if assignable(db) else None)
    confirmed = (db.query(MonthlySavings).filter_by(user_id=user_id).all()
                 if tables.has_table("monthly_savings") else None)
    totals = contributions(db, user_id)
    plans = (db.query(FinancialPlan).filter_by(user_id=user_id).all()
             if tables.has_table("financial_plans") else [])
    goals = []
    for row in plans:
        data = json.loads(row.payload)
        if data.get("kind") != "savings":
            continue
        progress = with_progress(data, totals.get(row.id))
        goals.append({"goal": data.get("title"), "targetAmount": data.get("targetAmount"),
                      "savedAmount": progress["savedAmount"],
                      "current_amount": progress["enteredSavedAmount"],
                      "amount": progress["contributedAmount"],
                      "monthlyContribution": data.get("monthlyContribution"),
                      "deadline": data.get("deadline")})
    return {
        "debts": debts,
        "savings": {
            "manual_contributions": None if manual is None else {"amount": sum(r.amount_cents for r in manual) / 100},
            "confirmed_months": None if confirmed is None else {"amount": sum(r.saved_cents for r in confirmed) / 100},
            "total_recorded": None if manual is None or confirmed is None else {
                "amount": (sum(r.amount_cents for r in manual) + sum(r.saved_cents for r in confirmed)) / 100},
            "goals": goals,
        },
        "meaning": (
            "Debt amount is outstanding total left to pay; monthlyContribution is an estimated payment obligation, "
            "not a paid expense. Budget targets are planned spending, not balances. "
            "Savings total_recorded is manual contributions plus confirmed monthly savings, not a live bank balance. "
            "Goal current_amount is user-entered starting progress; amount is assigned recorded contributions; "
            "savedAmount combines them. Goal monthlyContribution is a plan, not an actual contribution. "
            "Do not add goal progress to total_recorded; those amounts can overlap. "
            "Empty lists mean no stored records; null means unavailable, never invent missing records."
        ),
    }


def current_budget_answer(text, budget, language, currency, rate):
    """Direct current-period income/budget lookups use saved amounts, not model arithmetic."""
    if language != "en" or re.search(
        r"\b(?:last|next|previous|ago|year|january|february|march|april|may|june|july|august|"
        r"september|october|november|december|spent|spending|debt|savings)\b|\d{4}", text, re.I):
        return None
    income = bool(re.search(r"\b(?:income|salary|earnings)\b", text, re.I))
    planned = bool(re.search(r"\bbudget(?:ed|s)?\b|planned expenses|expense targets", text, re.I))
    if not income and not planned:
        return None
    # Explanations/advice still use the conversational answer.
    if not QUESTION.search(text.strip()) or re.search(r"\b(?:why|should|could|would|if|afford|recommend|improve|reduce|increase)\b", text, re.I):
        return None
    factor = rate if currency == "CNY" else Decimal(1)
    def amount(value):
        return f"{currency} {Decimal(str(value)) * factor:,.2f}"
    parts = [f"For {budget['year']:04d}-{budget['month']:02d}:"]
    if income:
        parts.append("Your saved monthly income is " + amount(budget["income"]) + "."
                     if budget["income"] is not None else "No monthly income is saved.")
    if planned:
        saved = budget["ideal_budget"]
        if saved is None or not saved.get("customized"):
            parts.append("No complete expense budget is saved.")
        elif any(row["target"] is None for row in saved["allocations"]):
            parts.append("Your expense budget has missing targets.")
        else:
            total = sum((Decimal(str(row["target"])) for row in saved["allocations"]), Decimal(0))
            parts.append("Your planned expense budget is " + amount(total) +
                         ", including any derived Debt allocation. This is planned spending, not money already spent.")
    return " ".join(parts)
