import json
from uuid import uuid4
from datetime import date, datetime, timedelta, timezone
from pydantic import BaseModel, ConfigDict, Field
from app.routers.chat import BudgetChoices
from app.routers.budget import ideal_budget
from app.models.income import MonthlyIncome
from decimal import Decimal
from app.services.budget_goals import draft_plan, fingerprint
from uuid import UUID
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import CurrentUser
from app.models.financial_plan import PlanningProfile, FinancialPlan
from app.schemas.planning import PlanningInput
from app.services.planning import planning_context, evaluate
from app.services.goal_savings import assignable, contributions, with_progress
from app.models.savings import ManualSavings

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
    totals = contributions(db, current_user.id)
    return [with_progress(dict(json.loads(row.payload), id=row.id), totals.get(row.id))
            for row in db.query(FinancialPlan).filter_by(user_id=current_user.id).order_by(FinancialPlan.id).all()]


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


def progress(db, user_id, plan):
    """A saved plan as listed, including savings assigned to it."""
    return with_progress(plan, contributions(db, user_id).get(plan["id"]))


def owned(db, user_id, plan_id):
    row = db.query(FinancialPlan).filter_by(user_id=user_id, id=plan_id).first()
    if not row:
        raise HTTPException(404, "Plan not found")
    return row


@router.put("/plans/{plan_id}")
def update(plan_id: str, body: PlanningInput, current_user: CurrentUser, db: Session = Depends(get_db)):
    return progress(db, current_user.id, persist(body, db, current_user.id, owned(db, current_user.id, plan_id)))


