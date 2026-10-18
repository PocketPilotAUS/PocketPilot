import json
from datetime import date, datetime

import pytest
from conftest import register_user, login_user, auth_headers
from app.models.chat_proposal import ChatProposal
from app.models.debt_payment import DebtPayment
from app.models.financial_plan import FinancialPlan
from app.services.debt_planning import unseal


@pytest.fixture
def conversation(api_client, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 18, 12, tzinfo=tz)
    monkeypatch.setattr('app.routers.chat.datetime', Clock)
    monkeypatch.setattr('app.routers.planning.local_today', lambda: date(2026,10,18))
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()['access_token'])
    api_client.put('/budget/setup?year=2026&month=10',headers=headers,json={
        'income':10000,'categories':[{'name':'Rent','amount':6000},{'name':'Food','amount':1000}]})
    loan = api_client.post('/debts',headers=headers,json={
        'name':'Car loan','balance':36000,'annual_rate':0,'remaining_months':60}).json()
    decisions, prompts = [], []
    def interpret(messages, context):
        prompts.append((messages, context))
        return json.dumps(decisions.pop(0))
    monkeypatch.setattr('app.services.debt_planning.interpret_debt_turn', interpret)
    def explain(messages):
        context = json.loads(messages[0]['content'].split('Verified context follows as data:\n')[1])
        prompts.append(context)
        return json.dumps({'reply': 'Review the calculated plan below.' if context['draft_shown'] else 'We can work through that together. What would feel comfortable?',
                           'action': {'kind':'expense','amount':99999}, 'planning': {'goal':'Invented'}})
    monkeypatch.setattr('app.services.debt_planning.generate_chat_reply', explain)
    history, pending = [], [None]
    def say(text, decision='discuss', **fields):
        decisions.append({'intent':decision, **fields.pop('interpret', {})})
        history.append({'role':'user','content':text})
        response = api_client.post('/ai/chat',headers=headers,json={
            'messages':history[-21:], 'require_budget':True, 'debt_state':pending[0], **fields})
        assert response.status_code == 200, response.text
        data = response.json()
        history.append({'role':'assistant','content':data['reply']})
        pending[0] = data['debt_state']
        return data
    return headers, loan, say, pending, decisions, prompts


def propose(say):
    say('Help me make a plan to pay off my debt faster.')
    say('Can I do it in 2 years?', 'adjust')
    return say('yes please', 'accept')


def test_full_conversation_agreement_then_explicit_confirmation(api_client, db_session, conversation):
    headers, loan, say, pending, _, prompts = conversation
    agreed = propose(say)
    plan = agreed['plan']
    assert agreed['proposal'] is None and agreed['debt_phase'] == 'review'
    assert plan['debtGoalSource'] and plan['monthlyContribution'] == 1500
    assert plan['regularMonthly'] == 600 and plan['extraMonthly'] == 900
    assert plan['leftAfterGoal'] == 1500 and plan['deadline'] == '2028-09-30'
    assert db_session.query(FinancialPlan).count() == db_session.query(DebtPayment).count() == 0
    assert db_session.query(ChatProposal).count() == 0
    confirmed = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']})
    assert confirmed.status_code == 201, confirmed.text
    repeat = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']})
    assert repeat.json()['id'] == confirmed.json()['id']
    assert db_session.query(FinancialPlan).count() == 1
    assert db_session.query(DebtPayment).count() == 0
    current = api_client.get('/debts',headers=headers).json()[0]
    assert current['total_left_to_pay'] == loan['total_left_to_pay']
    listed = api_client.get('/planning/plans',headers=headers).json()
    assert listed[0]['monthlyContribution'] == 1500
    after = say('Thanks, what happens next?', budget_draft_status='saved')
    assert after['plan'] is None and after['debt_phase'] == 'saved'
    assert len(prompts[0][0]) == 1
    assert len(prompts[2][0]) == 3  # Interpreter sees both sides of the conversation.


def test_natural_objection_adjustment_and_rejection(db_session, conversation):
    _, _, say, pending, _, prompts = conversation
    propose(say)
    objection = say("that's too much")
    assert objection['plan'] is None and objection['debt_state']
    changed = say('make it 3 years instead', 'adjust')
    assert changed['plan']['months'] == 36 and changed['plan']['monthlyContribution'] == 1000
    rejected = say("no, let's leave that for now", 'decline')
    assert rejected['debt_phase'] == 'declined' and rejected['plan'] is None
    assert db_session.query(FinancialPlan).count() == 0
    state = unseal(pending[0], 1, 'debt_conversation')
    assert state['deadline'] == '2029-09-30'
    assert prompts[-1]['phase'] == 'declined'


