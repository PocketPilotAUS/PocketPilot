"""Durable financial-plan reviews in the Financial Plan review registry.

Registry entries never represent income, expenses or savings deposits.
"""
import json
import re
import time
from uuid import uuid4
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from app.models.plan_review import PlanReview
from app.models.financial_plan import FinancialPlan


def owned(db, user_id, key, lock=False):
    query=db.query(PlanReview).filter_by(id=key,user_id=user_id)
    row=(query.with_for_update() if lock else query).first()
    if row is None or not json.loads(row.payload).get("_financial_plan"):
        raise HTTPException(404,"Financial Plan review not found")
    return row


def register(db,user_id,plan):
    if not plan or not plan.get("ready") or plan.get("id"):
        return plan
    key=plan.get("confirmationKey") or str(uuid4())
    row=db.get(PlanReview,key)
    if row:
        row=owned(db,user_id,key)
        return dict(plan,reviewId=key,reviewStatus=status(db,row))
    reviewed=dict(plan,reviewId=key,reviewStatus="pending")
    payload={"_financial_plan":True,"expires_at":int(time.time())+1800,"plan":reviewed}
    db.add(PlanReview(id=key,user_id=user_id,status="pending",payload=json.dumps(payload)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        owned(db,user_id,key)
    return reviewed



def saved_plan(db,row):
    exact=db.query(FinancialPlan).filter_by(id=row.id,user_id=row.user_id).first()
    if exact:
        return exact
    return next((plan for plan in db.query(FinancialPlan).filter_by(user_id=row.user_id).all()
                 if json.loads(plan.payload).get("confirmationKey")==row.id),None)


def status(db,row):
    saved=saved_plan(db,row)
    if saved:
        desired="saved"
    elif row.status in ("pending","accepting") and json.loads(row.payload)["expires_at"]<=time.time():
        desired="expired"
    else:
        return row.status
    if desired!=row.status:
        db.query(PlanReview).filter_by(id=row.id,user_id=row.user_id,status=row.status).update({"status":desired})
        db.commit()
        db.refresh(row)
    return row.status


def guard(db,user_id,key,allow_legacy=False):
    row=db.get(PlanReview,key)
    if row is None and allow_legacy:
        return None
    row=owned(db,user_id,key,lock=True)
    state=status(db,row)
    if state=="saved":
        saved=saved_plan(db,row)
        if saved is None:
            raise HTTPException(409,"This Financial Plan acceptance was already consumed. Create a new plan.")
        reviewed=json.loads(row.payload)["plan"]
        current=json.loads(saved.payload)
        if reviewed.get("budgetGoalSource"):
            same=(current.get("debtConfirmation")==reviewed.get("debtConfirmation")) if reviewed.get("debtGoalSource") else current.get("confirmationKey")==row.id
            if not same:
                raise HTTPException(409,"This Financial Plan was updated. Review a new plan.")
    own_claim=db.info.get("plan_claim")
    same_claim=own_claim and own_claim["key"]==key and own_claim["nonce"]==json.loads(row.payload).get("_claim")
    if state=="accepting" and same_claim:
        return row
    if state not in ("pending","saved"):
        raise HTTPException(409,f"This Financial Plan was {state} and can no longer be accepted. Create a new plan.")
    return row


def checked_budget(db,user_id,body):
    row=guard(db,user_id,str(body.request_key))
    from app.schemas.planning import PlanningInput
    from app.routers.chat import BudgetChoices
    plan=json.loads(row.payload)["plan"]
    if not plan.get("budgetGoalSource") or plan.get("debtGoalSource"):
        raise HTTPException(409,"Choose the matching Financial Plan acceptance control")
    # Decimal equality tolerates JavaScript serializing 10000.0 as 10000 while
    # still requiring every reviewed financial fact to match.
    expected=(PlanningInput.model_validate(plan["profile"]),
              BudgetChoices.model_validate(plan.get("budgetChoices",{})),plan["budgetFingerprint"])
    actual=(body.profile,body.choices,body.budget_fingerprint)
    if actual!=expected:
        raise HTTPException(409,"The reviewed Financial Plan details changed. Review a new plan.")
    acquire(db,user_id,str(body.request_key))
    return row


def reject(db,user_id,key):
    row=owned(db,user_id,key,lock=True)
    state=status(db,row)
    if state=="accepting":
        raise HTTPException(409,"This Financial Plan is being accepted. Please refresh before rejecting it.")
    if state=="pending":
        changed=db.query(PlanReview).filter_by(id=key,user_id=user_id,status="pending").update({"status":"rejected"})
        if not changed:
            db.rollback()
            raise HTTPException(409,"This Financial Plan was already handled")
        db.commit();state="rejected"
    return {"review_id":key,"status":state}


def reference(db,user_id,rows,semantic,latest,currency,rate):
    candidates=list(rows)
    named=[row for row in candidates if json.loads(row.payload)["plan"]["title"].casefold() in latest.casefold()]
    if named:
        candidates=named
    if not candidates:
        return {"reply":"I can't find that Financial Plan in this chat. Please create a new plan. Nothing has been saved."}
    if len(candidates)!=1:
        return {"reply":"Which Financial Plan do you mean? Please specify its goal. Nothing has been saved."}
    row=candidates[0];state=status(db,row);plan=json.loads(row.payload)["plan"]
    amount=Decimal(str(plan["targetAmount"]))*(rate if currency=="CNY" else Decimal(1))
    kind_label="savings plan" if plan.get("kind")=="savings" else "financial plan"
    label=f"{currency} {amount:,.2f} {plan['title']} {kind_label}"
    update={"review_id":row.id,"status":state}
    if state=="accepting":
        return {"reply":f"Your {label} is being accepted. Please wait and refresh its status."}
    if state=="saved":
        saved=saved_plan(db,row)
        if saved:
            update["plan"]=dict(json.loads(saved.payload),id=saved.id,reviewId=row.id,reviewStatus="saved")
            reply=f"Your {label} was already accepted and saved. Nothing else has been changed."
        else:
            reply=f"Your {label} was already accepted and is no longer available. Please create a new plan."
    elif state in ("rejected","expired"):
        reply=f"Your {label} was {state} and can no longer be accepted. If you'd like to proceed, please create a new plan."
    else:
        reply=f"Your {label} is still pending. Use Accept plan to save it or Reject to decline it. Nothing has been saved."
    return {"reply":reply,"plan_updates":[update]}



def acquire(db,user_id,key,allow_legacy=False):
    row=guard(db,user_id,key,allow_legacy)
    if row is None or row.status in ("saved","accepting"):
        return row
    nonce=str(uuid4())
    payload=json.loads(row.payload);payload["_claim"]=nonce
    changed=db.query(PlanReview).filter_by(id=key,user_id=user_id,status="pending").update(
        {"status":"accepting","payload":json.dumps(payload)})
    if not changed:
        db.rollback()
        raise HTTPException(409,"This Financial Plan is already being handled. Please refresh.")
    db.commit()
    db.info["plan_claim"]={"key":key,"nonce":nonce,"user_id":user_id}
    return row


def run_acceptance(db,operation):
    try:
        result=operation()
        claim=db.info.get("plan_claim")
        if claim:
            db.query(PlanReview).filter_by(id=claim["key"],user_id=claim["user_id"],status="accepting").update({"status":"saved"})
            db.commit()
        return result
    except Exception:
        claim=db.info.get("plan_claim")
        db.rollback()
        if claim:
            row=db.get(PlanReview,claim["key"])
            if row and row.status=="accepting" and json.loads(row.payload).get("_claim")==claim["nonce"]:
                payload=json.loads(row.payload);payload.pop("_claim",None)
                state="saved" if saved_plan(db,row) else "expired" if payload["expires_at"]<=time.time() else "pending"
                db.query(PlanReview).filter_by(id=row.id,user_id=claim["user_id"],status="accepting").update({"status":state,"payload":json.dumps(payload)})
                db.commit()
        raise



def is_reference(semantic, latest, history):
    if semantic.intent=="financial_plan":
        return True
    if not history or not re.search(r"\bplan\b",latest,re.I):
        return False
    if semantic.intent=="proposal":
        return True
    # Model task labels can conflict with the actual referenced acceptance
    # operation. This guard authorizes only a status read, never a new plan.
    return (semantic.intent in ("record","plan","read")
            and semantic.savings_operation!="affordability"
            and re.search(r"\b(?:accept|approve|confirm|finalize)\b",latest,re.I) is not None)
