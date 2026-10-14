import pytest
from conftest import register_user, login_user, auth_headers
from app.routers.debts import estimate


def headers(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


DATA = {"name": "Car loan", "balance": 12000, "annual_rate": 6, "remaining_months": 24, "original_principal": 20000}


def test_crud_and_owner_isolation(api_client):
    alice = headers(api_client)
    bob = headers(api_client, "bob@example.com")
    created = api_client.post("/debts", json=DATA, headers=alice)
    assert created.status_code == 201
    row = created.json()
    assert row["estimated_monthly_payment"] == 531.85
    assert api_client.get("/debts", headers=bob).json() == []
    for method in ["put", "delete"]:
        args = {"headers": bob}
        if method == "put":
            args["json"] = DATA
        assert getattr(api_client, method)(f'/debts/{row["id"]}', **args).status_code == 404
    assert api_client.put(f'/debts/{row["id"]}', json={**DATA, "balance": 0, "original_principal": None}, headers=alice).json()["estimated_monthly_payment"] == 0
    assert api_client.delete(f'/debts/{row["id"]}', headers=alice).status_code == 204
    assert api_client.get("/debts", headers=alice).json() == []


@pytest.mark.parametrize("field,value", [("balance", -1), ("balance", "NaN"), ("balance", "1.001"), ("annual_rate", 101), ("annual_rate", -1), ("remaining_months", 0), ("remaining_months", 601), ("remaining_months", 1.5), ("name", "  "), ("original_principal", 0)])
def test_invalid_inputs(api_client, field, value):
    assert api_client.post("/debts", json={**DATA, field: value}, headers=headers(api_client)).status_code == 422


def test_authentication(api_client):
    assert api_client.get("/debts").status_code == 401
    assert api_client.post("/debts", json=DATA).status_code == 401


def test_zero_rate_and_small_rate():
    assert estimate(1200, 0, 12) == (100, 0)
    payment, interest = estimate(1200, .0001, 12)
    assert payment == 100 and interest >= 0


def test_migration_preserves_data_and_is_idempotent(tmp_path):
    import sqlite3
    from migrate_debts import migrate
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO users VALUES (1, 'Alice')")
    migrate(path)
    migrate(path)
    assert len(list(tmp_path.glob("*.backup-debts-*.db"))) == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM users").fetchone() == ("Alice",)
        assert db.execute("SELECT count(*) FROM debts").fetchone() == (0,)