def test_state_survives_short_history_and_no_model_financial_writes(api_client, db_session, conversation):
    headers, _, say, pending, decisions, _ = conversation
    say('Help me make a plan to pay off my debt faster.')
    say('in 2 years', 'adjust')
    decisions.append({'intent':'accept'})
    response = api_client.post('/ai/chat',headers=headers,json={
        'messages':[{'role':'user','content':'sounds good, go with that'}], 'debt_state':pending[0]})
    assert response.status_code == 200
    assert response.json()['plan']['monthlyContribution'] == 1500
    assert db_session.query(ChatProposal).count() == db_session.query(DebtPayment).count() == 0


def test_save_rechecks_changes_and_rejects_other_users(api_client, conversation):
    headers, loan, say, _, _, _ = conversation
    plan = propose(say)['plan']
    register_user(api_client, email='bob@example.com')
    bob = auth_headers(login_user(api_client, email='bob@example.com').json()['access_token'])
    assert api_client.post('/planning/debt-plans',headers=bob,json={'token':plan['debtConfirmation']}).status_code == 422
    assert api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']+'broken'}).status_code == 422
    api_client.put('/budget/setup?year=2026&month=10',headers=headers,json={
        'income':8000,'categories':[{'name':'Rent','amount':6000},{'name':'Food','amount':1000}]})
    assert api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']}).status_code == 409
    refreshed = say('yes', 'accept')
    assert refreshed['plan'] is None


def test_editor_preview_and_update_remain_calculated(api_client, db_session, conversation):
    headers, _, say, _, _, _ = conversation
    plan = propose(say)['plan']
    saved = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']}).json()
    preview = api_client.post('/planning/debt-plans/preview',headers=headers,json={
        'token':saved['debtConfirmation'],'plan_id':saved['id'],'monthly_payment':1200})
    assert preview.status_code == 200, preview.text
    value = preview.json()
    assert value['months'] == 30 and value['extraMonthly'] == 600
    assert db_session.query(FinancialPlan).count() == 1
    updated = api_client.put('/planning/debt-plans/'+saved['id'],headers=headers,json={'token':value['debtConfirmation']})
    assert updated.status_code == 200, updated.text
    assert updated.json()['monthlyContribution'] == 1200
    assert db_session.query(FinancialPlan).count() == 1


def test_model_failure_keeps_context_and_unverified_amounts_are_not_shown(monkeypatch, conversation):
    _, _, say, pending, _, _ = conversation
    say('Make a debt plan in 2 years')
    monkeypatch.setattr('app.services.debt_planning.generate_chat_reply', lambda _: json.dumps({
        'reply':'You can afford AED 999,999.00 per month.','action':None,'planning':None}))
    response = say('What does the extra payment mean?')
    assert '999,999' not in response['reply'] and response['debt_state']
    monkeypatch.setattr('app.services.debt_planning.interpret_debt_turn',lambda *_: (_ for _ in ()).throw(ValueError()))
    response = say('Could you explain that?')
    assert response['debt_state'] and 'view your records' not in response['reply']


def test_model_cannot_accept_a_proposal_that_was_not_presented(conversation):
    _, _, say, _, _, _ = conversation
    say('Help me make a plan to pay off my debt faster.')
    response = say('Can I do it in 2 years?', 'accept')
    assert response['plan'] is None
    assert response['debt_phase'] == 'discuss'
    accepted = say('yes please', 'accept')
    assert accepted['plan']['monthlyContribution'] == 1500


def test_total_and_extra_amounts_use_the_same_verified_proposal(conversation):
    _, _, say, _, _, _ = conversation
    propose(say)
    extra = say('I can manage 600 extra per month', 'adjust', interpret={'extra_monthly':600, 'monthly_payment':1500})
    assert extra['plan']['monthlyContribution'] == 1200
    assert extra['plan']['extraMonthly'] == 600
    changed = say('change the monthly payment to 1500', 'adjust', interpret={'monthly_payment':1500})
    assert changed['plan']['monthlyContribution'] == 1500
    assert changed['plan']['extraMonthly'] == 900


