import json
import sqlite3
from uuid import uuid4
from conftest import register_user, login_user, auth_headers
from test_proactive_goal_plans import setup, model, ASK, IPHONE
from app.models.savings import ManualSavings


def auth(client, email='alice@example.com'):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()['access_token'])


def accepted_goal(client, monkeypatch, headers):
    setup(client, headers)
    model(monkeypatch, IPHONE)
    plan = client.post('/ai/chat', headers=headers, json={'messages': ASK, 'goal_planning': True, 'require_budget': True}).json()['plan']
    saved = client.post('/planning/budget-plans', headers=headers, json={'profile': plan['profile'], 'choices': {}, 'budget_fingerprint': plan['budgetFingerprint'], 'request_key': plan['confirmationKey']})
    assert saved.status_code == 201
    return saved.json()['id']


def add(client, headers, amount, goal_id=None, key=None):
    return client.post('/savings/manual', headers=headers, json={'label': 'Savings', 'amount': amount, 'request_key': key or str(uuid4()), **({'goal_id': goal_id} if goal_id else {})})


def goal(client, headers):
    [plan] = client.get('/planning/plans', headers=headers).json()
    return plan


def test_assigned_savings_update_goal_progress(api_client, monkeypatch):
    headers = auth(api_client)
    goal_id = accepted_goal(api_client, monkeypatch, headers)
    assert goal(api_client, headers)['savedAmount'] == 0
    entry = add(api_client, headers, 500, goal_id)
    assert entry.status_code == 201 and entry.json()['goal_id'] == goal_id
    plan = goal(api_client, headers)
    assert plan['savedAmount'] == 500 and plan['contributedAmount'] == 500 and plan['enteredSavedAmount'] == 0
    assert plan['targetAmount'] - plan['savedAmount'] == 4500
    # The plan itself (deadline, monthly contribution) is unchanged.
    assert plan['monthlyContribution'] == 833.34 and plan['months'] == 6
    overview = api_client.get('/savings?year=2026&month=10', headers=headers).json()
    assert overview['goals'] == [{'id': goal_id, 'title': 'iPhone', 'target': 5000.0, 'saved': 500.0, 'remaining': 4500.0}]
    assert overview['total_saved'] == 500


def test_general_savings_never_count_toward_a_goal(api_client, monkeypatch):
    headers = auth(api_client)
    accepted_goal(api_client, monkeypatch, headers)
    assert add(api_client, headers, 300).json()['goal_id'] is None
    assert goal(api_client, headers)['savedAmount'] == 0
    assert api_client.get('/savings?year=2026&month=10', headers=headers).json()['total_saved'] == 300


def test_corrections_and_retries_do_not_double_count(api_client, monkeypatch):
    headers = auth(api_client)
    goal_id = accepted_goal(api_client, monkeypatch, headers)
    key = str(uuid4())
    entry = add(api_client, headers, 500, goal_id, key).json()
    assert add(api_client, headers, 500, goal_id, key).json()['id'] == entry['id']
    assert goal(api_client, headers)['savedAmount'] == 500
    edited = api_client.put(f"/savings/manual/{entry['id']}", headers=headers, json={'label': 'Savings', 'amount': 700, 'goal_id': goal_id})
    assert edited.status_code == 200 and goal(api_client, headers)['savedAmount'] == 700
    # Moving it to general savings removes it from the goal but keeps the money recorded.
    api_client.put(f"/savings/manual/{entry['id']}", headers=headers, json={'label': 'Savings', 'amount': 700})
    assert goal(api_client, headers)['savedAmount'] == 0
    assert api_client.get('/savings?year=2026&month=10', headers=headers).json()['total_saved'] == 700
    api_client.put(f"/savings/manual/{entry['id']}", headers=headers, json={'label': 'Savings', 'amount': 700, 'goal_id': goal_id})
    assert api_client.delete(f"/savings/manual/{entry['id']}", headers=headers).status_code == 204
    assert goal(api_client, headers)['savedAmount'] == 0


def test_only_own_savings_goals_can_be_assigned(api_client, monkeypatch, db_session):
    alice = auth(api_client)
    goal_id = accepted_goal(api_client, monkeypatch, alice)
    bob = auth(api_client, 'bob@example.com')
    assert add(api_client, bob, 100, goal_id).status_code == 422
    assert add(api_client, alice, 100, 'not-a-plan').status_code == 422
    assert db_session.query(ManualSavings).count() == 0
    assert goal(api_client, alice)['savedAmount'] == 0


def test_deleting_goal_keeps_savings_as_general(api_client, monkeypatch, db_session):
    headers = auth(api_client)
    goal_id = accepted_goal(api_client, monkeypatch, headers)
    entry = add(api_client, headers, 500, goal_id).json()
    assert api_client.delete(f'/planning/plans/{goal_id}', headers=headers).status_code == 204
    overview = api_client.get('/savings?year=2026&month=10', headers=headers).json()
    assert overview['goals'] == [] and overview['total_saved'] == 500
    assert overview['manual_entries'] == [dict(entry, goal_id=None)]


def test_adjusted_plan_keeps_assigned_savings(api_client, monkeypatch):
    headers = auth(api_client)
    goal_id = accepted_goal(api_client, monkeypatch, headers)
    add(api_client, headers, 500, goal_id)
    plan = goal(api_client, headers)
    profile = dict(plan['profile'], deadline='2027-09-30')
    updated = api_client.put(f'/planning/budget-plans/{goal_id}', headers=headers, json={'profile': profile, 'choices': {}, 'budget_fingerprint': plan['budgetFingerprint'], 'request_key': str(uuid4())})
    assert updated.status_code == 200 and updated.json()['savedAmount'] == 500
    assert goal(api_client, headers)['savedAmount'] == 500


def test_migration_adds_goal_column_and_keeps_entries(tmp_path):
    import migrate_savings_goals
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        db.execute('CREATE TABLE manual_savings (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), label VARCHAR(80) NOT NULL, amount_cents INTEGER NOT NULL, request_key VARCHAR(36) NOT NULL, UNIQUE(user_id,request_key))')
        db.execute("INSERT INTO users VALUES (1)")
        db.execute("INSERT INTO manual_savings VALUES (1, 1, 'Previous savings', 50000, 'k1')")
    migrate_savings_goals.migrate(str(path))
    migrate_savings_goals.migrate(str(path))
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT id, label, amount_cents, goal_id FROM manual_savings').fetchall() == [(1, 'Previous savings', 50000, None)]
    assert len(list(tmp_path.glob('legacy.backup-savings-goals-*.db'))) == 1
