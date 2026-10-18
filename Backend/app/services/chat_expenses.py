"""Grounded expense drafts using the common pending-record and confirmation flow."""
import re
from types import SimpleNamespace
from fastapi import HTTPException
from app.core.currency import base_patch
from app.routers.proposals import ProposedAction, create_proposal
from app.schemas.planning import CATEGORIES
from app.services.chat_context import _user_text, _requested_category
from app.services.chat_records import pending_reply, recording_text
from app.services.planning import ALIASES
from app.services.chat_record_drafts import (
    RecordDraft as ExpenseDraft, amount_value, grounded_amount_token, resolved_date, date_answer,
    load_draft, seal_draft, complete_field, currency_problem,
)


def extract_draft(semantic, messages, today, currency, rate, previous=None):
    latest = _user_text(messages[-1].content)
    source = previous.source + " " + latest if previous else _user_text(recording_text(messages, semantic.continuation))
    if len(source) > 24000:
        raise HTTPException(422, "Expense details are too long. Please describe the expense again. Nothing has been saved.")
    draft = previous.model_copy(update={"source": source}) if previous else ExpenseDraft(source=source, currency=currency, rate=rate)
    # A carried value may be kept; replacement values must be quoted in this turn.
    evidence = latest if previous else source
    if amount_value(semantic.amount_text, evidence) is not None:
        draft.amount_text = grounded_amount_token(semantic.amount_text, evidence)
    if semantic.category_text and semantic.category_text.casefold() in evidence.casefold():
        explicit = _requested_category(evidence)
        canonical = {name.casefold(): name for name in (*CATEGORIES, "Groceries")}
        aliases = {**canonical, **ALIASES}
        mentioned = {category for label, category in aliases.items()
                     if re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", evidence, re.I)}
        if explicit is None and len(mentioned) == 1:
            explicit = next(iter(mentioned))
        category = explicit if explicit in canonical.values() else canonical.get((semantic.category or "").casefold(),
            ALIASES.get((semantic.category or "").casefold(), semantic.category))
        draft.category_text, draft.category = semantic.category_text, category
    payment_date = resolved_date(evidence, today)
    if payment_date is not None:
        draft.payment_date = payment_date
    return ExpenseDraft.model_validate(draft.model_dump())


def respond(draft, db, user_id, currency, rate, latest_text):
    if currency_problem(draft.source, draft.currency):
        return {"reply": "Please clarify the expense currency using your selected AED or CNY currency. Nothing has been saved."}
    value = amount_value(draft.amount_text, draft.source)
    missing = []
    if value is None:
        missing.append("amount")
    if not draft.category or not draft.category.strip() or not draft.category_text:
        missing.append("category")
    if value is not None and draft.category and draft.category_text:
        # Keep the actual latest reply separate for negation, hypothetical and
        # affirmation vetoes; concatenating it into history would bypass them.
        evidence = SimpleNamespace(kind="expense", amount=value, category=draft.category)
        messages = [SimpleNamespace(content=draft.source), SimpleNamespace(content=""),
                    SimpleNamespace(content=_user_text(latest_text))]
        interpretation = draft.interpretation().model_copy(update={"continuation": True})
        if not interpretation.supports(messages, evidence):
            return {"reply": "Which amount and category should I use for this expense? Nothing has been saved."}
    if draft.payment_date is None:
        missing.append("payment date")
    if missing:
        if missing == ["payment date"]:
            question = f"When did you pay for {draft.category_text}?"
        elif missing == ["amount"]:
            question = "How much did you pay?"
        elif missing == ["category"]:
            question = "What was the expense for?"
        else:
            question = "What " + ", ".join(missing) + " should I use for this expense?"
        return {"reply": question + " Nothing has been saved.", "record_state": seal_draft(draft, user_id)}
    raw = {"kind": "expense", "amount": value, "category": draft.category, "date": draft.payment_date,
           "description": draft.category_text}
    action = ProposedAction.model_validate(base_patch(raw, draft.rate) if draft.currency == "CNY" else raw)
    return {"reply": pending_reply(action, currency, rate), "proposal": create_proposal(db, user_id, action, draft.draft_id)}
