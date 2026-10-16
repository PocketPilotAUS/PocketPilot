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


def test_dashboard_groups_debt_without_changing_savings(api_client, db_session):
    auth, debt = setup(api_client, db_session)
    second = api_client.post('/debts', headers=auth, json={
        'name': 'Second loan', 'balance': 5000, 'annual_rate': 0, 'remaining_months': 12,
    }).json()
    db_session.add(Transaction(user_id=1, amount=2000, category='Rent', date=date(2020, 1, 5)))
    db_session.commit()
    first_payment = payment(api_client, auth, debt, amount=3000).json()
    payment(api_client, auth, second, amount=1600)
    payment(api_client, auth, debt, amount=900, paid_on='2020-02-01')

    def dashboard():
        response = api_client.get('/budget/monthly?year=2020&month=1', headers=auth)
        assert response.status_code == 200
        return response.json()

    data = dashboard()
    assert data['category_spending'] == {'Food': 1000, 'Rent': 2000, 'Debt': 4600}
    assert data['spent'] == 7600
    assert data['remaining'] == 2400
    assert data['spent_percentage'] == 76
    savings = api_client.get('/savings?year=2020&month=1', headers=auth).json()
    assert savings['spent'] == 3000 and savings['debt_payments'] == 4600
    confirmed = api_client.put('/savings/confirm', headers=auth, json={
        'year': 2020, 'month': 1, 'expected_income': 10000,
        'expected_spent': 3000, 'expected_debt_payments': 4600,
    })
    assert confirmed.status_code == 200
    assert confirmed.json()['saved'] == 2400
    # Changing income must return the same combined summary.
    updated = api_client.put('/budget/income?year=2020&month=1', headers=auth, json={'amount': 10000})
    assert updated.json()['spent'] == 7600
    api_client.delete(f"/debts/payments/{first_payment['id']}", headers=auth)
    assert dashboard()['category_spending']['Debt'] == 1600
    assert dashboard()['remaining'] == 5400

    register_user(api_client, email='other@example.com')
    other = auth_headers(login_user(api_client, email='other@example.com').json()['access_token'])
    other_data = api_client.get('/budget/monthly?year=2020&month=1', headers=other).json()
    assert other_data['spent'] == 0 and other_data['category_spending'] == {}


def test_automatic_debt_budget_tracks_loans_and_keeps_payments_separate(api_client, db_session):
    auth, debt = setup(api_client, db_session)
    from app.routers.debts import estimate
    expected = estimate(10000, 5, 24)[0]

    def budget():
        response = api_client.get('/budget/monthly?year=2020&month=1', headers=auth)
        assert response.status_code == 200
        return response.json()

    def debt_row():
        rows = [row for row in budget()['ideal_budget']['allocations'] if row['category'] == 'Debt']
        assert len(rows) == 1
        return rows[0]

    assert debt_row()['target'] == expected
    assert debt_row()['spent'] == 0 and debt_row()['automatic'] is True
    assert budget()['spent'] == 1000  # A planned instalment is not a payment.
    second = api_client.post('/debts', headers=auth, json={
        'name': 'Second loan', 'balance': 1200, 'annual_rate': 0, 'remaining_months': 12,
    }).json()
    assert debt_row()['target'] == round(expected + 100, 2)
    response = api_client.put('/budget/setup?year=2020&month=1', headers=auth, json={
        'income': 10000, 'categories': [{'name': 'Food', 'amount': 2000}, {'name': 'debt', 'amount': 1}],
    })
    assert response.status_code == 200
    assert debt_row()['target'] == round(expected + 100, 2)
    assert budget()['ideal_budget']['planned_total'] == round(2000 + expected + 100, 2)
    payment(api_client, auth, debt, amount=200)
    payment(api_client, auth, second, amount=100)
    assert debt_row()['spent'] == 300
    assert budget()['spent'] == 1300
    edited = api_client.put(f"/debts/{debt['id']}", headers=auth, json={
        'name': 'Loan', 'balance': 2400, 'annual_rate': 0, 'remaining_months': 12,
    })
    assert edited.status_code == 200
    assert debt_row()['target'] == 300
    api_client.delete(f"/debts/{second['id']}", headers=auth)
    assert debt_row()['target'] == 200 and debt_row()['spent'] == 300
    api_client.delete(f"/debts/{debt['id']}", headers=auth)
    result = budget()
    assert all(row['category'] != 'Debt' for row in result['ideal_budget']['allocations'])
    assert result['category_spending']['Debt'] == 300  # Paid history survives loan deletion.
    assert result['ideal_budget']['planned_total'] == 2000
