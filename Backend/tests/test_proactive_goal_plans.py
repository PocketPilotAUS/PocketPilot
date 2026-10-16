import json
from datetime import date, datetime, timedelta, timezone
from conftest import register_user, login_user, auth_headers
from app.models.financial_plan import FinancialPlan
from app.services.goal_dates import deadline_from_months


def auth(client, email='alice@example.com'):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()['access_token'])


def today():
    return datetime.now(timezone(timedelta(hours=4))).date()


def setup(client, headers):
    now = today()
    response = client.put(f'/budget/setup?year={now.year}&month={now.month}', headers=headers,
        json={'income': 10000, 'categories': [{'name': 'Rent', 'amount': 4000}, {'name': 'Food', 'amount': 1600}]})
    assert response.status_code == 200


def model(monkeypatch, planning, reply='Here is what that looks like.'):
    calls = []
    def answer(messages):
        calls.append(messages)
        return json.dumps({'reply': reply, 'action': None, 'planning': planning})
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', answer)
    return calls


IPHONE = {'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000, 'deadline_in_months': 6}
ASK = [{'role': 'user', 'content': 'I want to save 5000 AED for an iPhone in six months.'}]


def test_deadline_from_months_gives_exact_contribution_count():
    assert deadline_from_months(date(2026, 10, 16), 6) == date(2027, 3, 31)
    assert deadline_from_months(date(2026, 10, 16), 1) == date(2026, 10, 31)
    assert deadline_from_months(date(2027, 1, 31), 1) == date(2027, 1, 31)
    assert deadline_from_months(date(2026, 12, 1), 2) == date(2027, 1, 31)
    assert deadline_from_months(date(2027, 11, 5), 4) == date(2028, 2, 29)
    for invalid in (0, -1, 601, None, 2.5, '6', True):
        assert deadline_from_months(date(2026, 10, 16), invalid) is None


def test_goal_mode_offers_verified_unsaved_draft(api_client, monkeypatch, db_session):
    headers = auth(api_client); setup(api_client, headers)
    calls = model(monkeypatch, IPHONE)
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'goal_planning': True, 'require_budget': True}).json()
    plan = data['plan']
    assert plan['ready'] and plan['budgetGoalSource'] and 'id' not in plan
    assert plan['deadline'] == deadline_from_months(today(), 6).isoformat()
    assert plan['months'] == 6
    assert plan['monthlyContribution'] * 6 >= 5000
    assert 'deadline_in_months' not in data['planning_profile']
    assert 'no plan has been shown or saved' in calls[0][0]['content']
    assert db_session.query(FinancialPlan).count() == 0


def test_goal_detected_outside_goal_mode_offers_draft(api_client, monkeypatch, db_session):
    headers = auth(api_client); setup(api_client, headers)
    model(monkeypatch, IPHONE)
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK}).json()
    assert data['goal_planning'] is True and data['plan']['ready']
    assert float(data['planning_profile']['income']) == 10000
    assert db_session.query(FinancialPlan).count() == 0


def test_general_chat_without_goal_has_no_draft(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    model(monkeypatch, None, 'Your food spending is steady.')
    data = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'How is my food spending?'}]}).json()
    assert data['plan'] is None and data['reply'] == 'Your food spending is steady.'


def test_missing_timeframe_gets_follow_up_not_draft(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    model(monkeypatch, {'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000}, 'When would you like to have it?')
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'goal_planning': True, 'require_budget': True}).json()
    assert data['plan'] is None and data['reply'] == 'When would you like to have it?'


def test_same_draft_is_not_presented_twice(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    model(monkeypatch, IPHONE)
    first = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'goal_planning': True, 'require_budget': True}).json()
    model(monkeypatch, None, 'Take your time reviewing it.')
    again = api_client.post('/ai/chat', headers=headers, json={'messages': ASK + [{'role': 'assistant', 'content': 'Here.'}, {'role': 'user', 'content': 'Thanks'}],
        'goal_planning': True, 'require_budget': True, 'planning_profile': first['planning_profile'],
        'budget_draft_fingerprint': first['plan']['draftFingerprint'], 'budget_draft_status': 'draft'}).json()
    assert again['plan'] is None


