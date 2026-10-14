from datetime import date
from uuid import uuid4
import sqlite3
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction


def setup(client, db):
    register_user(client)
    auth = auth_headers(login_user(client).json()['access_token'])
    debt = client.post('/debts', headers=auth, json={'name': 'Loan', 'balance': 10000, 'annual_rate': 5, 'remaining_months': 24}).json()
    db.add(MonthlyIncome(user_id=1, year=2020, month=1, amount_cents=1000000))
    db.add(Transaction(user_id=1, amount=1000, category='Food', date=date(2020, 1, 5)))
    db.commit()
    return auth, debt


def payment(client, auth, debt, amount=500, paid_on='2020-01-15', key=None):
    return client.post(f"/debts/{debt['id']}/payments", headers=auth, json={'amount': amount, 'paid_on': paid_on, 'request_key': key or str(uuid4())})


def test_month_owner_and_confirmation_snapshot(api_client, db_session):
    auth, debt = setup(api_client, db_session)
    assert api_client.get('/savings?year=2020&month=1', headers=auth).json()['debt_payments'] == 0
    key = str(uuid4())
    assert payment(api_client, auth, debt, key=key).status_code == 201
    assert payment(api_client, auth, debt, key=key).status_code == 201
    assert payment(api_client, auth, debt, amount=600, key=key).status_code == 409
    payment(api_client, auth, debt, amount=900, paid_on='2020-02-01')
    register_user(api_client, email='bob@example.com')
    bob = auth_headers(login_user(api_client, email='bob@example.com').json()['access_token'])
    assert payment(api_client, bob, debt).status_code == 404
    assert api_client.get('/debts/payments', headers=bob).json() == []
    data = api_client.get('/savings?year=2020&month=1', headers=auth).json()
    assert data['debt_payments'] == 500
    body = {'year': 2020, 'month': 1, 'expected_income': 10000, 'expected_spent': 1000, 'expected_debt_payments': 500}
    saved = api_client.put('/savings/confirm', headers=auth, json=body).json()
    assert saved['saved'] == 8500 and saved['debt_payments'] == 500
    payment(api_client, auth, debt, amount=100)
    assert api_client.put('/savings/confirm', headers=auth, json=body).status_code == 409
    assert api_client.get('/savings?year=2020&month=1', headers=auth).json()['total_saved'] == 8500
    updated = api_client.put('/savings/confirm', headers=auth, json={**body, 'expected_debt_payments': 600}).json()
    assert updated['saved'] == 8400


def test_removal_and_loan_deletion_keep_history(api_client, db_session):
    auth, debt = setup(api_client, db_session)
    row = payment(api_client, auth, debt).json()
    api_client.delete(f"/debts/{debt['id']}", headers=auth)
    assert api_client.get('/debts/payments', headers=auth).json()[0]['debt_name'] == 'Loan'
    assert api_client.get('/savings?year=2020&month=1', headers=auth).json()['debt_payments'] == 500
    register_user(api_client, email='bob@example.com')
    bob = auth_headers(login_user(api_client, email='bob@example.com').json()['access_token'])
    assert api_client.delete(f"/debts/payments/{row['id']}", headers=bob).status_code == 404
    assert api_client.delete(f"/debts/payments/{row['id']}", headers=auth).status_code == 204
    assert api_client.get('/savings?year=2020&month=1', headers=auth).json()['debt_payments'] == 0


@pytest.mark.parametrize('amount,paid_on', [(0, '2020-01-01'), (-1, '2020-01-01'), ('1.001', '2020-01-01'), ('NaN', '2020-01-01'), (5, '2099-01-01'), (5, '2020-02-30')])
def test_invalid_payment(api_client, db_session, amount, paid_on):
    auth, debt = setup(api_client, db_session)
    assert payment(api_client, auth, debt, amount, paid_on).status_code == 422


def test_migration_preserves_database(tmp_path):
    from migrate_debt_payments import migrate
    path = tmp_path / 'test.db'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE users (id INTEGER PRIMARY KEY)')
        db.execute('INSERT INTO users VALUES (1)')
    migrate(path)
    migrate(path)
    assert len(list(tmp_path.glob('*.backup-debt-payments-*.db'))) == 1
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT * FROM users').fetchall() == [(1,)]
        assert db.execute('SELECT count(*) FROM debt_payments').fetchone() == (0,)


def test_auth_and_missing_storage(api_client, db_session):
    auth, debt = setup(api_client, db_session)
    assert api_client.get('/debts/payments').status_code == 401
    from sqlalchemy import text
    db_session.execute(text('DROP TABLE debt_payments'))
    db_session.commit()
    assert api_client.get('/debts/payments', headers=auth).status_code == 503
    assert api_client.get('/savings?year=2020&month=1', headers=auth).status_code == 503
