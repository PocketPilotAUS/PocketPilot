from datetime import date
from uuid import uuid4
import sqlite3
from conftest import register_user, login_user, auth_headers
from app.models.debt import Debt
from app.services import debt_schedule


def account(client):
    register_user(client)
    return auth_headers(login_user(client).json()["access_token"])


def loan(client, headers, **extra):
    response = client.post("/debts", headers=headers, json={
        "name": "Car", "balance": 1200, "annual_rate": 0, "remaining_months": 12, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def test_automatic_catchup_totals_idempotency_and_removal(api_client, db_session, monkeypatch):
    clock = [date(2020, 1, 1)]
    monkeypatch.setattr(debt_schedule, "today_local", lambda: clock[0])
    auth = account(api_client)
    first = loan(api_client, auth, automatic_day=31, next_due="2020-01-31")
    second = loan(api_client, auth, name="Other", balance=600)
    assert api_client.get('/debts/payments', headers=auth).json() == []
    clock[0] = date(2020, 3, 31)
    debts = api_client.get('/debts', headers=auth).json()
    assert debts[0]['total_left_to_pay'] == 900
    assert debts[0]['next_due'] == '2020-04-30'
    assert sum(row['total_left_to_pay'] for row in debts) == 1500
    payments = api_client.get('/debts/payments', headers=auth).json()
    assert len(payments) == 3 and all(row['automatic'] for row in payments)
    assert {row['paid_on'] for row in payments} == {'2020-01-31', '2020-02-29', '2020-03-31'}
    assert len(api_client.get('/debts/payments', headers=auth).json()) == 3
    budget = api_client.get('/budget/monthly?year=2020&month=2', headers=auth).json()
    assert budget['spent'] == 100 and budget['category_spending'] == {'Debt': 100}
    savings = api_client.get('/savings?year=2020&month=2', headers=auth).json()
    assert savings['spent'] == 0 and savings['debt_payments'] == 100
    assert api_client.delete(f"/debts/payments/{payments[0]['id']}", headers=auth).status_code == 204
    assert api_client.get('/debts', headers=auth).json()[0]['total_left_to_pay'] == 1000
    assert len(api_client.get('/debts/payments', headers=auth).json()) == 2  # Removed due date stays skipped.


def test_manual_reduces_automatic_instalment_and_retry_is_safe(api_client, db_session, monkeypatch):
    monkeypatch.setattr(debt_schedule, "today_local", lambda: date(2020, 1, 1))
    auth = account(api_client)
    debt = loan(api_client, auth, automatic_day=15, next_due='2020-01-15')
    body = {'amount': 40, 'paid_on': '2020-01-10', 'request_key': str(uuid4())}
    for _ in range(2):
        assert api_client.post(f"/debts/{debt['id']}/payments", headers=auth, json=body).status_code == 201
    monkeypatch.setattr(debt_schedule, "today_local", lambda: date(2020, 1, 15))
    payments = api_client.get('/debts/payments', headers=auth).json()
    assert sorted(row['amount'] for row in payments) == [40, 60]
    assert api_client.get('/debts', headers=auth).json()[0]['total_left_to_pay'] == 1100
    # Don't silently duplicate an instalment already automatically recorded.
    assert api_client.post(f"/debts/{debt['id']}/payments", headers=auth,
        json={**body, 'request_key': str(uuid4())}).status_code == 409


def test_final_payment_caps_at_zero_and_schedule_stops(api_client, db_session, monkeypatch):
    monkeypatch.setattr(debt_schedule, "today_local", lambda: date(2020, 1, 1))
    auth = account(api_client)
    debt = loan(api_client, auth, balance=100, remaining_months=3, automatic_day=1, next_due='2020-02-01')
    monkeypatch.setattr(debt_schedule, "today_local", lambda: date(2020, 6, 1))
    result = api_client.get('/debts', headers=auth).json()[0]
    assert result['total_left_to_pay'] == 0 and result['next_due'] is None
    rows = api_client.get('/debts/payments', headers=auth).json()
    assert len(rows) == 4  # Rounding leaves a final cent.
    assert round(sum(row['amount'] for row in rows), 2) == 100
    assert result['estimated_monthly_payment'] == 0


def test_migration_preserves_existing_records_and_disables_automatic_by_default(tmp_path):
    from migrate_automatic_debts import migrate
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE debts (id INTEGER PRIMARY KEY, balance NUMERIC)')
        db.execute('CREATE TABLE debt_payments (id INTEGER PRIMARY KEY, amount_cents INTEGER)')
        db.execute('INSERT INTO debts VALUES (1, 1200)')
        db.execute('INSERT INTO debt_payments VALUES (1, 10000)')
    migrate(path)
    migrate(path)
    assert len(list(tmp_path.glob('*.backup-auto-debts-*.db'))) == 1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT balance, automatic_day, next_due FROM debts').fetchone() == (1200, None, None)
        assert db.execute('SELECT amount_cents, applied_cents, automatic FROM debt_payments').fetchone() == (10000, 0, 0)


def test_current_due_date_records_on_save_and_rebase_preserves_history(api_client, db_session, monkeypatch):
    monkeypatch.setattr(debt_schedule, "today_local", lambda: date(2020, 1, 15))
    auth = account(api_client)
    debt = loan(api_client, auth, automatic_day=15, next_due='2020-01-15')
    assert debt['total_left_to_pay'] == 1100 and debt['next_due'] == '2020-02-15'
    old = api_client.get('/debts/payments', headers=auth).json()[0]
    updated = api_client.put(f"/debts/{debt['id']}", headers=auth, json={
        'name': 'Updated lender balance', 'balance': 600, 'annual_rate': 0,
        'remaining_months': 6, 'automatic_day': 15, 'next_due': '2020-02-15',
    })
    assert updated.status_code == 200
    assert updated.json()['total_left_to_pay'] == 600
    assert len(api_client.get('/debts/payments', headers=auth).json()) == 1
    api_client.delete(f"/debts/payments/{old['id']}", headers=auth)
    assert api_client.get('/debts', headers=auth).json()[0]['total_left_to_pay'] == 600
