"""Real review persistence and acceptance; models only classify conversation references."""
import json
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import pytest
from conftest import register_user,login_user,auth_headers
from app.models.plan_review import PlanReview
from app.models.financial_plan import FinancialPlan
from app.models.transaction import Transaction
from app.models.savings import ManualSavings
from app.models.debt_payment import DebtPayment
from app.models.income import MonthlyIncome


@pytest.fixture
def reviews(api_client,db_session):
    register_user(api_client)
    headers=auth_headers(login_user(api_client).json()["access_token"])
    today=datetime.now(timezone(timedelta(hours=4))).date()
    assert api_client.put(f"/budget/setup?year={today.year}&month={today.month}",headers=headers,
        json={"income":10000,"categories":[{"name":"Rent","amount":4000},{"name":"Food","amount":1000}]}).status_code==200
    def issue(kind="savings"):
        if kind=="debt":
            from app.routers.planning import debt_goal_basis
            from app.services.debt_planning import snapshot,scenario,draft
            loan=api_client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60}).json()
            budget=debt_goal_basis(db_session,1,today)
            data=snapshot(db_session,1,budget,today,[loan["id"]])
            calc=scenario(data,"2028-09-30",None,today)
            initial=draft(data,calc,budget,today,1,{})
            response=api_client.post("/planning/debt-plans/preview",headers=headers,json={"token":initial["debtConfirmation"]})
        elif kind in ("guided","spending"):
            from app.schemas.planning import CATEGORIES
            response=api_client.post("/planning/preview",headers=headers,json={"income":10000,"other_income":0,"household_size":1,
                "goal":"Vacation" if kind=="guided" else "Monthly budget","goal_kind":"savings" if kind=="guided" else "spending","target_amount":3000 if kind=="guided" else 6000,"current_amount":0,"deadline":"2027-07-31",
                "expenses":{key:4000 if key=="Rent" else 1000 if key=="Food" else 0 for key in CATEGORIES}})
        else:
            from app.routers.budget import summary
            from app.services.budget_goals import fingerprint
            budget=summary(db_session,1,today.year,today.month,include_debt=True)
            response=api_client.post("/planning/budget-plans/preview",headers=headers,json={"profile":{
                "goal":"Vacation","goal_kind":"savings","target_amount":3000,"current_amount":0,"monthly_contribution":300},
                "choices":{"targets":{"Food":900}} if kind=="budget" else {},
                "budget_fingerprint":fingerprint(budget),"request_key":str(uuid4())})
        assert response.status_code==200,response.text
        assert response.json()["reviewId"]
        return response.json()
    return headers,today,issue


def no_financial_records(db):
    assert db.query(FinancialPlan).count()==db.query(Transaction).count()==db.query(ManualSavings).count()==db.query(DebtPayment).count()==0
    assert db.query(MonthlyIncome).one().amount_cents==1000000


@pytest.mark.parametrize("kind",["savings","budget","debt","guided","spending"])
def test_reject_blocks_common_and_original_acceptance(reviews,api_client,db_session,kind):
    headers,_,issue=reviews
    plan=issue(kind);key=plan["reviewId"]
    for _ in range(2):
        response=api_client.post(f"/planning/reviews/{key}/reject",headers=headers)
        assert response.status_code==200 and response.json()["status"]=="rejected"
        assert api_client.post(f"/planning/reviews/{key}/accept",headers=headers,json={}).status_code==409
    if kind=="debt":
        assert api_client.post("/planning/debt-plans",headers=headers,json={"token":plan["debtConfirmation"]}).status_code==409
        assert api_client.post("/planning/debt-plans/preview",headers=headers,json={"token":plan["debtConfirmation"]}).status_code==409
    elif kind in ("savings","budget"):
        request={"profile":plan["profile"],"choices":plan["budgetChoices"],"budget_fingerprint":plan["budgetFingerprint"],"request_key":plan["confirmationKey"]}
        assert api_client.post("/planning/budget-plans",headers=headers,json=request).status_code==409
        assert api_client.post("/planning/budget-plans/preview",headers=headers,json=request).status_code==409
    no_financial_records(db_session)


