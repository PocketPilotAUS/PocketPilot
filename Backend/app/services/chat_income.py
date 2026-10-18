"""Income interpretation uses shared drafts, monthly totals and proposal confirmation."""
import re
from decimal import Decimal
from types import SimpleNamespace
from app.core.currency import base_patch
from app.models.income import MonthlyIncome
from app.routers.proposals import ProposedAction, create_proposal
from app.services.chat_context import _user_text
from app.services.chat_records import normalize_action, pending_reply, recording_text
from app.services.chat_record_drafts import RecordDraft, amount_value, grounded_amount_token, resolved_date, seal_draft, currency_problem


def extract_draft(semantic, messages, today, currency, rate, previous=None):
    latest = _user_text(messages[-1].content)
    source = previous.source + " " + latest if previous else _user_text(recording_text(messages, semantic.continuation))
    if len(source) > 24000:
        from fastapi import HTTPException
        raise HTTPException(422, "Record details are too long. Please describe the income again. Nothing has been saved.")
    draft = previous.model_copy(update={"source": source}) if previous else RecordDraft(kind="income", source=source, currency=currency, rate=rate)
    evidence = latest if previous else source
    if amount_value(semantic.amount_text, evidence, semantic.income_operation == "replace") is not None:
        draft.amount_text = grounded_amount_token(semantic.amount_text, evidence)
    if semantic.income_operation is not None:
        draft.income_operation = semantic.income_operation
    received = resolved_date(evidence, today)
    if received is not None:
        draft.payment_date = received
    if draft.income_operation == "replace":
        try:
            period = normalize_action({"kind": "income"}, [SimpleNamespace(content=evidence)], today, False)
            draft.income_year, draft.income_month = period["year"], period["month"]
        except (ValueError, TypeError, OverflowError):
            pass
    return RecordDraft.model_validate(draft.model_dump())


def respond(draft, db, user_id, currency, rate, latest_text, today):
    if currency_problem(draft.source, draft.currency):
        return {"reply": "Please clarify the income currency using your selected AED or CNY currency. Nothing has been saved."}
    if re.search(r"\b(?:save|saving|savings|contribution|set aside)\b", draft.source, re.I) and not re.search(
            r"\b(?:income|salary|earned|received|paid|wages?|paycheck|paycheque)\b", draft.source, re.I):
        return {"reply": "Is this a savings contribution or income you received? Nothing has been saved."}
    value = amount_value(draft.amount_text, draft.source, draft.income_operation == "replace")
    missing = []
    if value is None:
        missing.append("amount")
    if draft.income_operation is None:
        missing.append("operation")
    if draft.income_operation == "add" and draft.payment_date is None:
        missing.append("received date")
    if draft.income_operation == "replace" and draft.income_year is None and draft.payment_date is None:
        missing.append("month")
    if missing:
        questions = {"amount": "How much income did you receive?" if draft.income_operation == "add" else "What income amount should I use?",
            "operation": "Is this income you received to add to one month, or a new monthly income total?",
            "received date": "When did you receive this income?", "month": "Which month and year should this income total apply to?"}
        # Each follow-up asks for one genuinely missing field and retains the rest.
        return {"reply": questions[missing[0]] + " Nothing has been saved.", "record_state": seal_draft(draft, user_id)}
    messages = [SimpleNamespace(content=draft.source), SimpleNamespace(content=""), SimpleNamespace(content=_user_text(latest_text))]
    interpretation = draft.interpretation().model_copy(update={"continuation": True})
    if not interpretation.supports(messages, SimpleNamespace(kind="income", amount=value)):
        return {"reply": "Please clarify the income amount and whether you want to record it. Nothing has been saved."}
    if draft.income_operation == "add" and draft.payment_date > today:
        return {"reply": "That received date is in the future. Is this an expected payment? Nothing has been saved."}
    year, month = ((draft.payment_date.year, draft.payment_date.month) if draft.payment_date else (draft.income_year, draft.income_month))
    raw = {"kind": "income", "income_operation": draft.income_operation, "amount": value,
           "date": draft.payment_date, "year": year, "month": month}
    raw = base_patch(raw, draft.rate) if draft.currency == "CNY" else raw
    row = db.query(MonthlyIncome).filter_by(user_id=user_id, year=year, month=month).first()
    before = Decimal(row.amount_cents) / 100 if row else None
    after = (before or Decimal(0)) + Decimal(str(raw["amount"])) if draft.income_operation == "add" else Decimal(str(raw["amount"]))
    if after > 1_000_000_000:
        return {"reply": "That would exceed the supported monthly income total. Nothing has been saved."}
    action = ProposedAction.model_validate({**raw, "income_before": before, "income_after": after})
    return {"reply": pending_reply(action, currency, rate), "proposal": create_proposal(db, user_id, action, draft.draft_id)}


def scenario(semantic, messages, budget, currency, rate):
    """Read-only, conditional arithmetic; no inferred recurrence or financial writes."""
    source = _user_text(messages[-1].content)
    value = amount_value(semantic.amount_text, source, semantic.income_operation == "replace")
    if value is None:
        return None
    if currency_problem(source, currency):
        return {"reply": "Which supported currency is the hypothetical income amount in? Nothing has been changed."}
    targets = budget.get("ideal_budget")
    if budget["income"] is None or not targets or any(row["target"] is None for row in targets["allocations"]):
        return {"reply": "I need a saved income total and complete planned expenses to calculate this. A one-time receipt affects one month; a recurring increase would affect ongoing months. Nothing has been changed."}
    factor = rate if currency == "CNY" else Decimal(1)
    income = Decimal(str(budget["income"])) * factor
    expenses = sum((Decimal(str(row["target"])) for row in targets["allocations"]), Decimal(0)) * factor
    hypothetical = income + value if semantic.income_operation == "add" else value
    def money(amount):
        return f"{currency} {amount:,.2f}"
    change = (f"If {money(value)} is additional one-time income, that month's total would be " if semantic.income_operation == "add"
              else "If you replaced that month's income total, it would be ")
    return {"reply": f"Your saved monthly income is {money(income)}, planned expenses are {money(expenses)}, and conditional headroom is {money(income-expenses)}. "
        + change + f"{money(hypothetical)}, with {money(hypothetical-expenses)} headroom if planned spending stays the same. "
        "A one-time receipt affects that month only. An ongoing monthly increase would require a separate explicit choice; I haven't assumed recurrence. "
        "Is this one-time income or a recurring increase? Nothing has been changed."}
