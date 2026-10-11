import json
from uuid import uuid4
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.financial_plan import PlanningProfile, FinancialPlan
from app.schemas.planning import PlanningInput
from app.services.planning import planning_context, evaluate

router = APIRouter(prefix="/planning", tags=["Financial plans"])


def calculate(body, db, user_id):
    try:
        return evaluate(body, planning_context(db, user_id))
    except ValueError as error:
        raise HTTPException(422, str(error)) from None


def save_profile(db, user_id, body):
    row = db.get(PlanningProfile, user_id)
    if row is None:
        row = PlanningProfile(user_id=user_id)
        db.add(row)
    row.payload = body.model_dump_json()


@router.get("/context")
def context(current_user: CurrentUser, db: Session = Depends(get_db)):
    return planning_context(db, current_user.id)


@router.put("/profile")
def profile(body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    result = calculate(body, db, current_user.id)
    save_profile(db, current_user.id, body)
    db.commit()
    return result


@router.post("/preview")
def preview(body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return calculate(body, db, current_user.id)


@router.get("/plans")
def plans(current_user: CurrentUser, db: Session = Depends(get_db)):
    return [dict(json.loads(row.payload), id=row.id) for row in db.query(FinancialPlan).filter_by(user_id=current_user.id).order_by(FinancialPlan.id).all()]


def persist(body, db, user_id, row=None):
    result = calculate(body, db, user_id)
    if not result["ready"]:
        raise HTTPException(422, "Complete the household, goal and monthly expenses first")
    result["createdOn"] = date.today().isoformat()
    if row is None:
        row = FinancialPlan(id=str(uuid4()), user_id=user_id)
        db.add(row)
    row.payload = json.dumps(result)
    save_profile(db, user_id, body)
    db.commit()
    return dict(result, id=row.id)


@router.post("/plans", status_code=201)
def create(body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return persist(body, db, current_user.id)


def owned(db, user_id, plan_id):
    row = db.query(FinancialPlan).filter_by(user_id=user_id, id=plan_id).first()
    if not row:
        raise HTTPException(404, "Plan not found")
    return row


@router.put("/plans/{plan_id}")
def update(plan_id: str, body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return persist(body, db, current_user.id, owned(db, current_user.id, plan_id))


@router.delete("/plans/{plan_id}", status_code=204)
def delete(plan_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.delete(owned(db, current_user.id, plan_id))
    db.commit()