@pytest.mark.parametrize("kind",["savings","budget","debt","guided","spending"])
def test_accept_retries_are_idempotent_and_late_reject_cannot_unsave(reviews,api_client,db_session,kind):
    headers,_,issue=reviews
    plan=issue(kind);key=plan["reviewId"]
    for _ in range(2):
        response=api_client.post(f"/planning/reviews/{key}/accept",headers=headers,json={})
        assert response.status_code==200,response.text
        assert response.json()["id"]==key
    rejected=api_client.post(f"/planning/reviews/{key}/reject",headers=headers)
    assert rejected.json()["status"]=="saved"
    assert db_session.query(FinancialPlan).count()==1
    assert db_session.query(Transaction).count()==db_session.query(ManualSavings).count()==db_session.query(DebtPayment).count()==0


@pytest.mark.parametrize("kind",["savings","debt","guided","spending"])
def test_expired_review_is_not_accepted(reviews,api_client,db_session,kind):
    headers,_,issue=reviews
    plan=issue(kind);row=db_session.get(PlanReview,plan["reviewId"])
    payload=json.loads(row.payload);payload["expires_at"]=1;row.payload=json.dumps(payload);db_session.commit()
    result=api_client.post(f"/planning/reviews/{row.id}/accept",headers=headers,json={})
    assert result.status_code==409 and "expired" in result.text
    no_financial_records(db_session)


def test_foreign_review_is_not_read_rejected_or_accepted(reviews,api_client,db_session):
    headers,_,issue=reviews
    plan=issue()
    register_user(api_client,email="bob@example.com")
    bob=auth_headers(login_user(api_client,email="bob@example.com").json()["access_token"])
    for verb in ("accept","reject"):
        response=api_client.post(f"/planning/reviews/{plan['reviewId']}/{verb}",headers=bob,json={})
        assert response.status_code==404
    response=api_client.post("/ai/chat",headers=bob,json={"messages":[{"role":"user","content":"accept that plan"}],"plan_review_ids":[plan["reviewId"]]})
    assert response.status_code==404
    no_financial_records(db_session)


@pytest.mark.parametrize("state",["pending","rejected","saved","expired"])
@pytest.mark.parametrize("intent",["financial_plan","proposal","plan"])
def test_plan_reference_after_topic_switch_never_uses_transaction_words_or_creates_plan(reviews,api_client,db_session,monkeypatch,state,intent):
    headers,_,issue=reviews
    plan=issue();key=plan["reviewId"]
    if state in ("saved","rejected"):
        api_client.post(f"/planning/reviews/{key}/"+("accept" if state=="saved" else "reject"),headers=headers,json={})
    elif state=="expired":
        row=db_session.get(PlanReview,key);data=json.loads(row.payload);data["expires_at"]=1;row.payload=json.dumps(data);db_session.commit()
    text="Actually, can you accept that vacation savings plan now?"
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",lambda *_:json.dumps(dict(intent=intent,topic="savings",continuation=True,kind=None,
        amount_text=None,category_text=None,category=None,clarification=None,proposal_reference="that vacation savings plan")))
    response=api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"How is my budget?"},
        {"role":"assistant","content":"Here is your budget."},{"role":"user","content":text}],"plan_review_ids":[key]})
    assert response.status_code==200,response.text
    data=response.json()
    assert ("already accepted" if state=="saved" else state) in data["reply"]
    assert "transaction" not in data["reply"].lower()
    assert data["plan"] is None and data["proposal"] is None and data["record_state"] is None
    assert data["plan_updates"][0]["status"]==state
    assert db_session.query(FinancialPlan).count()==int(state=="saved")


def test_new_chat_does_not_search_old_plan_reviews(reviews,api_client,monkeypatch):
    headers,_,issue=reviews;issue()
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",lambda *_:json.dumps(dict(intent="financial_plan",topic="savings",continuation=False,
        kind=None,amount_text=None,category_text=None,category=None,clarification=None)))
    data=api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Accept that vacation plan."}]}).json()
    assert "Financial Plan" in data["reply"] and "in this chat" in data["reply"] and data["plan"] is None


