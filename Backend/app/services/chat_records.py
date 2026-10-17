"""Validated transaction periods and pending-only chat wording; no goal deadlines."""
import calendar
import re
from datetime import date, timedelta
from decimal import Decimal

MONTHS = {name.casefold(): index for names in (calendar.month_name, calendar.month_abbr)
          for index, name in enumerate(names) if name}


def unsupported_operation(text):
    if re.search(r"\b(?:financial|budget|savings)\s+plan\b", text, re.I) and not re.search(r"\btransaction\b", text, re.I):
        return None
    if re.search(r"\b(?:edit|update|change|correct|delete|remove)\b.{0,60}\b(?:expense|transaction|payment)\b", text, re.I):
        return "To edit or delete an existing expense, open Transactions and select the record. AI Chat cannot edit it. Nothing has been saved."
    if re.search(r"\b(?:add|deposit|contribute|put)\b.{0,50}\b(?:to|into|toward|towards)\b.{0,30}\bgoal\b|\b(?:record|add|log|deposit|contribute)\b.{0,70}\b(?:saving[s]?|contribution)\b|\b(?:saving[s]?|goal)\s+contribution\b|\bsave\b.{0,40}\b(?:to|into)\b.{0,30}\b(?:savings|goal)\b", text, re.I):
        return "Record actual savings contributions in Savings and choose the goal there. AI Chat cannot record savings contributions. Nothing has been saved."
    return None


def recording_text(messages):
    text = messages[-1].content
    # Mobile appends display-currency metadata; it is not a user date.
    text = re.sub(r"\n\[Currency for untagged amounts[^\n]*\]", "", text).strip()
    from app.services.chat_context import intent, WRITE
    if len(messages) >= 3 and not WRITE.search(text) and intent(messages) == "record":
        text = messages[-3].content + " " + text
    return text


def explicit_dates(text):
    values = []
    for value in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text):
        values.append(date.fromisoformat(value))
    names = "|".join(MONTHS)
    for month, day, year in re.findall(
        rf"\b({names})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(\d{{4}})\b", text, re.I):
        values.append(date(int(year), MONTHS[month.casefold()], int(day)))
    for day, month, year in re.findall(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({names})[,]?\s+(\d{{4}})\b", text, re.I):
        values.append(date(int(year), MONTHS[month.casefold()], int(day)))
    return values


def normalize_action(raw, messages, today):
    if not isinstance(raw, dict):
        raise ValueError("Specify an income or expense.")
    result = dict(raw)
    text = recording_text(messages)
    dates = set(explicit_dates(text))
    if raw.get("kind") == "expense":
        for word, offset in (("today", 0), ("yesterday", -1), ("tomorrow", 1)):
            if re.search(rf"\b{word}\b", text, re.I):
                dates.add(today + timedelta(days=offset))
        if len(dates) != 1:
            raise ValueError("Specify one exact payment date, or today, yesterday or tomorrow.")
        # Unresolved additional time expressions must not silently pick a date.
        if re.search(r"\b(?:last|next)\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|\d{1,2}/\d{1,2}", text, re.I):
            raise ValueError("Clarify the payment date.")
        result["date"] = dates.pop().isoformat()
    elif raw.get("kind") == "income":
        periods = {(d.year, d.month) for d in dates}
        for word, offset in (("this", 0), ("current", 0), ("last", -1), ("previous", -1), ("next", 1)):
            if re.search(rf"\b{word}\s+month\b", text, re.I):
                year, month = divmod(today.year * 12 + today.month - 1 + offset, 12)
                periods.add((year, month + 1))
        for year, month in re.findall(r"\b(\d{4})-(\d{2})(?!-\d)\b", text):
            periods.add((int(year), int(month)))
        for month, year in re.findall(r"\b(" + "|".join(MONTHS) + r")\s+(\d{4})\b", text, re.I):
            periods.add((int(year), MONTHS[month.casefold()]))
        if len(periods) > 1:
            raise ValueError("Specify one income month.")
        if not periods:
            if re.search(r"\b(?:" + "|".join(MONTHS) + r"|last|next|previous|ago|year|yesterday|tomorrow)\b|\d{1,2}/\d{1,2}", text, re.I):
                raise ValueError("Specify the income month and year.")
            # Existing income workflow defaults an unspecified month to this month,
            # now on the server and explicitly disclosed in the pending message.
            periods.add((today.year, today.month))
        result["year"], result["month"] = periods.pop()
    return result


def pending_reply(action, currency="AED", rate=None):
    amount = action.amount * (rate if currency == "CNY" else Decimal(1))
    if action.kind == "expense":
        day = action.date
        label = f"{calendar.month_name[day.month]} {day.day}, {day.year}"
        return f"Ready to record {currency} {amount:,.2f} for {action.category} on {label}. Confirm to save this expense."
    label = f"{calendar.month_name[action.month]} {action.year}"
    return f"Ready to set your monthly income to {currency} {amount:,.2f} for {label}. Confirm to save; this replaces any saved income for that month."