@router.delete("/plans/{plan_id}", status_code=204)
def delete(plan_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    row = owned(db, current_user.id, plan_id)
    if assignable(db):
        # Savings stay recorded; they just stop counting toward the removed goal
        db.query(ManualSavings).filter_by(user_id=current_user.id, goal_id=plan_id).update({"goal_id": None})
    db.delete(row)
    db.commit()


class BudgetGoalSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: PlanningInput
    choices: BudgetChoices = Field(default_factory=BudgetChoices)
    budget_fingerprint: str = Field(min_length=64, max_length=64)
    request_key: UUID


class DebtGoalSave(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=16000)
    apply_to_budget: bool | None = Field(default=None, strict=True)


class DebtGoalPreview(DebtGoalSave):
    deadline: date | None = None
    monthly_payment: Decimal | None = Field(default=None, gt=0, le=1_000_000_000, decimal_places=2, allow_inf_nan=False)
    plan_id: str | None = Field(default=None, max_length=36)


def debt_goal_basis(db, user_id, today):
    from app.routers.budget import summary
    result = summary(db, user_id, today.year, today.month, include_debt=True)
    if result['ideal_budget'] is None or result['income'] is None:
        raise HTTPException(422, 'Save this month\'s budget before reviewing a debt plan.')
    return result


@router.post('/debt-plans/preview')
def preview_debt_goal(body: DebtGoalPreview, current_user: CurrentUser, db: Session = Depends(get_db)):
    from app.services.debt_planning import unseal, snapshot, scenario, draft
    today = local_today()
    if body.plan_id:
        row = owned(db, current_user.id, body.plan_id)
        saved = json.loads(row.payload)
        if not saved.get('debtGoalSource'):
            raise HTTPException(422, 'Choose a debt repayment plan.')
        if saved.get('debtConfirmation') != body.token:
            raise HTTPException(409, 'This plan was updated. Reopen it before adjusting.')
    # A saved plan remains editable after its original review token expires.
    # Only the authenticated owner with the exact stored token may refresh it.
    values = unseal(body.token, current_user.id, 'debt_draft', allow_expired=body.plan_id is not None)
    budget = debt_goal_basis(db, current_user.id, today)
    data = snapshot(db, current_user.id, budget, today, values['debt_ids'], body.plan_id)
    deadline = body.deadline.isoformat() if body.deadline else values['deadline']
    chosen = float(body.monthly_payment) if body.monthly_payment is not None else None
    result = scenario(data, deadline, chosen, today)
    if not result or not result['feasible']:
        raise HTTPException(422, 'Choose a future deadline and a total monthly payment that fits your saved budget.')
    if body.monthly_payment is not None and body.monthly_payment < Decimal(str(data['regular'])):
        raise HTTPException(422, 'Keep making at least your required monthly payments.')
    return draft(data, result, budget, today, current_user.id, {'chosen': chosen}, body.plan_id)


def persist_debt_goal(body, user_id, db, existing=None):
    from app.services.debt_planning import unseal, seal, snapshot, scenario, draft
    values = unseal(body.token, user_id, 'debt_draft')
    key = values['key']
    existing_id = existing.id if existing else None
    if values.get('replace_id') != existing_id:
        raise HTTPException(409, 'Review this plan again before saving it.')
    previous = db.get(FinancialPlan, existing_id or key)
    if previous and previous.user_id == user_id and json.loads(previous.payload).get('debtConfirmation') == body.token:
        if body.apply_to_budget is not None and bool(json.loads(previous.payload).get('budgetApplied')) != body.apply_to_budget:
            raise HTTPException(409, 'This plan was already saved with a different budget choice. Adjust it to change the target.')
        return dict(json.loads(previous.payload), id=previous.id)
    if previous and not existing:
        raise HTTPException(409, 'This confirmation was already used. Review a new plan.')
    today = local_today()
    budget = debt_goal_basis(db, user_id, today)
    data = snapshot(db, user_id, budget, today, values['debt_ids'], existing_id)
    if data['snapshot'] != values['snapshot']:
        raise HTTPException(409, 'Your budget, debts, goals or planning date changed. Review the debt plan again before confirming.')
    result = scenario(data, values['deadline'], values.get('chosen'), today)
    if not result or not result['feasible']:
        raise HTTPException(422, 'This repayment target no longer fits the saved budget.')
    for row in db.query(FinancialPlan).filter_by(user_id=user_id).all():
        saved = json.loads(row.payload)
        if row.id != existing_id and saved.get('debtGoalSource') and set(saved.get('debtIds', [])) & set(values['debt_ids']):
            raise HTTPException(409, 'A repayment plan already covers this debt. Adjust that saved plan instead.')
    verified = draft(data, result, budget, today, user_id, values, existing_id)
    verified.update(confirmationKey=key, debtConfirmation=body.token, createdOn=today.isoformat())
    previous_data = json.loads(existing.payload) if existing else {}
    applied = body.apply_to_budget if body.apply_to_budget is not None else bool(previous_data.get('budgetApplied'))
    verified.update(budgetApplied=applied,
                    budgetAppliedFrom=(previous_data.get('budgetAppliedFrom') or today.strftime('%Y-%m')) if applied else None)
    verified['debtState'] = seal({'debt_ids': data['debt_ids'], 'deadline': result['deadline'],
                                  'chosen': values.get('chosen'), 'snapshot': data['snapshot'],
                                  'phase': 'saved', 'plan_key': existing_id or key}, user_id, 'debt_conversation')
    row = existing or FinancialPlan(id=key, user_id=user_id)
    row.payload = json.dumps(verified)
    if not existing:
        db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.get(FinancialPlan, key)
        if previous and previous.user_id == user_id and json.loads(previous.payload).get('debtConfirmation') == body.token:
            return dict(json.loads(previous.payload), id=previous.id)
        raise HTTPException(409, 'This confirmation changed. Review the plan again.') from None
    return dict(verified, id=row.id)


@router.post('/debt-plans', status_code=201)
def confirm_debt_goal(body: DebtGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.commit()
    if db.get_bind().dialect.name == 'sqlite':
        from sqlalchemy import text
        db.execute(text('BEGIN IMMEDIATE'))
    return persist_debt_goal(body, current_user.id, db)


@router.put('/debt-plans/{plan_id}')
def update_debt_goal(plan_id: str, body: DebtGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    db.commit()
    if db.get_bind().dialect.name == 'sqlite':
        from sqlalchemy import text
        db.execute(text('BEGIN IMMEDIATE'))
    row = owned(db, current_user.id, plan_id)
    if not json.loads(row.payload).get('debtGoalSource'):
        raise HTTPException(422, 'Choose a debt repayment plan.')
    return persist_debt_goal(body, current_user.id, db, row)


def persist_budget_goal(body, user_id, db, existing=None):
    today = datetime.now(timezone(timedelta(hours=4))).date()
    request_key = str(body.request_key)
    facts = json.dumps({"profile": body.profile.model_dump(mode="json"), "choices": body.choices.model_dump(mode="json"), "budget": body.budget_fingerprint}, sort_keys=True)
    def retry(row):
        data = json.loads(row.payload)
        if row.user_id != user_id or data.get("confirmationFacts") != facts:
            raise HTTPException(409, "This confirmation was already used. Review a new draft.")
        return dict(data, id=row.id)
    if existing is None:
        previous = db.get(FinancialPlan, request_key)
        if previous:
            return retry(previous)
    income = db.query(MonthlyIncome).filter_by(user_id=user_id, year=today.year, month=today.month).first()
    amount = Decimal(income.amount_cents) / 100 if income else None
    budget = {"year": today.year, "month": today.month, "income": float(amount) if amount is not None else None,
              "ideal_budget": ideal_budget(db, user_id, today.year, today.month, amount, {})}
    if budget["ideal_budget"] is None or budget["income"] is None:
        raise HTTPException(422, "Save your monthly budget before confirming a plan.")
    if fingerprint(budget) != body.budget_fingerprint:
        raise HTTPException(409, "Your budget changed. Ask AI Chat to refresh the plan before confirming.")
    result = draft_plan(body.profile.model_dump(mode="json"), budget, today, body.choices.model_dump(mode="json"))
    if result is None:
        raise HTTPException(422, "Review the goal, monthly contribution and deadline before confirming.")
    result.update(confirmationKey=request_key, confirmationFacts=facts, createdOn=today.isoformat())
    row = existing or FinancialPlan(id=request_key, user_id=user_id)
    row.payload = json.dumps(result)
    if existing is None:
        db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous = db.get(FinancialPlan, request_key)
        if previous is None:
            raise
        return retry(previous)
    return dict(result, id=row.id)


@router.post("/budget-plans", status_code=201)
def confirm_budget_plan(body: BudgetGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    user_id = current_user.id
    db.commit()
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import text
        db.execute(text("BEGIN IMMEDIATE"))
    return progress(db, user_id, persist_budget_goal(body, user_id, db))


@router.put("/budget-plans/{plan_id}")
def update_budget_goal(plan_id: str, body: BudgetGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    user_id = current_user.id
    db.commit()
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import text
        db.execute(text("BEGIN IMMEDIATE"))
    row = owned(db, user_id, plan_id)
    if not json.loads(row.payload).get("budgetGoalSource"):
        raise HTTPException(422, "Use the regular editor for this plan.")
    return progress(db, user_id, persist_budget_goal(body, user_id, db, row))


@router.post("/budget-plans/preview")
def preview_budget_goal(body: BudgetGoalSave, current_user: CurrentUser, db: Session = Depends(get_db)):
    today = datetime.now(timezone(timedelta(hours=4))).date()
    income = db.query(MonthlyIncome).filter_by(user_id=current_user.id, year=today.year, month=today.month).first()
    amount = Decimal(income.amount_cents) / 100 if income else None
    budget = {"year": today.year, "month": today.month, "income": float(amount) if amount is not None else None,
              "ideal_budget": ideal_budget(db, current_user.id, today.year, today.month, amount, {})}
    if budget["ideal_budget"] is None or amount is None:
        raise HTTPException(422, "Save your monthly budget before reviewing a plan.")
    choices = body.choices.model_dump(mode="json")
    if body.budget_fingerprint != fingerprint(budget):
        choices["targets"] = {}
    result = draft_plan(body.profile.model_dump(mode="json"), budget, today, choices)
    if result is None:
        raise HTTPException(422, "Choose a complete goal and an affordable monthly amount or future deadline.")
    return result


# Spending monitoring and AI budget adjustments for the current month

def local_today():
    return datetime.now(timezone(timedelta(hours=4))).date()


def adjustment_history(db, user_id, year, month):
    from app.models.budget_plan import BudgetPlan
    row = db.query(BudgetPlan).filter_by(user_id=user_id, year=year, month=month).first()
    return json.loads(row.percentages).get("adjustments", []) if row else []


@router.get("/status")
def spending_status_view(current_user: CurrentUser, db: Session = Depends(get_db)):
    from app.services.spending_monitor import spending_status
    today = local_today()
    status = spending_status(db, current_user.id, today)
    status["adjustments"] = adjustment_history(db, current_user.id, today.year, today.month)
    return status


class AdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instructions: str | None = Field(default=None, max_length=500)
    # The savings plan being viewed, for its recovery options
    plan_id: str | None = Field(default=None, max_length=36)


@router.post("/adjustments/proposal")
def propose_adjustment(body: AdjustmentRequest, current_user: CurrentUser, db: Session = Depends(get_db)):
    from app.ai.client import generate_budget_adjustment
    from app.services.spending_monitor import spending_status
    from app.services.budget_adjustments import advice, check_changes, currency_text, realistic_floor, summarize, target_amount
    today = local_today()
    status = spending_status(db, current_user.id, today)
    if not status["has_budget"]:
        raise HTTPException(422, "Save this month's budget in Budget Tracker first.")
    if status["level"] == 0:
        raise HTTPException(422, "Your spending is within budget and your goals look achievable. No adjustment is needed.")
    mode = "advice" if status["level"] == 1 else "recovery" if status["level"] == 3 else "adjust"
    context = {"days_left": status["days_left"], "level": status["level"], "goal_amount": float(target_amount(status)),
               "income": status["income"], "required_savings": status["required_contributions"],
               "over_budget": status["over_budget"], "upcoming_bills": status["upcoming_bills"],
               "forecast_confidence": status["forecast_confidence"],
               "currency": "AED",
               # Per category: projected month-end spending and the lowest realistic limit
               "categories": [{"category": row["category"], "budget": row["budget"], "spent": row["spent"], "upcoming_bills": row["upcoming"],
                               "projected": row["forecast"], "lowest_realistic_limit": float(realistic_floor(row)),
                               "fixed": row["method"] in ("fixed", "adjusted")} for row in status["categories"]]}
    try:
        raw = json.loads(generate_budget_adjustment(context, body.instructions, mode))
        suggestions = raw.get("changes") if isinstance(raw, dict) else None
        if not isinstance(suggestions, list):
            raise ValueError("Invalid proposal")
        tips = [currency_text(tip.strip()[:200]) for tip in raw.get("tips") or [] if isinstance(tip, str) and tip.strip()][:3]
    except Exception:
        if mode == "advice":
            # The goal is affordable: the verified breakdown is still useful without AI tips
            return advice(status, [])
        raise HTTPException(503, "AI suggestions are temporarily unavailable. Please try again.") from None
    if mode == "advice":
        return advice(status, tips)
    changes, notes = check_changes(status, [item for item in suggestions if isinstance(item, dict)], strict=False)
    plan = None
    if body.plan_id:
        row = db.query(FinancialPlan).filter_by(user_id=current_user.id, id=body.plan_id).first()
        if row is not None:
            plan = progress(db, current_user.id, dict(json.loads(row.payload), id=row.id))
            plan = plan if plan.get("kind") == "savings" else None
    # Free-text tips could contradict the checked limits, so proposals show only those limits
    return summarize(status, changes, notes, plan, today)


class AdjustmentChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(min_length=1, max_length=40)
    # Most the user plans to spend in the category by month-end
    limit: Decimal = Field(ge=0, le=1_000_000_000, max_digits=12, decimal_places=2, allow_inf_nan=False)


class AdjustmentAccept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fingerprint: str = Field(min_length=64, max_length=64)
    request_key: UUID
    changes: list[AdjustmentChange] = Field(min_length=1, max_length=50)


@router.post("/adjustments/accept")
def accept_adjustment(body: AdjustmentAccept, current_user: CurrentUser, db: Session = Depends(get_db)):
    from app.models.budget_plan import BudgetPlan
    from app.services.spending_monitor import spending_status
    from app.services.budget_adjustments import check_changes, apply_changes
    today = local_today()
    # spending_status records due recurring expenses and commits, so run it before locking
    status = spending_status(db, current_user.id, today)
    db.commit()
    if db.get_bind().dialect.name == "sqlite":
        from sqlalchemy import text
        db.execute(text("BEGIN IMMEDIATE"))
    row = db.query(BudgetPlan).filter_by(user_id=current_user.id, year=today.year, month=today.month).first()
    payload = json.loads(row.percentages) if row else {}
    history = payload.get("adjustments", [])
    key = str(body.request_key)
    if any(entry.get("request_key") == key for entry in history):
        # A repeated tap: already applied once
        db.rollback()
        return spending_status_view(current_user, db)
    if payload.get("version") != 2:
        db.rollback()
        raise HTTPException(422, "Save this month's budget in Budget Tracker first.")
    if status["fingerprint"] != body.fingerprint:
        db.rollback()
        raise HTTPException(409, "Your spending changed since this proposal was made. Review a new proposal.")
    try:
        changes, _ = check_changes(status, [change.model_dump(mode="json") for change in body.changes], strict=True)
    except ValueError as error:
        db.rollback()
        raise HTTPException(422, str(error)) from None
    if not changes:
        db.rollback()
        raise HTTPException(422, "This proposal doesn't reduce any spending.")
    history.append({"request_key": key, "accepted_on": today.isoformat(), "previous": payload["categories"],
                    "changes": [{"category": change["category"], "current": change["budget"], "proposed": change["budget_after"],
                                 "limit": change["limit"], "avoided": change["avoided"]} for change in changes]})
    payload["categories"] = apply_changes(payload["categories"], changes)
    payload["adjustments"] = history
    row.percentages = json.dumps(payload)
    db.commit()
    return spending_status_view(current_user, db)