def test_unknown_budget_identifier_is_not_an_acceptance_capability(reviews,api_client):
    headers,_,issue=reviews;plan=issue()
    result=api_client.post("/planning/budget-plans",headers=headers,json={"profile":plan["profile"],"choices":plan["budgetChoices"],
        "budget_fingerprint":plan["budgetFingerprint"],"request_key":str(uuid4())})
    assert result.status_code==404


@pytest.mark.parametrize("kind",["savings","debt","guided","spending"])
@pytest.mark.parametrize("race_reject",[False,True])
def test_concurrent_acceptance_and_rejection_are_serialized(api_client,tmp_path,kind,race_reject):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.main import app
    from app.database import Base,get_db
    engine=create_engine("sqlite:///"+str(tmp_path/"review-race.sqlite"),connect_args={"check_same_thread":False,"timeout":20})
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,autoflush=False)
    def isolated():
        with factory() as db:
            yield db
    previous=app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db]=isolated
    try:
        register_user(api_client)
        headers=auth_headers(login_user(api_client).json()["access_token"])
        today=datetime.now(timezone(timedelta(hours=4))).date()
        api_client.put(f"/budget/setup?year={today.year}&month={today.month}",headers=headers,json={
            "income":10000,"categories":[{"name":"Rent","amount":4000},{"name":"Food","amount":1000}]})
        if kind=="debt":
            from app.routers.planning import debt_goal_basis
            from app.services.debt_planning import snapshot,scenario,draft
            loan=api_client.post("/debts",headers=headers,json={"name":"Car Loan","balance":30000,"annual_rate":5,"remaining_months":60}).json()
            with factory() as db:
                budget=debt_goal_basis(db,1,today);data=snapshot(db,1,budget,today,[loan["id"]])
                initial=draft(data,scenario(data,"2028-09-30",None,today),budget,today,1,{})
            response=api_client.post("/planning/debt-plans/preview",headers=headers,json={"token":initial["debtConfirmation"]})
        elif kind in ("guided","spending"):
            from app.schemas.planning import CATEGORIES
            response=api_client.post("/planning/preview",headers=headers,json={"income":10000,"other_income":0,"household_size":1,
                "goal":"Vacation" if kind=="guided" else "Monthly budget","goal_kind":"savings" if kind=="guided" else "spending","target_amount":3000 if kind=="guided" else 6000,"current_amount":0,"deadline":"2027-07-31",
                "expenses":{key:4000 if key=="Rent" else 1000 if key=="Food" else 0 for key in CATEGORIES}})
        else:
            from app.services.budget_goals import fingerprint
            from app.routers.budget import summary
            with factory() as db:
                budget=summary(db,1,today.year,today.month,include_debt=True)
            response=api_client.post("/planning/budget-plans/preview",headers=headers,json={"profile":{
                "goal":"Vacation","goal_kind":"savings","target_amount":3000,"monthly_contribution":300},
                "budget_fingerprint":fingerprint(budget),"request_key":str(uuid4())})
        assert response.status_code==200,response.text
        key=response.json()["reviewId"]
        def request(action):
            return api_client.post(f"/planning/reviews/{key}/{action}",headers=headers,json={})
        actions=["accept","reject" if race_reject else "accept","accept"]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results=list(pool.map(request,actions))
        assert all(result.status_code in (200,409) for result in results),[result.text for result in results]
        with factory() as db:
            count=db.query(FinancialPlan).count();row=db.get(PlanReview,key)
            assert count in (0,1)
            assert count==int(row.status=="saved")
            assert row.status in ("saved","rejected")
            if not race_reject:
                assert count==1 and any(result.status_code==200 for result in results)
            if row.status=="rejected":
                assert request("accept").status_code==409
            assert db.query(Transaction).count()==db.query(ManualSavings).count()==db.query(DebtPayment).count()==0
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db,None)
        else:
            app.dependency_overrides[get_db]=previous
        engine.dispose()


