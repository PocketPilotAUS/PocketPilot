import json
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from conftest import register_user, login_user, auth_headers
from app.services.budget_goals import draft_plan
from app.models.financial_plan import FinancialPlan
from app.models.transaction import Transaction


def auth(client, email='alice@example.com'):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()['access_token'])


def setup(client, headers):
    now=datetime.now(timezone(timedelta(hours=4))).date()
    response=client.put(f'/budget/setup?year={now.year}&month={now.month}', headers=headers,
        json={'income':10000, 'categories':[{'name':'Rent','amount':5000},{'name':'Food','amount':1220}]})
    assert response.status_code == 200
    return response.json()


PROFILE={'goal':'iPhone', 'goal_kind':'savings', 'target_amount':5000, 'monthly_contribution':670}


def test_chosen_monthly_amount_produces_reviewable_draft():
    budget={'income':10000, 'year':2026, 'month':10, 'ideal_budget':{'allocations':[{'category':'Rent','target':5000},{'category':'Food','target':1220}]}}
    draft=draft_plan(PROFILE,budget,date(2026,10,15))
    assert draft['monthlyContribution']==670 and draft['months']==8
    assert draft['savedAmount']==0 and draft['deadline']=='2027-05-31'
    assert draft['availableAfter']==3780
    assert draft['profile'].get('household_size') is None
    assert draft['budgetGoalSource'] and 'id' not in draft
    assert draft_plan({**PROFILE,'monthly_contribution':4000},budget,date(2026,10,15)) is None
    assert draft_plan({**PROFILE,'goal':None},budget,date(2026,10,15)) is None


def test_restored_chat_preserves_model_reply_and_shows_unsaved_draft(api_client,monkeypatch,db_session):
    headers=auth(api_client); setup(api_client,headers)
    calls=[]
    answer="Sure, let's take it at your pace. Would 670 AED each month work for you?"
    def reply(messages):
        calls.append(messages)
        return json.dumps({'reply':answer,'action':None,'planning':PROFILE})
    monkeypatch.setattr('app.routers.chat.generate_chat_reply',reply)
    response=api_client.post('/ai/chat',headers=headers,json={'require_budget':True,'goal_planning':True,'messages':[
        {'role':'user','content':'I want to buy an iPhone for 5000.'},
        {'role':'assistant','content':'How much per month?'},
        {'role':'user','content':'Lets go with 670 per month.'}]}).json()
    assert len(calls)==1 and response['reply']==answer
    # The model's own extraction yields a verified draft for review; nothing is saved.
    assert response['plan']['ready'] and response['plan']['budgetGoalSource'] and 'id' not in response['plan']
    assert 'Recover explicit goal facts from prior USER messages' not in calls[0][0]['content']
    assert db_session.query(FinancialPlan).count()==0 and db_session.query(Transaction).count()==0


def test_restored_chat_does_not_recover_goal_when_model_omits_it(api_client,monkeypatch):
    headers=auth(api_client); setup(api_client,headers)
    calls=[]
    def reply(messages):
        calls.append(messages)
        return json.dumps({'reply':'What would you like to do next?', 'action':None, 'planning':None})
    monkeypatch.setattr('app.routers.chat.generate_chat_reply',reply)
    result=api_client.post('/ai/chat',headers=headers,json={'require_budget':True,'goal_planning':True,'messages':[
        {'role':'user','content':'I want to buy a new iphone, i want to save 5k by january 1 2027'},
        {'role':'assistant','content':'Would 500 AED per month work for you?'},
        {'role':'user','content':'lets go with 670'}]}).json()
    assert len(calls)==1 and result['plan'] is None
    assert result['planning_profile']['goal'] is None
    assert result['reply']=='What would you like to do next?'


def test_explicit_currency_tags_and_real_progress():
    from decimal import Decimal
    from app.routers.chat import Message
    from app.services.goal_facts import recover
    facts=recover({}, [Message(role='user',content='I want to buy an iPhone for 5000 AED.'),
        Message(role='assistant',content='You have 7560 AED saved. How much per month?'),
        Message(role='user',content='Lets go with 1340 CNY per month.'),
        Message(role='assistant',content='Okay'),
        Message(role='user',content='I already saved 100 AED.')], 'CNY', Decimal(2))
    assert facts['target_amount']=='5000' and facts['monthly_contribution']=='670.00'
    assert facts['current_amount']=='100'


def body(draft):
    return {'profile':draft['profile'],'choices':draft['budgetChoices'],'budget_fingerprint':draft['budgetFingerprint'],'request_key':draft['confirmationKey']}


def test_confirmation_is_explicit_idempotent_and_owner_scoped(api_client,db_session):
    alice=auth(api_client); budget=setup(api_client,alice)
    now=datetime.now(timezone(timedelta(hours=4))).date()
    draft=draft_plan(PROFILE,budget,now)
    first=api_client.post('/planning/budget-plans',headers=alice,json=body(draft))
    assert first.status_code==201
    repeated=api_client.post('/planning/budget-plans',headers=alice,json=body(draft))
    assert repeated.status_code==201 and repeated.json()['id']==first.json()['id']
    assert db_session.query(FinancialPlan).count()==1
    assert db_session.query(Transaction).count()==0
    assert len(api_client.get('/planning/plans',headers=alice).json())==1
    bob=auth(api_client,'bob@example.com')
    assert api_client.get('/planning/plans',headers=bob).json()==[]
    assert api_client.post('/planning/budget-plans',headers=bob,json=body(draft)).status_code==409
    assert api_client.put('/planning/budget-plans/'+first.json()['id'],headers=bob,json=body(draft)).status_code==404
    assert api_client.post('/planning/budget-plans',json=body(draft)).status_code==401


def test_stale_budget_rejected_and_edit_preview_does_not_save(api_client,db_session):
    headers=auth(api_client); budget=setup(api_client,headers)
    now=datetime.now(timezone(timedelta(hours=4))).date()
    draft=draft_plan(PROFILE,budget,now)
    payload=body(draft)
    now=datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f'/budget/income?year={now.year}&month={now.month}',headers=headers,json={'amount':9000})
    assert api_client.post('/planning/budget-plans',headers=headers,json=payload).status_code==409
    preview=api_client.post('/planning/budget-plans/preview',headers=headers,json={**payload,'profile':{**draft['profile'],'monthly_contribution':500}})
    assert preview.status_code==200 and preview.json()['monthlyContribution']==500
    assert db_session.query(FinancialPlan).count()==0
    saved=api_client.post('/planning/budget-plans',headers=headers,json=body(preview.json())).json()
    next_draft=draft_plan({**PROFILE,'monthly_contribution':700}, setup(api_client,headers),now)
    updated=api_client.put('/planning/budget-plans/'+saved['id'],headers=headers,json=body(next_draft))
    assert updated.status_code==200 and updated.json()['id']==saved['id']
    assert updated.json()['monthlyContribution']==700 and db_session.query(FinancialPlan).count()==1
