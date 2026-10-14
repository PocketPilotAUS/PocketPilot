from uuid import uuid4
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.savings import MonthlySavings, ManualSavings


def headers(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


def body(**changes):
    return {"label": "Previous savings", "amount": "5000.25", "request_key": str(uuid4()), **changes}


def test_crud_totals_and_monthly_preserved(api_client, db_session):
    auth = headers(api_client)
    db_session.add(MonthlySavings(user_id=1, year=2020, month=1, income_cents=100000, spent_cents=70000, extra_debt_cents=0, saved_cents=30000))
    db_session.commit()
    row = api_client.post("/savings/manual", json=body(), headers=auth).json()
    data = api_client.get("/savings?year=2020&month=1", headers=auth).json()
    assert data["manual_total"] == 5000.25 and data["total_saved"] == 5300.25
    assert data["income"] is None, "manual savings do not create monthly income"
    assert api_client.put(f'/savings/manual/{row["id"]}', json={"label": "Emergency fund", "amount": "6000"}, headers=auth).json()["amount"] == 6000
    assert api_client.get("/savings?year=2020&month=1", headers=auth).json()["total_saved"] == 6300
    assert api_client.delete(f'/savings/manual/{row["id"]}', headers=auth).status_code == 204
    assert api_client.get("/savings?year=2020&month=1", headers=auth).json()["total_saved"] == 300
    assert db_session.query(MonthlySavings).count() == 1


def test_repeat_request_is_not_double_counted(api_client, db_session):
    auth = headers(api_client)
    data = body()
    first = api_client.post("/savings/manual", json=data, headers=auth).json()
    second = api_client.post("/savings/manual", json=data, headers=auth).json()
    assert first == second and db_session.query(ManualSavings).count() == 1


def test_owner_isolation_and_auth(api_client):
    alice = headers(api_client)
    payload = body()
    row = api_client.post("/savings/manual", json=payload, headers=alice).json()
    bob = headers(api_client, "bob@example.com")
    assert api_client.get("/savings?year=2020&month=1", headers=bob).json()["manual_entries"] == []
    assert api_client.put(f'/savings/manual/{row["id"]}', json={"label": "Other", "amount": 10}, headers=bob).status_code == 404
    assert api_client.delete(f'/savings/manual/{row["id"]}', headers=bob).status_code == 404
    assert api_client.post("/savings/manual", json=payload).status_code == 401
    assert api_client.post("/savings/manual", json=payload, headers=bob).json()["id"] != row["id"], "same request key scoped to owner"
    assert api_client.delete("/savings/manual/999999999999999999999", headers=alice).status_code == 404


@pytest.mark.parametrize("changes", [{"amount": 0}, {"amount": -1}, {"amount": "NaN"}, {"amount": "1.001"}, {"label": " "}, {"label": "x" * 81}, {"request_key": "bad"}])
def test_validation(api_client, changes):
    assert api_client.post("/savings/manual", json=body(**changes), headers=headers(api_client)).status_code == 422


def test_migration_preserves_existing_table_and_backups(tmp_path):
    import sqlite3
    from migrate_manual_savings import migrate
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO users VALUES (1)")
        db.execute("CREATE TABLE monthly_savings (saved_cents INTEGER)")
        db.execute("INSERT INTO monthly_savings VALUES (30000)")
    migrate(path)
    migrate(path)
    assert len(list(tmp_path.glob("*.backup-manual-savings-*.db"))) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT saved_cents FROM monthly_savings").fetchone() == (30000,)
