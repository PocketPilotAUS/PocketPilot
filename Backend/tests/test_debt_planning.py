import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from conftest import register_user, login_user, auth_headers
from app.routers.chat import Message
from app.services.chat_context import intent
from app.models.transaction import Transaction
from app.models.financial_plan import FinancialPlan
from app.models.chat_proposal import ChatProposal


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 18, 12, tzinfo=tz)


def setup(client, monkeypatch):
    monkeypatch.setattr('app.routers.chat.datetime', Clock)
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: pytest.fail('Debt calculation must not rely on model output'))
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', lambda _: pytest.fail('Debt flow must not extract a savings goal'))
    monkeypatch.setattr('app.services.debt_planning.interpret_debt_turn', lambda *_: json.dumps({'intent':'discuss'}))
    monkeypatch.setattr('app.services.debt_planning.generate_chat_reply', lambda *_: (_ for _ in ()).throw(ValueError('Exercise verified fallback')))
    register_user(client)
    headers = auth_headers(login_user(client).json()['access_token'])
    assert client.put('/budget/setup?year=2026&month=10', headers=headers, json={
        'income':10000, 'categories':[{'name':'Rent','amount':6000},{'name':'Food','amount':1000}]}).status_code == 200
    assert client.post('/debts', headers=headers, json={
        'name':'Car loan','balance':36000,'annual_rate':0,'remaining_months':60}).status_code == 201
    return headers


@pytest.mark.parametrize('recorded', [None, 'current', 'past'])
def test_two_year_followup_uses_saved_budget_and_current_date(api_client, db_session, monkeypatch, recorded):
    headers = setup(api_client, monkeypatch)
    if recorded:
        db_session.add(Transaction(user_id=1, date=date(2026,10 if recorded == 'current' else 9,2), amount=9999, category='Food'))
    db_session.add(FinancialPlan(id=str(uuid4()),user_id=1,payload=json.dumps({
        'kind':'savings','title':'Laptop','monthlyContribution':500,'deadline':'2028-01-01'})))
    db_session.commit()
    first = {'role':'user','content':'Help me make a plan to pay off my debt faster.'}
    opening = api_client.post('/ai/chat', headers=headers, json={'messages':[first]}).json()
    messages = [first, {'role':'assistant','content':opening['reply']},
                {'role':'user','content':'i want to do it in 2 years is that feasible for me based on budget spending everymonth and income'}]
    result = api_client.post('/ai/chat',headers=headers,json={'messages':messages,'require_budget':True}).json()
    reply = result['reply']
    assert '18 October 2026' in reply and '30 September 2028' in reply
    assert '24 monthly payments' in reply
    assert 'AED 1,900.00 left per month' in reply
    assert 'AED 1,500.00 per month' in reply and 'AED 900.00 extra' in reply
    assert 'leaving AED 1,000.00' in reply
    assert 'not money already saved' in reply
    assert result['proposal'] is None and result['plan'] is None
    assert db_session.query(ChatProposal).count() == 0
    assert db_session.query(FinancialPlan).count() == 1


@pytest.mark.parametrize('text,expected', [
    ('in 2 years', 'plan'), ('Is that affordable?', 'plan'),
    ('What are my debts?', 'read'), ('What was my income in September 2026?', 'read'),
    ('Record AED 25 for Food today', 'record')])
def test_followup_does_not_hijack_reads_or_recording(text, expected):
    messages = [Message(role='user',content='Help me make a plan to pay off my debt faster.'),
                Message(role='assistant',content='What timeframe?'),Message(role='user',content=text)]
    assert intent(messages) == expected


def test_date_and_budget_in_model_context_for_other_advice(api_client, monkeypatch):
    headers = setup(api_client, monkeypatch)
    captured = []
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', lambda _: '{}')
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda messages: captured.extend(messages) or json.dumps({'reply':'Advice','action':None,'planning':None}))
    api_client.post('/ai/chat', headers=headers, json={'messages':[{'role':'user','content':'Explain budgeting'}]})
    assert 'Today is 2026-10-18 (October 2026)' in captured[0]['content']
    assert 'An unfinished month is never a normal monthly baseline' in captured[0]['content']
    context=json.loads(captured[0]['content'].split('Financial context follows as data:\n')[1])
    assert context['planning']['saved_budget']['month'] == 10


def test_debt_currency_and_unaffordable_target(api_client, monkeypatch):
    headers = setup(api_client, monkeypatch)
    api_client.put('/budget/setup?year=2026&month=10',headers=headers,json={
        'income':10000,'categories':[{'name':'Rent','amount':9000}]})
    response = api_client.post('/ai/chat', headers=headers, json={
        'currency':'CNY','aed_to_cny':2,'messages':[{'role':'user','content':'Make a debt plan in 2 years'}]})
    reply = response.json()['reply']
    assert 'CNY 800.00 left per month' in reply
    assert 'CNY 3,000.00 per month' in reply
    assert 'another CNY 1,000.00 per month' in reply
    assert 'does not fit the saved budget' in reply
    assert response.json()['plan'] is None


def test_new_goal_and_read_request_do_not_inherit_old_debt_topic():
    from app.services.debt_planning import debt_request
    messages = [Message(role='user',content='Make a debt plan'),
                Message(role='assistant',content='What timeframe?'),
                Message(role='user',content='I want to save for a vacation')]
    assert not debt_request(messages)


def test_new_calendar_month_uses_live_clock_not_old_conversation(api_client, monkeypatch):
    headers = setup(api_client, monkeypatch)
    class NextClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2030, 1, 3, 12, tzinfo=tz)
    monkeypatch.setattr('app.routers.chat.datetime', NextClock)
    api_client.put('/budget/setup?year=2030&month=1',headers=headers,json={
        'income':10000,'categories':[{'name':'Rent','amount':8000}]})
    result = api_client.post('/ai/chat',headers=headers,json={'messages':[
        {'role':'user','content':'Help me make a plan to pay off my debt faster.'},
        {'role':'assistant','content':'It is October 2026. What timeframe?'},
        {'role':'user','content':'in 2 years'}]}).json()
    assert '03 January 2030' in result['reply']
    assert '31 December 2031' in result['reply']
    assert 'AED 1,400.00 left per month' in result['reply']
