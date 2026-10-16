"""Deterministic goal deadlines from relative timeframes ("in six months").

The model reports how many months the user mentioned; the server turns that
into a date, so dates are never calculated by the model.
"""
import calendar
from datetime import date

MAX_GOAL_MONTHS = 600


def deadline_from_months(today, months):
    """Last day of the Nth contribution month, counting this month as the first.

    Matches budget_goals.assess(), where contributions start this calendar
    month and include the deadline month, so the goal gets exactly `months`
    monthly contributions. Returns None for invalid input.
    """
    if isinstance(months, bool) or not isinstance(months, int) or not 1 <= months <= MAX_GOAL_MONTHS:
        return None

    index = today.year * 12 + today.month - 1 + months - 1
    year, month = divmod(index, 12)

    if year > 9998:
        return None

    return date(year, month + 1, calendar.monthrange(year, month + 1)[1])


# Deadlines are read from what the user wrote, so a model can only choose
# between dates and timeframes that are actually in the conversation.
import re

MONTHS = {name: number for number, names in enumerate([
    ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",),
    ("june", "jun"), ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"),
    ("october", "oct"), ("november", "nov"), ("december", "dec")], start=1) for name in names}
COUNTS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
          "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "eighteen": 18,
          "twenty": 20, "twenty-four": 24, "thirty": 30, "thirty-six": 36}
MONTH = "(" + "|".join(sorted(MONTHS, key=len, reverse=True)) + r")\.?"
DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
COUNT = r"(\d{1,3}|" + "|".join(sorted(COUNTS, key=len, reverse=True)) + ")"
PATTERNS = [
    # (regex, kind) — kinds decide how groups become a date
    (re.compile(MONTH + r"\s+" + DAY + r",?\s+(\d{4})\b", re.I), "month_day_year"),
    (re.compile(r"\b" + DAY + r"\s+(?:of\s+)?" + MONTH + r",?\s+(\d{4})\b", re.I), "day_month_year"),
    (re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"), "iso"),
    (re.compile(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{4})\b"), "day_first"),
    (re.compile(r"\b" + MONTH + r",?\s+(\d{4})\b", re.I), "month_year"),
    (re.compile(r"\b(\d{1,2})[/-](\d{4})\b"), "numeric_month_year"),
    (re.compile(r"\b(\d{4})-(\d{1,2})\b(?!-\d)"), "year_month"),
    (re.compile(r"\b(?:by|until|before|till)\s+(?:next\s+)?" + MONTH + r"(?!\s*,?\s*\d)", re.I), "month_only"),
    # "per/every/each 2 months" is a rate, not a deadline
    (re.compile(r"(?<!per )(?<!every )(?<!each )\b" + COUNT + r"\s*-?\s*(months?|years?|yrs?)\b", re.I), "relative"),
    # "a month"/"a year" only as a timeframe ("in a year"), never a rate ("500 a month")
    (re.compile(r"\b(?:in|within|over|after|for)\s+(a|an|one)\s+(month|year)\b", re.I), "relative"),
    (re.compile(r"\bhalf\s+a\s+year\b", re.I), "half_year"),
]


def _month_end(year, month):
    if not 1 <= month <= 12 or not 1 <= year <= 9998:
        return None
    return date(year, month, calendar.monthrange(year, month)[1])


def _exact(year, month, day):
    try:
        return date(year, month, day)
    except ValueError:
        return None


def deadline_mentions(text, today):
    """Deadlines stated in text, as (position, date, months or None), in order."""
    found, taken = [], []
    for pattern, kind in PATTERNS:
        for match in pattern.finditer(text):
            # Longer forms are matched first; skip text they already used
            if any(match.start() < end and start < match.end() for start, end in taken):
                continue
            groups = match.groups()
            months = None
            if kind == "month_day_year":
                value = _exact(int(groups[2]), MONTHS[groups[0].lower()], int(groups[1]))
            elif kind == "day_month_year":
                value = _exact(int(groups[2]), MONTHS[groups[1].lower()], int(groups[0]))
            elif kind == "iso":
                value = _exact(int(groups[0]), int(groups[1]), int(groups[2]))
            elif kind == "day_first":
                value = _exact(int(groups[2]), int(groups[1]), int(groups[0]))
            elif kind == "month_year":
                value = _month_end(int(groups[1]), MONTHS[groups[0].lower()])
            elif kind == "numeric_month_year":
                value = _month_end(int(groups[1]), int(groups[0]))
            elif kind == "year_month":
                value = _month_end(int(groups[0]), int(groups[1]))
            elif kind == "month_only":
                month = MONTHS[groups[0].lower()]
                value = _month_end(today.year + (month < today.month), month)
            elif kind == "relative":
                count = int(groups[0]) if groups[0].isdigit() else COUNTS.get(groups[0].lower(), 1)
                months = count * (12 if groups[1].lower().startswith(("year", "yr")) else 1) if count else None
                value = deadline_from_months(today, months)
            else:
                months = 6
                value = deadline_from_months(today, months)
            if value is not None:
                found.append((match.start(), value, months))
                taken.append((match.start(), match.end()))
    return sorted(found, key=lambda item: item[0])


def resolve_deadline(user_messages, today, model_deadline=None, model_months=None):
    """(deadline, problem) for a goal, from the user's own words.

    The user's latest stated future date or timeframe wins; month-only dates
    mean the end of that month. problem is "past" when only dates that have
    already passed were stated. The model's values are used only when nothing
    is recognised here (for example other languages), and only if the user
    wrote the year or number of months.
    """
    mentions = []
    for index, text in enumerate(user_messages):
        mentions += [((index, position), value) for position, value, _ in deadline_mentions(text, today)]
    if mentions:
        future = [item for item in mentions if item[1] >= today]
        if not future:
            return None, "past"
        return max(future, key=lambda item: item[0])[1], None
    text = " ".join(user_messages)
    if isinstance(model_deadline, str):
        try:
            value = date.fromisoformat(model_deadline)
        except ValueError:
            value = None
        if value is not None and re.search(r"\b%d\b" % value.year, text):
            return (value, None) if value >= today else (None, "past")
    if isinstance(model_months, int) and not isinstance(model_months, bool) and re.search(r"\b%d\b" % model_months, text):
        return deadline_from_months(today, model_months), None
    return None, None
