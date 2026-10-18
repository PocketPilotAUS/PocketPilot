import math
from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from app.models.debt_payment import DebtPayment
from app.services.debt_payments import ready as payments_ready
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.database import MAX_DATABASE_ID, get_db
from app.dependencies import CurrentUser
from app.models.debt import Debt

router = APIRouter(prefix="/debts", tags=["debts"])


class DebtInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80)
    balance: Decimal = Field(ge=0, le=1_000_000_000, max_digits=12, decimal_places=2, allow_inf_nan=False)
    annual_rate: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=4, allow_inf_nan=False)
    remaining_months: int = Field(ge=1, le=600, strict=True)
    original_principal: Decimal | None = Field(default=None, gt=0, le=1_000_000_000, max_digits=12, decimal_places=2, allow_inf_nan=False)

    automatic_day: int | None = Field(default=None, ge=1, le=31, strict=True)
    next_due: date | None = None

    @model_validator(mode="after")
    def schedule_pair(self):
        if (self.automatic_day is None) != (self.next_due is None):
            raise ValueError("Choose a payment day and first payment date together.")
        if self.next_due is not None:
            from calendar import monthrange
            if self.next_due.day != min(self.automatic_day, monthrange(self.next_due.year, self.next_due.month)[1]):
                raise ValueError("First payment date must match the selected payment day.")
        return self

    @field_validator("name")
    @classmethod
    def printable_name(cls, value):
        if not value.isprintable():
            raise ValueError("Enter a readable debt name.")
        return value


def estimate(balance, annual_rate, months):
    principal, rate = float(balance), float(annual_rate) / 1200
    payment = principal / months if rate == 0 else principal * rate / -math.expm1(-months * math.log1p(rate))
    return round(payment, 2), round(max(0, payment * months - principal), 2)


def serialize(debt, db=None):
    payment, interest = estimate(debt.balance, debt.annual_rate, debt.remaining_months)
    from app.services.debt_schedule import totals
    remaining, fixed = totals(db, debt) if db is not None else (round((float(debt.balance) + interest) * 100), round(payment * 100))
    return {"total_left_to_pay": remaining / 100, "automatic_day": debt.automatic_day,
            "next_due": debt.next_due.isoformat() if debt.next_due else None, "id": debt.id, "name": debt.name, "balance": float(debt.balance),
            "annual_rate": float(debt.annual_rate), "remaining_months": debt.remaining_months,
            "original_principal": float(debt.original_principal) if debt.original_principal is not None else None,
            "estimated_monthly_payment": min(fixed, remaining) / 100, "estimated_remaining_interest": interest}


def ready(db):
    if not inspect(db.get_bind()).has_table("debts"):
        raise HTTPException(503, "Debt storage is not ready. Run Backend/migrate_debts.py and restart the backend.")

    if "total_due_cents" not in {c["name"] for c in inspect(db.get_bind()).get_columns("debts")}:
        raise HTTPException(503, "Run Backend/migrate_automatic_debts.py and restart the backend.")


def owned(db, user_id, debt_id):
    ready(db)
    debt = db.query(Debt).filter(Debt.user_id == user_id, Debt.id == debt_id).first() if 1 <= debt_id <= MAX_DATABASE_ID else None
    if debt is None:
        raise HTTPException(404, "Debt not found")
    return debt


class PaymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(gt=0, le=1_000_000_000, max_digits=12, decimal_places=2, allow_inf_nan=False)
    paid_on: date
    request_key: UUID

    @field_validator("paid_on")
    @classmethod
    def completed_date(cls, value):
        if value > datetime.now(timezone(timedelta(hours=4))).date():
            raise ValueError("Enter a payment date on or before today.")
        return value


def payment_record(row):
    return {"automatic": row.automatic, "id": row.id, "debt_id": row.debt_id, "debt_name": row.debt_name,
            "amount": row.amount_cents / 100, "paid_on": row.paid_on.isoformat()}


@router.get("/payments")
def list_payments(current_user: CurrentUser, db: Session = Depends(get_db)):
    payments_ready(db)
    from app.services.debt_schedule import sync
    sync(db, current_user.id)
    return [payment_record(row) for row in db.query(DebtPayment).filter_by(user_id=current_user.id)
            .order_by(DebtPayment.paid_on.desc(), DebtPayment.id.desc()).all()]