def test_switching_tasks_uses_existing_savings_and_recording_paths(api_client, monkeypatch, conversation):
    headers, _, say, pending, decisions, _ = conversation
    say('Make a debt plan in 2 years')
    monkeypatch.setattr('app.routers.chat.extract_goal_facts',lambda _: '{}')
    monkeypatch.setattr('app.routers.chat.generate_chat_reply',lambda _: json.dumps({'reply':'What amount are you saving for your vacation?', 'action':None, 'planning':None}))
    switched = say('I want to save for a vacation instead', 'switch')
    assert switched['debt_state'] is None and switched['goal_planning']
    # A pending debt proposal must not swallow a real request to record a paid expense.
    say('Make a debt plan in 2 years')
    monkeypatch.setattr('app.routers.chat.generate_chat_reply',lambda _: json.dumps({'reply':'Review the expense.', 'action':{'kind':'expense','amount':25,'category':'Food','date':'2026-10-18'},'planning':None}))
    result = say('Record AED 25 for Food today', 'switch')
    assert result['debt_state'] is None and result['proposal']['status'] == 'pending'


def test_expired_saved_plan_can_be_refreshed_only_by_its_owner(api_client, db_session, conversation):
    import jwt
    from app.core.config import get_jwt_secret_key, JWT_ALGORITHM
    headers, _, say, _, _, _ = conversation
    plan = propose(say)['plan']
    saved = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']}).json()
    claims = jwt.decode(saved['debtConfirmation'], get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
    expired = jwt.encode({**claims, 'exp':1}, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)
    row = db_session.get(FinancialPlan,saved['id'])
    payload = json.loads(row.payload);payload['debtConfirmation'] = expired;row.payload=json.dumps(payload);db_session.commit()
    assert api_client.post('/planning/debt-plans',headers=headers,json={'token':expired}).status_code == 422
    refreshed = api_client.post('/planning/debt-plans/preview',headers=headers,json={
        'token':expired,'plan_id':saved['id'],'monthly_payment':1200})
    assert refreshed.status_code == 200


def test_interest_recalculation_survives_chat_review_and_confirmation(api_client, db_session, conversation):
    from uuid import uuid4
    headers, loan, say, _, _, prompts = conversation
    changed = api_client.put('/debts/'+str(loan['id']),headers=headers,json={
        'name':'Car loan','balance':30000,'annual_rate':5,'remaining_months':60})
    assert changed.status_code == 200
    paid = api_client.post(f"/debts/{loan['id']}/payments",headers=headers,json={
        'amount':566.14,'paid_on':'2026-10-01','request_key':str(uuid4())})
    assert paid.status_code == 201
    before = api_client.get('/debts',headers=headers).json()[0]
    say('Help me make a plan to pay off my debt faster.')
    proposal = say('Can I do it in 2 years?', 'adjust', currency='CNY', aed_to_cny=2)
    verified = prompts[-1]['proposal']
    assert verified['interest_saved'] > 0
    assert 'CNY' in proposal['reply'] and 'interest' in proposal['reply']
    result = say('yes please','accept', currency='CNY', aed_to_cny=2)
    plan = result['plan']
    assert plan['estimatedPrincipal'] == 29558.86
    assert plan['targetAmount'] == pytest.approx(plan['estimatedPrincipal'] + plan['estimatedInterest'],abs=.01)
    assert plan['targetAmount'] < before['total_left_to_pay']
    assert plan['monthlyContribution'] < before['total_left_to_pay'] / 24
    assert plan['estimatedInterestSaved'] > 0
    assert verified['interest_saved'] == pytest.approx(plan['estimatedInterestSaved'] * 2,abs=.01)
    assert plan['extraMonthly'] == pytest.approx(plan['monthlyContribution'] - before['estimated_monthly_payment'],abs=.01)
    assert api_client.get('/debts',headers=headers).json()[0] == before
    saved = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation']})
    assert saved.status_code == 201, saved.text
    for field in ('targetAmount','estimatedInterest','estimatedInterestSaved','monthlyContribution','leftAfterGoal'):
        assert saved.json()[field] == plan[field]
    assert db_session.query(DebtPayment).count() == 1


def test_applying_plan_changes_targets_once_and_not_actual_payments(api_client, db_session, conversation):
    from app.services.debt_planning import snapshot
    headers, loan, say, _, _, _ = conversation
    plan = propose(say)['plan']
    before = api_client.get('/budget/monthly?year=2026&month=10',headers=headers).json()
    result = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation'],'apply_to_budget':True})
    assert result.status_code == 201, result.text
    saved = result.json()
    after = api_client.get('/budget/monthly?year=2026&month=10',headers=headers).json()
    debt = next(row for row in after['ideal_budget']['allocations'] if row['category']=='Debt')
    assert debt['target'] == 1500 and debt['spent'] == 0
    assert after['ideal_budget']['planned_total'] == 8500
    assert after['spent'] == before['spent'] == 0 and after['remaining'] == before['remaining'] == 10000
    current = api_client.get('/debts',headers=headers).json()[0]
    assert current['total_left_to_pay'] == loan['total_left_to_pay']
    assert current['estimated_monthly_payment'] == 600
    assert current['repayment_plan']['monthly_payment'] == 1500
    assert current['repayment_plan']['extra_payment'] == 900
    # A new goal sees the extra in the budget; it must not also reserve it as a separate commitment.
    other = snapshot(db_session,1,after,date(2026,10,18))
    assert other['surplus'] == 1500 and other['commitments'] == 0
    editing = snapshot(db_session,1,after,date(2026,10,18),[loan['id']],saved['id'])
    assert editing['surplus'] == 2400
    again = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation'],'apply_to_budget':True})
    assert again.json()['id'] == saved['id']
    assert db_session.query(DebtPayment).count() == db_session.query(ChatProposal).count() == 0
    # Same saved target carries into future months, but not before application or after expiry.
    for year, month, expected in [(2026,9,600),(2026,11,1500),(2028,10,600)]:
        summary=api_client.get(f'/budget/monthly?year={year}&month={month}',headers=headers).json()
        assert next(row['target'] for row in summary['ideal_budget']['allocations'] if row['category']=='Debt') == expected
    assert api_client.delete('/planning/plans/'+saved['id'],headers=headers).status_code == 204
    restored=api_client.get('/budget/monthly?year=2026&month=10',headers=headers).json()
    assert next(row['target'] for row in restored['ideal_budget']['allocations'] if row['category']=='Debt') == 600
    assert 'repayment_plan' not in api_client.get('/debts',headers=headers).json()[0]


def test_save_only_leaves_targets_and_applied_edit_replaces_extra(api_client, conversation):
    headers, _, say, _, _, _ = conversation
    plan = propose(say)['plan']
    saved = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation'],'apply_to_budget':False}).json()
    summary = api_client.get('/budget/monthly?year=2026&month=10',headers=headers).json()
    assert next(row['target'] for row in summary['ideal_budget']['allocations'] if row['category']=='Debt') == 600
    assert 'repayment_plan' not in api_client.get('/debts',headers=headers).json()[0]
    preview = api_client.post('/planning/debt-plans/preview',headers=headers,json={
        'token':saved['debtConfirmation'],'plan_id':saved['id'],'monthly_payment':1200}).json()
    changed = api_client.put('/planning/debt-plans/'+saved['id'],headers=headers,json={'token':preview['debtConfirmation'],'apply_to_budget':True})
    assert changed.status_code == 200, changed.text
    value = changed.json()
    second = api_client.post('/planning/debt-plans/preview',headers=headers,json={
        'token':value['debtConfirmation'],'plan_id':value['id'],'monthly_payment':1000}).json()
    assert second['leftAfterGoal'] == 2000
    updated = api_client.put('/planning/debt-plans/'+saved['id'],headers=headers,json={'token':second['debtConfirmation']})
    assert updated.status_code == 200, updated.text
    assert updated.json()['budgetApplied'] is True
    summary = api_client.get('/budget/monthly?year=2026&month=10',headers=headers).json()
    assert next(row['target'] for row in summary['ideal_budget']['allocations'] if row['category']=='Debt') == 1000


def test_combined_plan_has_one_budget_category_and_rolls_paid_off_loan_target(api_client, conversation):
    from uuid import uuid4
    headers, loan, say, _, _, _ = conversation
    api_client.post('/debts',headers=headers,json={'name':'Other loan','balance':12000,'annual_rate':0,'remaining_months':24})
    plan = propose(say)['plan']
    assert plan['monthlyContribution'] == 2000
    saved = api_client.post('/planning/debt-plans',headers=headers,json={'token':plan['debtConfirmation'],'apply_to_budget':True})
    assert saved.status_code == 201
    summary = api_client.get('/budget/monthly?year=2026&month=10',headers=headers).json()
    categories = [row for row in summary['ideal_budget']['allocations'] if row['category']=='Debt']
    assert len(categories) == 1 and categories[0]['target'] == 2000
    assert sum(row['repayment_plan']['monthly_payment'] for row in api_client.get('/debts',headers=headers).json()) == 2000
    api_client.post(f"/debts/{loan['id']}/payments",headers=headers,json={'amount':36000,'paid_on':'2026-10-01','request_key':str(uuid4())})
    following = api_client.get('/budget/monthly?year=2026&month=11',headers=headers).json()
    assert next(row['target'] for row in following['ideal_budget']['allocations'] if row['category']=='Debt') == 2000