def test_accepted_draft_is_saved_and_listed(api_client, monkeypatch, db_session):
    headers = auth(api_client); setup(api_client, headers)
    model(monkeypatch, IPHONE)
    plan = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'goal_planning': True, 'require_budget': True}).json()['plan']
    assert api_client.get('/planning/plans', headers=headers).json() == []
    body = {'profile': plan['profile'], 'choices': plan.get('budgetChoices') or {}, 'budget_fingerprint': plan['budgetFingerprint'], 'request_key': plan['confirmationKey']}
    saved = api_client.post('/planning/budget-plans', headers=headers, json=body)
    assert saved.status_code == 201
    listed = api_client.get('/planning/plans', headers=headers).json()
    assert [row['id'] for row in listed] == [saved.json()['id']]
    assert listed[0]['deadline'] == plan['deadline'] and listed[0]['monthlyContribution'] == plan['monthlyContribution']
    # Retrying the same Accept tap does not duplicate the plan.
    assert api_client.post('/planning/budget-plans', headers=headers, json=body).json()['id'] == saved.json()['id']
    assert db_session.query(FinancialPlan).count() == 1


def test_prompt_reports_saved_state_truthfully(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    calls = model(monkeypatch, None, 'Great.')
    api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'goal_planning': True, 'require_budget': True, 'budget_draft_status': 'declined'})
    assert 'rejected by the user, NOT saved' in calls[0][0]['content']
    assert 'never say a plan or goal was created, saved or set' in calls[0][0]['content']


def extractor(monkeypatch, facts):
    calls = []
    def extract(messages):
        calls.append(messages)
        if isinstance(facts, Exception):
            raise facts
        return json.dumps(facts)
    monkeypatch.setattr('app.routers.chat.extract_goal_facts', extract)
    return calls


def test_extracted_facts_build_card_before_reply(api_client, monkeypatch, db_session):
    headers = auth(api_client); setup(api_client, headers)
    extractor(monkeypatch, {'goal': 'Laptop', 'goal_kind': 'savings', 'target_amount': 3000, 'current_amount': None, 'deadline': None, 'deadline_in_months': 10})
    calls = model(monkeypatch, None, 'Here is a plan for your laptop.')
    messages = [{'role': 'user', 'content': 'I would like to buy a 3000 AED laptop within 10 months.'}]
    data = api_client.post('/ai/chat', headers=headers, json={'messages': messages, 'require_budget': True}).json()
    plan = data['plan']
    assert data['goal_planning'] is True and plan['ready'] and plan['months'] == 10
    assert plan['deadline'] == deadline_from_months(today(), 10).isoformat()
    assert data['planning_profile']['goal'] == 'Laptop' and data['reply'] == 'Here is a plan for your laptop.'
    context = json.loads(calls[0][0]['content'].split('Financial context follows as data:\n', 1)[1])
    assert context['plan_card']['monthlyContribution'] == plan['monthlyContribution']
    assert context['plan_card']['deadline'] == plan['deadline']
    assert 'new verified plan card is shown' in context['goal_plan_status']
    assert db_session.query(FinancialPlan).count() == 0


