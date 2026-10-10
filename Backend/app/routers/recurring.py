from calendar import monthrange
from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.recurring import RecurringExpense, RecurringOccurrence
from app.models.transaction import Transaction

router = APIRouter(prefix="/recurring", tags=["Recurring expenses"])

def today_local():
    # UAE app currency/timezone; fixed offset avoids Windows tzdata dependency.
    from datetime import timezone, timedelta
    return datetime.now(timezone(timedelta(hours=4))).date()

def due_date(year, month, day):
    return date(year, month, min(day, monthrange(year, month)[1]))

def next_month(value, day):
    return due_date(value.year + (value.month == 12), value.month % 12 + 1, day)

def sync_recurring(db, user_id, today=None):
    # Older databases can keep serving existing endpoints until init_db adds new tables.
    if not inspect(db.get_bind()).has_table("recurring_expenses"):
        return
    today = today or today_local()
    schedules = db.query(RecurringExpense).filter_by(user_id=user_id, active=True).all()
    for schedule in schedules:
        while schedule.next_date <= today:
            due = schedule.next_date
            try:
                with db.begin_nested():
                    claimed = db.query(RecurringExpense).filter_by(id=schedule.id, next_date=due, active=True).update({"next_date": next_month(due, schedule.day)}, synchronize_session=False)
                    if not claimed:
                        break
                    expense = Transaction(user_id=user_id, amount=schedule.amount_cents / 100, category=schedule.category, description=schedule.description, date=due)
                    db.add(expense)
                    db.flush()
                    db.add(RecurringOccurrence(schedule_id=schedule.id, due_date=due, transaction_id=expense.id))
                    db.flush()
                db.refresh(schedule)
            except IntegrityError:
                db.refresh(schedule)
                break
    db.commit()

class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(gt=0, le=1000000000, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=500)
    day: int = Field(ge=1, le=31)
    @field_validator("category")
    @classmethod
    def clean_category(cls, value):
        if not value.strip(): raise ValueError("Category required")
        return value.strip()

class CreateSchedule(ScheduleInput):
    request_key: UUID

def view(schedule):
    return {"id": schedule.id, "amount": schedule.amount_cents / 100, "category": schedule.category,
            "description": schedule.description, "day": schedule.day, "next_date": schedule.next_date, "active": schedule.active}

@router.get("/")
def list_schedules(current_user: CurrentUser, db: Session = Depends(get_db)):
    sync_recurring(db, current_user.id)
    return [view(row) for row in db.query(RecurringExpense).filter_by(user_id=current_user.id).order_by(RecurringExpense.id).all()]

@router.post("/", status_code=201)
def create(body: CreateSchedule, current_user: CurrentUser, db: Session = Depends(get_db)):
    existing = db.query(RecurringExpense).filter_by(user_id=current_user.id, request_key=str(body.request_key)).first()
    if existing: return view(existing)
    today = today_local()
    schedule = RecurringExpense(user_id=current_user.id, request_key=str(body.request_key), amount_cents=int(body.amount * 100), category=body.category, description=body.description, day=body.day, next_date=next_month(today, body.day), active=True)
    db.add(schedule)
    try:
        db.flush()
        # The form records today's payment; recurrence begins next month.
        expense = Transaction(user_id=current_user.id, amount=float(body.amount), category=body.category, description=body.description, date=today)
        db.add(expense)
        db.flush()
        db.add(RecurringOccurrence(schedule_id=schedule.id, due_date=today, transaction_id=expense.id))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(RecurringExpense).filter_by(user_id=current_user.id, request_key=str(body.request_key)).first()
        if existing: return view(existing)
        raise
    return view(schedule)

def owned(db, user_id, schedule_id):
    schedule = db.query(RecurringExpense).filter_by(id=schedule_id, user_id=user_id).first()
    if not schedule: raise HTTPException(404, "Recurring expense not found")
    return schedule

@router.put("/{schedule_id}")
def edit(schedule_id: int, body: ScheduleInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    sync_recurring(db, current_user.id)
    schedule = owned(db, current_user.id, schedule_id)
    if not schedule.active: raise HTTPException(409, "This schedule is stopped")
    schedule.amount_cents = int(body.amount * 100)
    schedule.category = body.category
    schedule.description = body.description
    schedule.day = body.day
    schedule.next_date = due_date(schedule.next_date.year, schedule.next_date.month, body.day)
    if schedule.next_date <= today_local(): schedule.next_date = next_month(schedule.next_date, body.day)
    db.commit()
    return view(schedule)

@router.post("/{schedule_id}/stop")
def stop(schedule_id: int, current_user: CurrentUser, db: Session = Depends(get_db)):
    schedule = owned(db, current_user.id, schedule_id)
    schedule.active = False
    db.commit()
    return view(schedule)
