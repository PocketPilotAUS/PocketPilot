"""Project AED financial context into CNY and normalize reviewable model drafts."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

MONEY_KEYS = {
    "amount", "income", "other_income", "target_amount", "current_amount", "current_income",
    "monthly_contribution", "spent", "remaining", "planned_total", "planned_remaining", "target", "baseline",
    "baselineSpending", "availableBefore", "availableAfter", "requiredMonthly", "monthlyContribution",
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
