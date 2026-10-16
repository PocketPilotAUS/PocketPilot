"""Assumed monthly payments, caught up on authenticated debt/budget reads."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid5, NAMESPACE_URL
from sqlalchemy import func, inspect
from app.models.debt import Debt
from app.models.debt_payment import DebtPayment
from app.routers.recurring import next_month


def today_local():
    return datetime.now(timezone(timedelta(hours=4))).date()


def totals(db, debt):
    from app.routers.debts import estimate
    monthly, interest = estimate(debt.balance, debt.annual_rate, debt.remaining_months)
    baseline = debt.total_due_cents if debt.total_due_cents is not None else round((float(debt.balance) + interest) * 100)
    paid = db.query(func.coalesce(func.sum(DebtPayment.applied_cents), 0)).filter_by(user_id=debt.user_id, debt_id=debt.id).scalar()
    return max(0, baseline - paid), debt.fixed_monthly_cents if debt.fixed_monthly_cents is not None else round(monthly * 100)


def initialize(debt):
    from app.routers.debts import estimate
    monthly, interest = estimate(debt.balance, debt.annual_rate, debt.remaining_months)
    debt.total_due_cents = round((Decimal(str(debt.balance)) + Decimal(str(interest))) * 100)
    debt.fixed_monthly_cents = round(Decimal(str(monthly)) * 100)


def sync(db, user_id, today=None):
    if not inspect(db.get_bind()).has_table("debts") or "next_due" not in {c["name"] for c in inspect(db.get_bind()).get_columns("debts")}:
        return
    today = today or today_local()
    schedules = db.query(Debt).filter(Debt.user_id == user_id, Debt.automatic_day.isnot(None), Debt.next_due <= today).all()
    changed = False
    for debt in schedules:
        while debt.next_due and debt.next_due <= today:
            due = debt.next_due
            following = next_month(due, debt.automatic_day)
            with db.begin_nested():
                claimed = db.query(Debt).filter_by(id=debt.id, user_id=user_id, next_due=due).update({"next_due": following}, synchronize_session=False)
                if not claimed:
                    break
                remaining, monthly = totals(db, debt)
                # A manual payment in this instalment's month covers that amount.
                start = due.replace(day=1)
                end = next_month(start, 1)
                paid = db.query(func.coalesce(func.sum(DebtPayment.amount_cents), 0)).filter(
                    DebtPayment.user_id == user_id, DebtPayment.debt_id == debt.id,
                    DebtPayment.paid_on >= start, DebtPayment.paid_on < end).scalar()
                amount = min(remaining, max(0, monthly - paid))
                if amount:
                    db.add(DebtPayment(user_id=user_id, debt_id=debt.id, debt_name=debt.name,
                        amount_cents=amount, applied_cents=amount, paid_on=due, automatic=True,
                        request_key=str(uuid5(NAMESPACE_URL, f"pocketpilot-debt:{user_id}:{debt.id}:{due}"))))
                    db.flush()
                changed = True
            db.refresh(debt)
            if remaining <= amount:
                debt.automatic_day = None
                debt.next_due = None
                break
    if changed:
        db.commit()
