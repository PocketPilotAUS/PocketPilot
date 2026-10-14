from datetime import date
from fastapi import HTTPException
from sqlalchemy import inspect, func
from app.models.debt_payment import DebtPayment


def ready(db):
    if not inspect(db.get_bind()).has_table("debt_payments"):
        raise HTTPException(503, "Debt payment storage is not ready. Run Backend/migrate_debt_payments.py.")


def monthly_cents(db, user_id, year, month):
    ready(db)
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return db.query(func.coalesce(func.sum(DebtPayment.amount_cents), 0)).filter(
        DebtPayment.user_id == user_id, DebtPayment.paid_on >= start,
        DebtPayment.paid_on < end).scalar()