def test_extraction_failure_keeps_conversation_working(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    extractor(monkeypatch, ValueError('model unavailable'))
    model(monkeypatch, None, 'Tell me more about your goal.')
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    assert data['reply'] == 'Tell me more about your goal.'


def test_extracted_card_not_repeated_after_reject(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    facts = {'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000, 'current_amount': None, 'deadline': None, 'deadline_in_months': 6}
    extractor(monkeypatch, facts)
    model(monkeypatch, None)
    first = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    again = api_client.post('/ai/chat', headers=headers, json={'messages': ASK + [{'role': 'assistant', 'content': 'Here.'}, {'role': 'user', 'content': 'No thanks'}],
        'require_budget': True, 'goal_planning': True, 'planning_profile': first['planning_profile'],
        'budget_draft_fingerprint': first['plan']['draftFingerprint'], 'budget_draft_status': 'declined'}).json()
    assert again['plan'] is None
    # Changing the goal produces a new card to review.
    extractor(monkeypatch, dict(facts, deadline_in_months=8))
    changed = api_client.post('/ai/chat', headers=headers, json={'messages': ASK + [{'role': 'assistant', 'content': 'Here.'}, {'role': 'user', 'content': 'Make it eight months instead'}],
        'require_budget': True, 'goal_planning': True, 'planning_profile': first['planning_profile'],
        'budget_draft_fingerprint': first['plan']['draftFingerprint'], 'budget_draft_status': 'declined'}).json()
    assert changed['plan']['months'] == 8


def test_no_extraction_without_saved_budget(api_client, monkeypatch):
    headers = auth(api_client)
    calls = extractor(monkeypatch, {})
    data = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    assert data['budget_required'] is True and calls == []


def test_extraction_runs_without_reasoning(monkeypatch):
    import app.ai.client as client
    sent = []
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'done': True, 'message': {'content': '{"goal": null}'}}
    monkeypatch.setenv('OLLAMA_URL', 'http://localhost:11434')
    monkeypatch.setattr(client.httpx.Client, 'post', lambda self, url, json=None, **kw: sent.append(json) or Response())
    client.extract_goal_facts([{'role': 'user', 'content': 'hi'}])
    assert sent[-1]['think'] is False and set(sent[-1]['format']['properties']) >= {'goal', 'target_amount', 'deadline_in_months'}
    monkeypatch.delenv('OLLAMA_THINK', raising=False)
    client.generate_answer([{'role': 'user', 'content': 'hi'}])
    assert sent[-1]['think'] is True
    monkeypatch.setenv('OLLAMA_THINK', 'false')
    client.generate_answer([{'role': 'user', 'content': 'hi'}])
    assert sent[-1]['think'] is False


def facts_for(monkeypatch, text, extracted):
    from app.routers.chat import ChatRequest, ai_goal_facts
    extractor(monkeypatch, extracted)
    return ai_goal_facts(ChatRequest(messages=[{'role': 'user', 'content': text}]), date(2026, 10, 16))[0]


def test_extracted_figures_must_come_from_the_user(monkeypatch):
    base = {'goal': 'iPhone', 'goal_kind': 'savings', 'current_amount': None, 'deadline': None, 'deadline_in_months': None}
    # An amount the user never wrote is dropped; "5k" counts as 5000.
    assert 'target_amount' not in facts_for(monkeypatch, 'Save 5000 for an iPhone', dict(base, target_amount=5001))
    assert facts_for(monkeypatch, 'Save 5k for an iPhone', dict(base, target_amount=5000))['target_amount'] == '5000'
    assert facts_for(monkeypatch, 'Save 5,000 for an iPhone', dict(base, target_amount=5000))['target_amount'] == '5000'
    # The user's timeframe wins over a date the model filled in itself.
    assert facts_for(monkeypatch, 'Save 5000 in six months', dict(base, target_amount=5000, deadline='2024-09-30', deadline_in_months=6))['deadline'] == '2027-03-31'
    # Dates come from the user's words; a month without a year is its next occurrence.
    assert facts_for(monkeypatch, 'Save 5000 by 2027-02-28', dict(base, target_amount=5000, deadline='2027-02-28'))['deadline'] == '2027-02-28'
    assert facts_for(monkeypatch, 'Save 5000 by February', dict(base, target_amount=5000, deadline='2031-02-28'))['deadline'] == '2027-02-28'
    assert 'deadline' not in facts_for(monkeypatch, 'Save 5000 soon', dict(base, target_amount=5000, deadline='2027-02-28'))


def test_same_goal_keeps_reviewed_name(api_client, monkeypatch):
    headers = auth(api_client); setup(api_client, headers)
    facts = {'goal': 'iPhone', 'goal_kind': 'savings', 'target_amount': 5000, 'current_amount': None, 'deadline': None, 'deadline_in_months': 6}
    extractor(monkeypatch, facts)
    model(monkeypatch, None)
    first = api_client.post('/ai/chat', headers=headers, json={'messages': ASK, 'require_budget': True}).json()
    extractor(monkeypatch, dict(facts, goal='new iPhone'))
    again = api_client.post('/ai/chat', headers=headers, json={'messages': ASK + [{'role': 'assistant', 'content': 'Here.'}, {'role': 'user', 'content': 'Is it saved?'}],
        'require_budget': True, 'goal_planning': True, 'planning_profile': first['planning_profile'],
        'budget_draft_fingerprint': first['plan']['draftFingerprint'], 'budget_draft_status': 'saved'}).json()
    assert again['plan'] is None and again['planning_profile']['goal'] == 'iPhone'
