from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from app.database import get_db, MAX_DATABASE_ID
from app.dependencies import CurrentUser
from app.models.savings import MonthlySavings, ManualSavings
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction
from app.routers.budget import summary

router = APIRouter(prefix="/savings", tags=["Savings"])


def today():
    return datetime.now(timezone(timedelta(hours=4))).date()


def ready(db):
    if not inspect(db.get_bind()).has_table("monthly_savings"):
        raise HTTPException(503, "Savings storage is not ready. Run Backend/migrate_savings.py.")


def cents(value):
    return int(Decimal(str(value)).quantize(Decimal(".01")) * 100)


def record(row):
    return {"year": row.year, "month": row.month, "income": row.income_cents / 100,
            "spent": row.spent_cents / 100, "extra_debt_payments": row.extra_debt_cents / 100,
            "saved": row.saved_cents / 100,
            "leftover": (row.income_cents - row.spent_cents - row.extra_debt_cents) / 100}


class Confirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(ge=1, le=9998, strict=True)
    month: int = Field(ge=1, le=12, strict=True)
    extra_debt_payments: Decimal = Field(ge=0, le=1_000_000_000, max_digits=12, decimal_places=2, allow_inf_nan=False)
    expected_income: Decimal = Field(ge=0, allow_inf_nan=False)
    expected_spent: Decimal = Field(ge=0, allow_inf_nan=False)


@router.get("")
def overview(current_user: CurrentUser, year: int = Query(ge=1, le=9998), month: int = Query(ge=1, le=12), db: Session = Depends(get_db)):
    ready(db)
    manual_ready(db)
    data = summary(db, current_user.id, year, month)
    history = db.query(MonthlySavings).filter_by(user_id=current_user.id).order_by(MonthlySavings.year.desc(), MonthlySavings.month.desc()).all()
    entries = db.query(ManualSavings).filter_by(user_id=current_user.id).order_by(ManualSavings.id.desc()).all()
    return {"year": year, "month": month, "income": data["income"], "spent": data["spent"],
            "can_confirm": (year, month) < (today().year, today().month),
            "total_saved": (sum(row.saved_cents for row in history) + sum(row.amount_cents for row in entries)) / 100,
            "manual_total": sum(row.amount_cents for row in entries) / 100,
            "manual_entries": [manual_record(row) for row in entries],
            "history": [record(row) for row in history]}


@router.put("/confirm")
def confirm(body: Confirmation, current_user: CurrentUser, db: Session = Depends(get_db)):
    ready(db)
    if (body.year, body.month) >= (today().year, today().month):
        raise HTTPException(422, "Confirm savings only after the month has ended.")
    # Release the auth read transaction; serialize snapshot confirmation and upsert.
    summary(db, current_user.id, body.year, body.month)
    db.commit()
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import text
        db.execute(text("BEGIN IMMEDIATE"))
    # Read under the write lock; budget.summary syncs recurring rows and commits,
    # so it must not be called here after BEGIN IMMEDIATE.
    start = date(body.year, body.month, 1)
    end = date(body.year + (body.month == 12), body.month % 12 + 1, 1)
    income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=body.year, month=body.month).first()
    amounts = db.query(Transaction.amount).filter(Transaction.user_id == current_user.id, Transaction.date >= start, Transaction.date < end).all()
    data = {"income": income.amount_cents / 100 if income else None,
            "spent": float(sum((Decimal(str(amount)) for (amount,) in amounts), Decimal(0)).quantize(Decimal(".01")))}
    if data["income"] is None:
        raise HTTPException(422, "Set income for this month before confirming savings.")
    if cents(data["income"]) != cents(body.expected_income) or cents(data["spent"]) != cents(body.expected_spent):
        raise HTTPException(409, "Monthly records changed. Refresh and review the savings estimate again.")
    row = db.query(MonthlySavings).filter_by(user_id=current_user.id, year=body.year, month=body.month).first()
    if row is None:
        row = MonthlySavings(user_id=current_user.id, year=body.year, month=body.month)
        db.add(row)
    row.income_cents, row.spent_cents = cents(data["income"]), cents(data["spent"])
    row.extra_debt_cents = cents(body.extra_debt_payments)
    row.saved_cents = max(0, row.income_cents - row.spent_cents - row.extra_debt_cents)
    db.commit()
    return record(row)


class ManualInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=80)
    amount: Decimal = Field(gt=0, le=1_000_000_000, max_digits=12, decimal_places=2, allow_inf_nan=False)

    @field_validator("label")
    @classmethod
    def readable(cls, value):
        if not value.isprintable():
            raise ValueError("Enter a readable savings label.")
        return value


class ManualCreate(ManualInput):
    request_key: UUID


def manual_ready(db):
    if not inspect(db.get_bind()).has_table("manual_savings"):
        raise HTTPException(503, "Manual savings storage is not ready. Run Backend/migrate_manual_savings.py.")


def manual_record(row):
    return {"id": row.id, "label": row.label, "amount": row.amount_cents / 100}


def owned_entry(db, user_id, entry_id):
    manual_ready(db)
    row = db.query(ManualSavings).filter_by(user_id=user_id, id=entry_id).first() if 1 <= entry_id <= MAX_DATABASE_ID else None
    if row is None:
        raise HTTPException(404, "Savings entry not found")
    return row


@router.post("/manual", status_code=201)
def add_manual(body: ManualCreate, current_user: CurrentUser, db: Session = Depends(get_db)):
    manual_ready(db)
    user_id = current_user.id
    key = str(body.request_key)
    previous = db.query(ManualSavings).filter_by(user_id=user_id, request_key=key).first()
    if previous:
        return manual_record(previous)
    row = ManualSavings(user_id=user_id, label=body.label, amount_cents=cents(body.amount), request_key=key)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.query(ManualSavings).filter_by(user_id=user_id, request_key=key).first()
        if previous is None:
            raise
        return manual_record(previous)
    return manual_record(row)


@router.put("/manual/{entry_id}")
def edit_manual(entry_id: int, body: ManualInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    row = owned_entry(db, current_user.id, entry_id)
    row.label, row.amount_cents = body.label, cents(body.amount)
    db.commit()
    return manual_record(row)


@router.delete("/manual/{entry_id}", status_code=204)
def delete_manual(entry_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.delete(owned_entry(db, current_user.id, entry_id))
    db.commit()
    return Response(status_code=204)
