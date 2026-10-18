from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from typing import Literal
import csv
import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import JWT_ALGORITHM, get_jwt_secret_key
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.transaction import Transaction
from app.services.statement_import import parse_statement, review_rows, fingerprint, CATEGORIES, MAX_BYTES, MAX_ROWS
from app.ai.statement import classify_statement

router = APIRouter(prefix="/transactions/import", tags=["Statement import"])


class PreviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csv_text: str = Field(min_length=1, max_length=MAX_BYTES)
    currency: Literal["AED", "CNY"]
    date_order: Literal["DMY", "MDY"] = "DMY"
    amount_style: Literal["negative_debits", "positive_debits"] = "negative_debits"
    aed_to_cny: Decimal | None = Field(default=None, ge=.0001, lt=1000, allow_inf_nan=False)
    categories: list[str] = Field(default_factory=list, max_length=50)


class Selection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_id: int
    category: str = Field(min_length=1, max_length=40)
    include_possible_duplicate: bool = False


class ConfirmInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_token: str = Field(min_length=1, max_length=150000)
    selections: list[Selection] = Field(min_length=1, max_length=MAX_ROWS)


@router.post("/preview")
def preview(body: PreviewInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    if body.currency == "CNY" and body.aed_to_cny is None:
        raise HTTPException(422, "A yuan conversion rate is required. Choose CNY in Settings first to load one.")
    try:
        rows, errors = parse_statement(body.csv_text, body.currency, body.date_order, body.amount_style, body.aed_to_cny)
    except (ValueError, csv.Error) as error:
        raise HTTPException(422, str(error)) from None
    categories = list(dict.fromkeys(CATEGORIES + [item.strip() for item in body.categories if 0 < len(item.strip()) <= 40 and item.strip().isprintable()]))
    ai_available = True
    try:
        labels = classify_statement(rows, categories)
    except Exception:
        labels, ai_available = [], False
    dates = [date.fromisoformat(row["date"]) for row in rows]
    existing = [{"date": row.date.isoformat(), "amount_aed": row.amount, "description": row.description or ""} for row in db.query(Transaction).filter(Transaction.user_id == current_user.id, Transaction.date >= min(dates), Transaction.date <= max(dates)).all()]
    reviewed = review_rows(rows, labels, existing, categories)
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": str(current_user.id), "type": "statement_preview", "iat": now, "exp": now + timedelta(minutes=20), "rows": reviewed}, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    return {"preview_token": token, "rows": reviewed, "errors": errors, "ai_available": ai_available, "categories": categories}


@router.post("/confirm")
def confirm(body: ConfirmInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    owner = current_user.id
    try:
        claims = jwt.decode(body.preview_token, get_jwt_secret_key(), algorithms=[JWT_ALGORITHM], options={"require": ["sub", "type", "exp", "iat", "rows"]})
        if claims["sub"] != str(owner) or claims["type"] != "statement_preview":
            raise ValueError("Wrong preview owner")
        rows = {row["row_id"]: row for row in claims["rows"]}
        if len({item.row_id for item in body.selections}) != len(body.selections):
            raise ValueError("Repeated row selection")
        for selection in body.selections:
            row = rows[selection.row_id]
            if row["direction"] != "debit" or not selection.category.strip() or not selection.category.strip().isprintable():
                raise ValueError("Only valid debit expenses can be imported")
            if row["possible_duplicate"] and not selection.include_possible_duplicate:
                raise ValueError("Review possible duplicates before including them")
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(422, "Preview expired or selection is invalid. Read the statement again and review the selected expenses.") from None
    # Serialize SQLite confirmations so concurrent retries cannot duplicate rows.
    db.commit()
    try:
        db.execute(text("BEGIN IMMEDIATE"))
        dates = [date.fromisoformat(rows[item.row_id]["date"]) for item in body.selections]
        existing = {fingerprint({"date": row.date.isoformat(), "amount_aed": row.amount, "description": row.description or ""}) for row in db.query(Transaction).filter(Transaction.user_id == owner, Transaction.date >= min(dates), Transaction.date <= max(dates)).all()}
        added, skipped = 0, 0
        for selection in body.selections:
            row = rows[selection.row_id]
            key = fingerprint(row)
            if key in existing:
                skipped += 1
                continue
            db.add(Transaction(user_id=owner, date=date.fromisoformat(row["date"]), amount=float(Decimal(row["amount_aed"])), category=selection.category.strip(), description=row["description"]))
            existing.add(key)
            added += 1
        db.commit()
        return {"added": added, "skipped_duplicates": skipped}
    except Exception:
        db.rollback()
        raise
