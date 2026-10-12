from conftest import register_user, login_user, auth_headers
import sqlite3
from migrate_account_settings import migrate


def account(client, email="alice@example.com"):
    register_user(client, email=email)
    token = login_user(client, email=email).json()["access_token"]
    return auth_headers(token)


def test_profile_persists_and_only_changes_current_user(api_client):
    alice = account(api_client)
    bob = account(api_client, "bob@example.com")
    response = api_client.patch("/auth/me", headers=alice, json={"name": " Alice Smith ", "email": "ALICE@example.com", "phone": "+971 50 123 4567"})
    assert response.status_code == 200
    assert response.json()["name"] == "Alice Smith"
    assert response.json()["phone"] == "+971501234567"
    assert "hashed_password" not in response.json()
    assert api_client.get("/auth/me", headers=alice).json()["phone"] == "+971501234567"
    assert api_client.get("/auth/me", headers=bob).json()["phone"] is None
    assert api_client.patch("/auth/me", headers=alice, json={"name": "Alice", "email": "alice@example.com", "phone": ""}).json()["phone"] is None


def test_email_requires_password_and_rejects_duplicates(api_client):
    headers = account(api_client)
    account(api_client, "bob@example.com")
    body = {"name": "Alice", "email": "new@example.com", "phone": None}
    assert api_client.patch("/auth/me", headers=headers, json=body).status_code == 403
    assert api_client.patch("/auth/me", headers=headers, json={**body, "current_password": "wrong"}).status_code == 403
    assert api_client.patch("/auth/me", headers=headers, json={**body, "email": "BOB@example.com", "current_password": "correct-horse-1"}).status_code == 409
    assert api_client.get("/auth/me", headers=headers).json()["email"] == "alice@example.com"
    assert api_client.patch("/auth/me", headers=headers, json={**body, "current_password": "correct-horse-1"}).status_code == 200
    assert login_user(api_client).status_code == 401
    assert login_user(api_client, email="new@example.com").status_code == 200


def test_password_change_revokes_all_old_tokens(api_client):
    first = account(api_client)
    second = auth_headers(login_user(api_client).json()["access_token"])
    body = {"current_password": "correct-horse-1", "new_password": "a-new-password-2"}
    assert api_client.post("/auth/password", headers=first, json={**body, "current_password": "wrong"}).status_code == 403
    assert api_client.get("/auth/me", headers=first).status_code == 200
    assert api_client.post("/auth/password", headers=first, json=body).status_code == 204
    assert api_client.get("/auth/me", headers=first).status_code == 401
    assert api_client.get("/auth/me", headers=second).status_code == 401
    assert login_user(api_client).status_code == 401
    new_token = login_user(api_client, password="a-new-password-2").json()["access_token"]
    assert api_client.get("/auth/me", headers=auth_headers(new_token)).status_code == 200


def test_settings_validation_and_authentication(api_client):
    headers = account(api_client)
    body = {"name": "Alice", "email": "alice@example.com", "phone": None}
    assert api_client.patch("/auth/me", json=body).status_code == 401
    for invalid in [{"name": " "}, {"email": "bad"}, {"phone": "abc"}, {"phone": "123"}, {"user_id": 2}]:
        assert api_client.patch("/auth/me", headers=headers, json={**body, **invalid}).status_code == 422
    assert api_client.post("/auth/password", headers=headers, json={"current_password": "correct-horse-1", "new_password": "short"}).status_code == 422
    assert api_client.post("/auth/password", headers=headers, json={"current_password": "correct-horse-1", "new_password": "correct-horse-1"}).status_code == 422


def test_settings_migration_preserves_records_and_is_repeatable(tmp_path):
    path = tmp_path / "example.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO users VALUES (1, 'Alice')")
        db.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount INTEGER)")
        db.execute("INSERT INTO transactions VALUES (1, 500)")
    migrate(path)
    migrate(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM users").fetchall() == [(1, "Alice")]
        assert db.execute("SELECT * FROM transactions").fetchall() == [(1, 500)]
        db.execute("INSERT INTO account_settings (user_id) VALUES (1)")
        assert db.execute("SELECT token_version FROM account_settings").fetchone() == (0,)
    backups = list(tmp_path.glob("example.backup-settings-*.db"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute("SELECT * FROM transactions").fetchall() == [(1, 500)]
        assert db.execute("SELECT name FROM sqlite_master WHERE name='account_settings'").fetchone() is None
