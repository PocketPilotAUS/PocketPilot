import json
import time
from datetime import date as PaymentDate
from decimal import Decimal
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.chat_proposal import ChatProposal
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction

router = APIRouter(prefix="/ai/proposals", tags=["AI confirmations"])

class ProposedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["expense", "income"]
    income_operation: Literal["add", "replace"] = "replace"
    income_before: Decimal | None = Field(default=None, ge=0, le=1000000000, decimal_places=2, allow_inf_nan=False)
    income_after: Decimal | None = Field(default=None, ge=0, le=1000000000, decimal_places=2, allow_inf_nan=False)
    amount: Decimal = Field(ge=0, le=1000000000, decimal_places=2, max_digits=12)
    category: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, min_length=1, max_length=200)
    date: PaymentDate | None = None
    year: int | None = Field(default=None, ge=1, le=9998)
    month: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def required_details(self):
        if self.kind == "expense" and (self.amount <= 0 or not self.category or not self.category.strip() or self.date is None):
            raise ValueError("Expense needs amount, category and payment date")
        if self.kind == "income" and (self.year is None or self.month is None):
            raise ValueError("Income needs year and month")
        if self.kind == "income" and self.income_operation == "add":
            if self.amount <= 0 or self.date is None or (self.year, self.month) != (self.date.year, self.date.month):
                raise ValueError("An income receipt needs a positive amount and received date")
            if self.income_after != (self.income_before or Decimal(0)) + self.amount:
                raise ValueError("Income receipt needs a verified before/after total")
        elif self.kind == "income" and self.income_after is not None and self.income_after != self.amount:
            raise ValueError("Monthly income replacement total must equal the proposed amount")
        return self


def owned_proposal(db, user_id, proposal_id):
    row = db.query(ChatProposal).filter_by(id=proposal_id, user_id=user_id).first()
    if row is None:
        raise HTTPException(404, "Proposal not found")
    return row



def expire_proposal(db, user_id, proposal):
    """Resolve expiry against persisted state, never client-supplied card status."""
    expires_at = json.loads(proposal.payload).get("_expires_at")
    if proposal.status == "pending" and expires_at is not None and expires_at <= time.time():
        db.query(ChatProposal).filter_by(id=proposal.id, user_id=user_id, status="pending").update({"status": "expired"})
        db.commit()
        db.refresh(proposal)
    return proposal


def create_proposal(db, user_id, action, draft_id=None):
    # A signed incomplete draft and its completed proposal share one durable ID.
    # A canceled/consumed draft cannot mint another confirmation.
    payload = {**action.model_dump(mode="json"), "_expires_at": int(time.time()) + 1800}
    proposal = ChatProposal(id=draft_id or str(uuid4()), user_id=user_id, payload=json.dumps(payload), status="pending")
    db.add(proposal)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This pending record was already handled. Please start a new record.") from None
    return {"id": proposal.id, **action.model_dump(mode="json"), "status": "pending"}


def dismiss_proposal(db, user_id, proposal_id):
    proposal = owned_proposal(db, user_id, proposal_id)
    if proposal.status == "dismissed":
        return {"status": "dismissed"}
    if proposal.status != "pending":
        raise HTTPException(409, "This proposal is no longer pending")
    claimed = db.query(ChatProposal).filter_by(id=proposal_id, user_id=user_id, status="pending").update({"status": "dismissed"})
    if not claimed:
        db.rollback()
        raise HTTPException(409, "This proposal was already handled")
    db.commit()
    return {"status": "dismissed"}


@router.post("/{proposal_id}/confirm")
def confirm(proposal_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    proposal = db.query(ChatProposal).filter_by(id=proposal_id, user_id=current_user.id).first()
    if proposal is None:
        raise HTTPException(404, "Proposal not found")
    if proposal.status == "saved":
        return {"status": "saved"}
    if proposal.status != "pending":
        raise HTTPException(409, "This proposal is no longer pending")
    payload = json.loads(proposal.payload)
    payload.pop("_expires_at", None)
    if expire_proposal(db, current_user.id, proposal).status == "expired":
        raise HTTPException(409, "This proposal expired. Please describe the record again.")
    # Claim and apply in one transaction, so retrying cannot duplicate expenses.
    claimed = db.query(ChatProposal).filter_by(id=proposal_id, user_id=current_user.id, status="pending").update({"status": "saved"})
    if not claimed:
        db.rollback()
        raise HTTPException(409, "Proposal already handled. Please reopen chat.")
    action = ProposedAction.model_validate(payload)
    if action.kind == "expense":
        db.add(Transaction(user_id=current_user.id, amount=float(action.amount), category=action.category.strip(), date=action.date, description=action.description or "Added from AI Chat"))
    else:
        income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=action.year, month=action.month).first()
        if action.income_after is not None:
            before = Decimal(income.amount_cents) / 100 if income is not None else None
            if before != action.income_before:
                db.rollback()
                raise HTTPException(409, "Income changed since this proposal. Ask to review it again before confirming.")
            if income is not None:
                updated = db.query(MonthlyIncome).filter_by(id=income.id, user_id=current_user.id,
                    amount_cents=income.amount_cents).update({"amount_cents": int(action.income_after * 100)})
                if updated != 1:
                    db.rollback()
                    raise HTTPException(409, "Income changed. Ask to review the proposal again.")
                db.commit()
                return {"status": "saved"}
        if income is None:
            income = MonthlyIncome(user_id=current_user.id, year=action.year, month=action.month)
            db.add(income)
        income.amount_cents = int((action.income_after if action.income_after is not None else action.amount) * 100)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if action.kind == "income":
            raise HTTPException(409, "Income changed. Ask to review the proposal again.") from None
        raise
    return {"status": "saved"}


@router.post("/{proposal_id}/dismiss")
def dismiss(proposal_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    return dismiss_proposal(db, current_user.id, proposal_id)