def test_consumed_capability_cannot_recreate_a_deleted_plan(reviews,api_client,db_session):
    headers,_,issue=reviews;plan=issue();key=plan["reviewId"]
    assert api_client.post(f"/planning/reviews/{key}/accept",headers=headers,json={}).status_code==200
    assert api_client.delete(f"/planning/plans/{key}",headers=headers).status_code==204
    assert api_client.post(f"/planning/reviews/{key}/accept",headers=headers,json={}).status_code==409
    request={"profile":plan["profile"],"choices":plan["budgetChoices"],"budget_fingerprint":plan["budgetFingerprint"],"request_key":key}
    assert api_client.post("/planning/budget-plans",headers=headers,json=request).status_code==409
    assert db_session.query(FinancialPlan).count()==0


def test_failed_stale_acceptance_releases_claim_so_rejection_can_finish(reviews,api_client,db_session):
    headers,today,issue=reviews;plan=issue();key=plan["reviewId"]
    assert api_client.put(f"/budget/income?year={today.year}&month={today.month}",headers=headers,json={"amount":11000}).status_code==200
    result=api_client.post(f"/planning/reviews/{key}/accept",headers=headers,json={})
    assert result.status_code==409
    db_session.expire_all()
    assert db_session.get(PlanReview,key).status=="pending"
    assert api_client.post(f"/planning/reviews/{key}/reject",headers=headers).json()["status"]=="rejected"
    assert db_session.query(FinancialPlan).count()==0


@pytest.mark.parametrize("kind",["savings","debt"])
def test_superseded_review_cannot_restore_old_plan_or_create_a_second_one(reviews,api_client,db_session,kind):
    headers,_,issue=reviews;initial=issue(kind);original_key=initial["reviewId"]
    saved=api_client.post(f"/planning/reviews/{original_key}/accept",headers=headers,json={}).json()
    if kind=="debt":
        response=api_client.post("/planning/debt-plans/preview",headers=headers,json={"token":saved["debtConfirmation"],"plan_id":saved["id"],"monthly_payment":1500})
        assert response.status_code==200,response.text
        next_plan=response.json()
        request={"token":next_plan["debtConfirmation"]}
        endpoint="/planning/debt-plans"
    else:
        response=api_client.post("/planning/budget-plans/preview",headers=headers,json={"profile":dict(saved["profile"],monthly_contribution="250"),
            "choices":saved["budgetChoices"],"budget_fingerprint":saved["budgetFingerprint"],"request_key":str(uuid4())})
        assert response.status_code==200,response.text
        next_plan=response.json()
        request={"profile":next_plan["profile"],"choices":next_plan["budgetChoices"],"budget_fingerprint":next_plan["budgetFingerprint"],"request_key":next_plan["confirmationKey"]}
        endpoint="/planning/budget-plans"
    for _ in range(2):
        response=api_client.put(endpoint+"/"+saved["id"],headers=headers,json=request)
        assert response.status_code==200,response.text
    assert api_client.post(f"/planning/reviews/{original_key}/accept",headers=headers,json={}).status_code==409
    assert api_client.post(endpoint,headers=headers,json=request).status_code==409
    assert db_session.query(FinancialPlan).count()==1


@pytest.mark.parametrize("kind",["savings","debt"])
def test_original_endpoint_consumes_review_without_needing_a_status_read(reviews,api_client,db_session,kind):
    headers,_,issue=reviews;plan=issue(kind);key=plan["reviewId"]
    if kind=="debt":
        endpoint="/planning/debt-plans";request={"token":plan["debtConfirmation"]}
    else:
        endpoint="/planning/budget-plans";request={"profile":plan["profile"],"choices":plan["budgetChoices"],
            "budget_fingerprint":plan["budgetFingerprint"],"request_key":key}
    response=api_client.post(endpoint,headers=headers,json=request)
    assert response.status_code==201,response.text
    db_session.expire_all()
    assert db_session.get(PlanReview,key).status=="saved"
    assert api_client.delete("/planning/plans/"+response.json()["id"],headers=headers).status_code==204
    assert api_client.post(endpoint,headers=headers,json=request).status_code==409
    assert db_session.query(FinancialPlan).count()==0


