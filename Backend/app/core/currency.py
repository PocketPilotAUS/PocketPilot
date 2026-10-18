"""Project AED financial context into CNY and normalize reviewable model drafts."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

MONEY_KEYS = {
    "balance", "amount", "income", "other_income", "target_amount", "current_amount", "current_income",
    "average", "tolerance", "suggested_target", "increase", "extra_commitments", "available_for_increases",
    "proposed_total", "total_increase", "remaining_after_proposal", "required_contributions",
    "monthly_contribution", "spent", "remaining", "planned_total", "planned_remaining", "target", "baseline",
    "baselineSpending", "availableBefore", "availableAfter", "remainingAfterSavings", "requiredMonthly", "monthlyContribution",
    "unfundedMonthly", "targetAmount", "savedAmount", "monthlyAmount", "historicalMonthly",
    "plannedMonthly", "difference", "overBy", "total_spending", "scenarioAvailable", "scenarioUnfunded",
}
MONEY_MAPS = {"expenses", "category_spending", "recorded_spending", "past_months", "recurring_obligations"}


def money(value, factor):
    try:
        result = Decimal(str(value)) * factor
        if not result.is_finite():
            raise ValueError("Invalid money")
        return float(result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError, OverflowError) as error:
        raise ValueError("Invalid money") from error


def display_context(value, rate, money_map=False):
    if isinstance(value, dict):
        return {key: display_context(item, rate, money_map or key in MONEY_MAPS)
                if isinstance(item, (dict, list)) else
                money(item, rate) if item is not None and (money_map or key in MONEY_KEYS) and not isinstance(item, bool) else item
                for key, item in value.items()}
    if isinstance(value, list):
        return [display_context(item, rate, money_map) for item in value]
    return value


def base_patch(value, rate):
    if not isinstance(value, dict):
        return value
    result = dict(value)
    for key in ("amount", "income", "other_income", "target_amount", "current_amount", "monthly_contribution"):
        if result.get(key) is not None:
            if isinstance(result[key], bool):
                raise ValueError("Invalid money")
            result[key] = money(result[key], Decimal(1) / rate)
    if isinstance(result.get("expenses"), dict):
        result["expenses"] = {key: None if amount is None else money(amount, Decimal(1) / rate)
                              for key, amount in result["expenses"].items()}
    return result


def format_reply_currency(text, currency="AED", source_text=""):
    """Normalize presentation only: keep values and explicit foreign labels intact.

    Bare dollar glyphs emitted for app figures use the selected display currency;
    an attached explicit currency label wins. This never performs conversion.
    """
    import re
    symbol_currency = "USD" if re.search(r"\b(?:USD|dollars?)\b|\$", source_text, re.I) else currency
    number = r"-?\d[\d,]*(?:\.\d+)?"
    labels = r"AED|CNY|USD|EUR|GBP"
    pattern = (rf"(?:(?P<prefix>\b(?:{labels}))\s*)?\$\s*(?P<number>{number})"
               rf"(?:\s*(?:\((?P<paren>{labels})\)|(?P<suffix>{labels})\b))?")
    def replace(match):
        label = match["prefix"] or match["paren"] or match["suffix"] or symbol_currency
        return f"{label.upper()} {match['number']}"
    text = re.sub(pattern, replace, text, flags=re.I)
    text = re.sub(rf"\b({labels})\s+({number})\s*\(\1\)", r"\1 \2", text, flags=re.I)
    return text


def format_model_reply(raw, currency, source_text=""):
    """Normalize only the human-readable field, never structured financial data."""
    import json
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return raw
    if isinstance(value, dict) and isinstance(value.get("reply"), str):
        value["reply"] = format_reply_currency(value["reply"], currency, source_text)
        return json.dumps(value)
    return raw
