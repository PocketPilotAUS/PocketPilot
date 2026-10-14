import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
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


def serialize(debt):
    payment, interest = estimate(debt.balance, debt.annual_rate, debt.remaining_months)
    return {"id": debt.id, "name": debt.name, "balance": float(debt.balance),
            "annual_rate": float(debt.annual_rate), "remaining_months": debt.remaining_months,
            "original_principal": float(debt.original_principal) if debt.original_principal is not None else None,
            "estimated_monthly_payment": payment, "estimated_remaining_interest": interest}


def ready(db):
    if not inspect(db.get_bind()).has_table("debts"):
        raise HTTPException(503, "Debt storage is not ready. Run Backend/migrate_debts.py and restart the backend.")


def owned(db, user_id, debt_id):
    ready(db)
    debt = db.query(Debt).filter(Debt.user_id == user_id, Debt.id == debt_id).first() if 1 <= debt_id <= MAX_DATABASE_ID else None
    if debt is None:
        raise HTTPException(404, "Debt not found")
    return debt


@router.get("")
def list_debts(current_user: CurrentUser, db: Session = Depends(get_db)):
    ready(db)
    return [serialize(row) for row in db.query(Debt).filter(Debt.user_id == current_user.id).order_by(Debt.id).all()]


@router.post("", status_code=201)
def add_debt(body: DebtInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    ready(db)
    debt = Debt(user_id=current_user.id, **body.model_dump())
    db.add(debt)
    db.commit()
    db.refresh(debt)
    return serialize(debt)


@router.put("/{debt_id}")
def update_debt(debt_id: int, body: DebtInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    debt = owned(db, current_user.id, debt_id)
    for key, value in body.model_dump().items():
        setattr(debt, key, value)
    db.commit()
    db.refresh(debt)
    return serialize(debt)


@router.delete("/{debt_id}", status_code=204)
def delete_debt(debt_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.delete(owned(db, current_user.id, debt_id))
    db.commit()
    return Response(status_code=204)
