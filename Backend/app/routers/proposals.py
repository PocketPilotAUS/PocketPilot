import json
from datetime import date as PaymentDate
from decimal import Decimal
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.chat_proposal import ChatProposal
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction

router = APIRouter(prefix="/ai/proposals", tags=["AI confirmations"])

class ProposedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["expense", "income"]
    amount: Decimal = Field(ge=0, le=1000000000, decimal_places=2, max_digits=12)
    category: str | None = Field(default=None, min_length=1, max_length=40)
    date: PaymentDate | None = None
    year: int | None = Field(default=None, ge=1, le=9998)
    month: int | None = Field(default=None, ge=1, le=12)

    @model_validator(mode="after")
    def required_details(self):
        if self.kind == "expense" and (self.amount <= 0 or not self.category or not self.category.strip() or self.date is None):
            raise ValueError("Expense needs amount, category and payment date")
        if self.kind == "income" and (self.year is None or self.month is None):
            raise ValueError("Income needs year and month")
        return self


def create_proposal(db, user_id, action):
    proposal = ChatProposal(id=str(uuid4()), user_id=user_id, payload=action.model_dump_json(), status="pending")
    db.add(proposal)
    db.commit()
    return {"id": proposal.id, **json.loads(proposal.payload), "status": "pending"}


@router.post("/{proposal_id}/confirm")
def confirm(proposal_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    proposal = db.query(ChatProposal).filter_by(id=proposal_id, user_id=current_user.id).first()
    if proposal is None:
        raise HTTPException(404, "Proposal not found")
    if proposal.status == "saved":
        return {"status": "saved"}
    if proposal.status != "pending":
        raise HTTPException(409, "This proposal is no longer pending")
    # Claim and apply in one transaction, so retrying cannot duplicate expenses.
    claimed = db.query(ChatProposal).filter_by(id=proposal_id, user_id=current_user.id, status="pending").update({"status": "saved"})
    if not claimed:
        db.rollback()
        raise HTTPException(409, "Proposal already handled. Please reopen chat.")
    action = ProposedAction.model_validate_json(proposal.payload)
    if action.kind == "expense":
        db.add(Transaction(user_id=current_user.id, amount=float(action.amount), category=action.category.strip(), date=action.date, description="Added from AI Chat"))
    else:
        income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=action.year, month=action.month).first()
        if income is None:
            income = MonthlyIncome(user_id=current_user.id, year=action.year, month=action.month)
            db.add(income)
        income.amount_cents = int(action.amount * 100)
    db.commit()
    return {"status": "saved"}


@router.post("/{proposal_id}/dismiss")
def dismiss(proposal_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    proposal = db.query(ChatProposal).filter_by(id=proposal_id, user_id=current_user.id).first()
    if proposal is None:
        raise HTTPException(404, "Proposal not found")
    if proposal.status != "pending":
        raise HTTPException(409, "This proposal is no longer pending")
    db.query(ChatProposal).filter_by(id=proposal_id, user_id=current_user.id, status="pending").update({"status": "dismissed"})
    db.commit()
    return {"status": "dismissed"}
