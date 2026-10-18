"""Shared owner-bound, expiring drafts and grounded fields for chat proposals."""
import re
import time
import hashlib
from uuid import uuid4, UUID
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Literal
import jwt
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.core.config import JWT_ALGORITHM, get_jwt_secret_key
from app.schemas.planning import CATEGORIES
from app.services.planning import ALIASES
from app.services.chat_context import _user_text
from app.services.chat_interpretation import ChatInterpretation, without_dates
from app.services.chat_records import normalize_action


class RecordDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    draft_id: str | None = Field(default=None, max_length=36)
    kind: Literal["expense", "income"] = "expense"
    income_operation: Literal["add", "replace"] | None = None
    income_year: int | None = Field(default=None, ge=1, le=9998)
    income_month: int | None = Field(default=None, ge=1, le=12)
    source: str = Field(max_length=24000)
    amount_text: str | None = Field(default=None, max_length=80)
    category_text: str | None = Field(default=None, max_length=200)
    category: str | None = Field(default=None, max_length=40)
    payment_date: date | None = None
    currency: Literal["AED", "CNY"]
    rate: Decimal | None = None

    def interpretation(self):
        return ChatInterpretation(intent="record", topic="budget", continuation=False, kind=self.kind, income_operation=self.income_operation,
            amount_text=self.amount_text, category_text=self.category_text, category=self.category, clarification=None)

    def model_context(self):
        return self.model_dump(mode="json")


NUMBER = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?\s*[kK]?"


def numeric_value(token):
    value = token.lower().replace(",", "").replace(" ", "")
    return Decimal(value.rstrip("k")) * (1000 if value.endswith("k") else 1)


def grounded_amount_token(token, source):
    """Match monetary value, retaining the literal user token for later validation.

    Models may normalize '2k' or '2,000' to '2000'. Equivalent formatting is
    evidence, but a partial number, date, negative or invented value isn't.
    """
    if not token or not re.fullmatch(NUMBER, token.strip()):
        return None
    expected = numeric_value(token.strip())
    matches = re.finditer(r"(?<![\w.,-])" + NUMBER + r"(?!\w|[.,]\d)", without_dates(source))
    return next((match.group().strip() for match in matches if numeric_value(match.group().strip()) == expected), None)


def amount_value(token, source, allow_zero=False):
    grounded = grounded_amount_token(token, source)
    if grounded is None:
        return None
    value = numeric_value(grounded)
    return value if (0 <= value <= 1_000_000_000 if allow_zero else 0 < value <= 1_000_000_000) else None


def resolved_date(text, today):
    try:
        return date.fromisoformat(normalize_action({"kind": "expense"},
            [SimpleNamespace(content=text)], today, False)["date"])
    except (ValueError, TypeError, OverflowError):
        return None


def date_answer(text, today):
    """A field answer, not an arbitrary new request merely containing a date."""
    clean = _user_text(text).strip().rstrip(".!?").strip()
    residue = re.sub(r"\b(?:today|yesterday|tomorrow)\b", "", without_dates(clean), flags=re.I)
    return resolved_date(clean, today) if not residue.strip(" ,./-!?") else None


def load_draft(token, user_id, db=None):
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "exp", "draft"]})
        if payload["sub"] != str(user_id) or payload["type"] != "chat_" + payload["draft"].get("kind", "expense") + "_draft":
            raise ValueError()
        draft = RecordDraft.model_validate(payload["draft"])
        if draft.draft_id is None:
            draft.draft_id = str(UUID(bytes=hashlib.sha256(token.encode()).digest()[:16]))
        if db is not None:
            from app.models.chat_proposal import ChatProposal
            if db.get(ChatProposal, draft.draft_id) is not None:
                raise ValueError()
        return draft
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise HTTPException(422, "This pending record expired, was canceled or was already handled. Please describe it again. Nothing has been saved.") from None


def seal_draft(draft, user_id):
    if draft.draft_id is None:
        draft.draft_id = str(uuid4())
    return jwt.encode({"sub": str(user_id), "type": "chat_" + draft.kind + "_draft", "exp": int(time.time()) + 1800,
                       "draft": draft.model_dump(mode="json")}, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)


def complete_field(draft, text, today):
    """Resolve typed field-only replies without asking a model to reclassify the task."""
    clean = _user_text(text)
    if len(draft.source) + len(clean) + 1 > 24000:
        raise HTTPException(422, "Record details are too long. Please describe the record again. Nothing has been saved.")
    updates = {}
    payment_date = date_answer(clean, today)
    if draft.payment_date is None and payment_date is not None:
        updates["payment_date"] = payment_date
    elif draft.amount_text is None and amount_value(clean.strip().rstrip(".!?"), clean, draft.kind == "income" and draft.income_operation == "replace") is not None:
        updates["amount_text"] = clean.strip().rstrip(".!?")
    elif draft.kind == "expense" and draft.category is None:
        canonical = {name.casefold(): name for name in (*CATEGORIES, "Groceries")}
        category = canonical.get(clean.strip().rstrip(".!?").casefold()) or ALIASES.get(clean.strip().rstrip(".!?").casefold())
        if category:
            updates.update(category=category, category_text=draft.category_text or clean.strip().rstrip(".!?"))
    if not updates:
        return None
    return RecordDraft.model_validate({**draft.model_dump(), **updates, "source": draft.source + " " + clean})


def currency_problem(source, currency):
    foreign = r"\b(?:USD|EUR|GBP|dollars?|euros?|pounds?)\b|[$\u20ac\u00a3]"
    other = r"\b(?:CNY|RMB|yuan|renminbi)\b|[\u00a5\uffe5]" if currency == "AED" else r"\b(?:AED|dhs|dirhams?)\b"
    return bool(re.search(foreign + "|" + other, source, re.I))




def cancel_draft(db, draft, user_id):
    """Persist a tombstone in the same record-confirmation registry; no financial write."""
    from app.models.chat_proposal import ChatProposal
    from sqlalchemy.exc import IntegrityError
    db.add(ChatProposal(id=draft.draft_id, user_id=user_id, status="dismissed", payload="{}"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Another request completed/canceled this draft first. Never claim that
        # a concurrently completed pending proposal has been canceled visually.
        from app.routers.proposals import dismiss_proposal
        dismiss_proposal(db, user_id, draft.draft_id)