@router.post("/{debt_id}/payments", status_code=201)
def add_payment(debt_id: int, body: PaymentInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    payments_ready(db)
    user_id, key = current_user.id, str(body.request_key)
    amount = int(body.amount * 100)
    def retry(previous):
        if previous.debt_id != debt_id or previous.amount_cents != amount or previous.paid_on != body.paid_on:
            raise HTTPException(409, "This payment request was already used. Start a new payment.")
        return payment_record(previous)
    previous = db.query(DebtPayment).filter_by(user_id=user_id, request_key=key).first()
    if previous:
        return retry(previous)
    debt = owned(db, user_id, debt_id)
    start = body.paid_on.replace(day=1)
    from app.routers.recurring import next_month
    if db.query(DebtPayment).filter(DebtPayment.user_id == user_id, DebtPayment.debt_id == debt_id,
        DebtPayment.automatic.is_(True), DebtPayment.paid_on >= start,
        DebtPayment.paid_on < next_month(start, 1)).first():
        raise HTTPException(409, "An automatic payment is already recorded for this month. Remove it before recording a replacement.")
    row = DebtPayment(user_id=user_id, debt_id=debt.id, debt_name=debt.name,
                      amount_cents=amount, applied_cents=amount, paid_on=body.paid_on, request_key=key)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.query(DebtPayment).filter_by(user_id=user_id, request_key=key).first()
        if previous is None:
            raise
        return retry(previous)
    return payment_record(row)


@router.delete("/payments/{payment_id}", status_code=204)
def remove_payment(payment_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    payments_ready(db)
    row = db.query(DebtPayment).filter_by(user_id=current_user.id, id=payment_id).first() if 1 <= payment_id <= MAX_DATABASE_ID else None
    if row is None:
        raise HTTPException(404, "Payment not found")
    db.delete(row)
    db.commit()
    return Response(status_code=204)


@router.get("")
def list_debts(current_user: CurrentUser, db: Session = Depends(get_db)):
    ready(db)
    from app.services.debt_schedule import sync
    sync(db, current_user.id)
    records = [serialize(row, db) for row in db.query(Debt).filter(Debt.user_id == current_user.id).order_by(Debt.id).all()]
    from app.services.debt_targets import applied_targets
    from app.services.debt_schedule import today_local
    today = today_local()
    regulars = {row['id']: (Decimal(str(row['estimated_monthly_payment'])), Decimal(str(row['total_left_to_pay']))) for row in records}
    _, _, details = applied_targets(db, current_user.id, today.year, today.month, regulars)
    return [{**row, **({'repayment_plan': details[row['id']]} if row['id'] in details else {})} for row in records]


@router.post("", status_code=201)
def add_debt(body: DebtInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    ready(db)
    debt = Debt(user_id=current_user.id, **body.model_dump())
    from app.services.debt_schedule import initialize, today_local
    if body.next_due and body.next_due < today_local():
        raise HTTPException(422, "First automatic payment must be today or later.")
    initialize(debt)
    db.add(debt)
    db.commit()
    db.refresh(debt)
    from app.services.debt_schedule import sync
    sync(db, current_user.id)
    return serialize(debt, db)


@router.put("/{debt_id}")
def update_debt(debt_id: int, body: DebtInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    debt = owned(db, current_user.id, debt_id)
    from app.services.debt_schedule import initialize, today_local
    if body.next_due and body.next_due != debt.next_due and body.next_due < today_local():
        raise HTTPException(422, "First automatic payment must be today or later.")
    rebase = any(getattr(debt, key) != getattr(body, key) for key in ("balance", "annual_rate", "remaining_months"))
    for key, value in body.model_dump().items():
        setattr(debt, key, value)
    if rebase:
        # The edited lender figures become the new baseline; old payments stay
        # in spending history but must not be deducted from that baseline again.
        db.query(DebtPayment).filter_by(user_id=current_user.id, debt_id=debt.id).update({"applied_cents": 0})
        initialize(debt)
    db.commit()
    db.refresh(debt)
    from app.services.debt_schedule import sync
    sync(db, current_user.id)
    return serialize(debt, db)


@router.delete("/{debt_id}", status_code=204)
def delete_debt(debt_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.delete(owned(db, current_user.id, debt_id))
    db.commit()
    return Response(status_code=204)
