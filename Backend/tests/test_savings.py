from datetime import date
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.income import MonthlyIncome
from app.models.transaction import Transaction
from app.models.debt import Debt
from app.models.savings import MonthlySavings


def headers(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


def setup(client, db):
    auth = headers(client)
    db.add(MonthlyIncome(user_id=1, year=2020, month=1, amount_cents=1000000))
    db.add_all([Transaction(user_id=1, amount=6000, category="Food", date=date(2020, 1, 5)), Transaction(user_id=1, amount=1000, category="Debt payments", date=date(2020, 1, 8))])
    db.add(Debt(user_id=1, name="Loan", balance=50000, annual_rate=5, remaining_months=24))
    db.commit()
    return auth


BODY = {"year": 2020, "month": 1, "expected_income": 10000, "expected_spent": 7000, "extra_debt_payments": 0}


def test_confirm_double_count_and_idempotent_update(api_client, db_session):
    auth = setup(api_client, db_session)
    data = api_client.get("/savings?year=2020&month=1", headers=auth).json()
    assert data["spent"] == 7000 and data["total_saved"] == 0
    assert api_client.put("/savings/confirm", json=BODY, headers=auth).json()["saved"] == 3000
    assert api_client.put("/savings/confirm", json=BODY, headers=auth).json()["saved"] == 3000
    assert db_session.query(MonthlySavings).count() == 1
    assert api_client.put("/savings/confirm", json={**BODY, "extra_debt_payments": 500}, headers=auth).json()["saved"] == 2500
    assert api_client.get("/savings?year=2020&month=1", headers=auth).json()["total_saved"] == 2500


def test_shortfall_and_income_missing(api_client, db_session):
    auth = setup(api_client, db_session)
    row = api_client.put("/savings/confirm", json={**BODY, "extra_debt_payments": 4000}, headers=auth).json()
    assert row["saved"] == 0 and row["leftover"] == -1000
    assert api_client.put("/savings/confirm", json={**BODY, "month": 2}, headers=auth).status_code == 422


def test_stale_snapshot_and_confirmations_do_not_change_automatically(api_client, db_session):
    auth = setup(api_client, db_session)
    api_client.put("/savings/confirm", json=BODY, headers=auth)
    db_session.add(Transaction(user_id=1, amount=100, category="Food", date=date(2020, 1, 10)))
    db_session.commit()
    assert api_client.put("/savings/confirm", json=BODY, headers=auth).status_code == 409
    data = api_client.get("/savings?year=2020&month=1", headers=auth).json()
    assert data["spent"] == 7100 and data["total_saved"] == 3000


def test_owner_and_auth(api_client, db_session):
    auth = setup(api_client, db_session)
    api_client.put("/savings/confirm", json=BODY, headers=auth)
    bob = headers(api_client, "bob@example.com")
    data = api_client.get("/savings?year=2020&month=1", headers=bob).json()
    assert data["income"] is None and data["spent"] == 0 and data["history"] == []
    assert api_client.get("/savings?year=2020&month=1").status_code == 401


@pytest.mark.parametrize("changes", [{"year": 9998}, {"extra_debt_payments": -1}, {"extra_debt_payments": "NaN"}, {"extra_debt_payments": "1.001"}, {"month": 13}])
def test_invalid_inputs(api_client, changes):
    assert api_client.put("/savings/confirm", json={**BODY, **changes}, headers=headers(api_client)).status_code == 422


def test_current_month_cannot_confirm(api_client):
    from app.routers.savings import today
    now = today()
    assert api_client.put("/savings/confirm", json={**BODY, "year": now.year, "month": now.month}, headers=headers(api_client)).status_code == 422


def test_migration(tmp_path):
    import sqlite3
    from migrate_savings import migrate
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO users VALUES (1)")
    migrate(path)
    migrate(path)
    assert len(list(tmp_path.glob("*.backup-savings-*.db"))) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM users").fetchone() == (1,)
        assert db.execute("SELECT count(*) FROM monthly_savings").fetchone() == (0,)