def test_guided_edit_consumes_review_and_cannot_create_a_second_plan(reviews,api_client,db_session):
    headers,_,issue=reviews
    initial=issue("guided")
    saved=api_client.post(f"/planning/reviews/{initial['reviewId']}/accept",headers=headers,json={}).json()
    next_plan=issue("guided")
    for _ in range(2):
        response=api_client.post(f"/planning/reviews/{next_plan['reviewId']}/accept",headers=headers,json={"plan_id":saved["id"]})
        assert response.status_code==200,response.text
        assert response.json()["id"]==saved["id"]
    response=api_client.post(f"/planning/reviews/{next_plan['reviewId']}/accept",headers=headers,json={})
    assert response.status_code==200 and response.json()["id"]==saved["id"]
    assert db_session.query(FinancialPlan).count()==1


def test_reference_with_inconsistent_model_quote_does_not_recreate_rejected_plan(reviews,api_client,db_session,monkeypatch):
    headers,_,issue=reviews;plan=issue();key=plan["reviewId"]
    api_client.post(f"/planning/reviews/{key}/reject",headers=headers)
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",lambda *_:json.dumps(dict(intent="plan",topic="savings",continuation=True,
        kind=None,amount_text=None,category_text=None,category=None,clarification=None,proposal_reference=None)))
    response=api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Can you accept that vacation savings plan now?"}],"plan_review_ids":[key]})
    assert response.status_code==200
    assert "rejected" in response.json()["reply"] and response.json()["plan"] is None
    assert db_session.query(PlanReview).count()==1


def test_fresh_plan_creation_is_distinct_from_accepting_rejected_plan(reviews,api_client,db_session,monkeypatch):
    headers,_,issue=reviews;plan=issue();key=plan["reviewId"]
    api_client.post(f"/planning/reviews/{key}/reject",headers=headers)
    text="Create a new Vacation savings plan for 3000 AED with 300 AED monthly."
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn",lambda *_:json.dumps(dict(intent="plan",topic="savings",continuation=False,
        kind=None,amount_text=None,category_text=None,category=None,clarification=None,proposal_reference=text,savings_operation="goal")))
    monkeypatch.setattr("app.routers.chat.extract_goal_facts",lambda *_:json.dumps({"goal":"Vacation","goal_kind":"savings","target_amount":3000,"monthly_contribution":300}))
    monkeypatch.setattr("app.routers.chat.generate_chat_reply",lambda *_:json.dumps({"reply":"Review your new plan.","action":None,"planning":None}))
    response=api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":text}],"plan_review_ids":[key],"require_budget":True})
    assert response.status_code==200,response.text
    draft=response.json()["plan"]
    assert draft and draft["reviewId"]!=key and draft["reviewStatus"]=="pending"
    assert db_session.query(FinancialPlan).count()==0
    assert db_session.get(PlanReview,key).status=="rejected"


def test_browser_numeric_serialization_preserves_reviewed_financial_facts(reviews,api_client):
    headers,_,issue=reviews;plan=issue()
    profile=dict(plan["profile"],income=10000,monthly_contribution=300,target_amount=3000,current_amount=0)
    request={"profile":profile,"choices":plan["budgetChoices"],"budget_fingerprint":plan["budgetFingerprint"],"request_key":plan["confirmationKey"]}
    result=api_client.post("/planning/budget-plans",headers=headers,json=request)
    assert result.status_code==201,result.text
    request["profile"]["income"]=10000.0
    assert api_client.post("/planning/budget-plans",headers=headers,json=request).status_code==201
    request["profile"]["monthly_contribution"]=301
    assert api_client.post("/planning/budget-plans",headers=headers,json=request).status_code==409
