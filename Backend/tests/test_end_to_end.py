import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from conftest import auth_headers
from migrate_add_users import migrate
from migrate_refresh_sessions import migrate as migrate_refresh_sessions
from test_migration import LEGACY_ROWS, legacy_rows, make_legacy_db


@pytest.fixture
def migrated_client(tmp_path, jwt_secret):
    # A database file in the original pre-authentication format, migrated,
    # then served by the real application
    path = make_legacy_db(tmp_path / "pocketpilot.db")
    migrate(path)
    migrate_refresh_sessions(path)

    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, path
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def sign_up(client, name, email, password):
    response = client.post("/auth/register", json={"name": name, "email": email, "password": password})
    assert response.status_code == 201

    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200

    return auth_headers(response.json()["access_token"])


def test_full_workflow_on_migrated_database(migrated_client):
    client, path = migrated_client

    # Register and log in
    alice = sign_up(client, "Alice", "alice@example.com", "alice-password-1")
    assert client.get("/auth/me", headers=alice).json()["name"] == "Alice"

    # Create and retrieve
    created = client.post(
        "/transactions/",
        json={"amount": 42.5, "category": "Food", "description": "Dinner", "date": "2026-10-09"},
        headers=alice
    )
    assert created.status_code == 201
    transaction_id = created.json()["id"]

    listed = client.get("/transactions/", headers=alice).json()
    assert [t["id"] for t in listed] == [transaction_id]

    # Summary includes only Alice's transaction, not the legacy rows
    summary = client.get("/spending/summary", headers=alice).json()
    assert summary["total_spending"] == 42.5
    assert summary["category_spending"] == {"Food": 42.5}

    # Another user cannot see or delete it
    bob = sign_up(client, "Bob", "bob@example.com", "bob-password-1")
    assert client.get("/transactions/", headers=bob).json() == []
    assert client.delete(f"/transactions/{transaction_id}", headers=bob).status_code == 404
    assert client.get("/spending/summary", headers=bob).json()["total_spending"] == 0

    # Anonymous requests are refused
    assert client.get("/transactions/").status_code == 401
    assert client.delete(f"/transactions/{transaction_id}").status_code == 401

    # Owner deletes it
    assert client.delete(f"/transactions/{transaction_id}", headers=alice).status_code == 200
    assert client.get("/transactions/", headers=alice).json() == []
    assert client.get("/spending/summary", headers=alice).json()["total_spending"] == 0

    # Legacy rows were never exposed or changed, and are still unowned
    assert legacy_rows(path) == LEGACY_ROWS
    connection = sqlite3.connect(path)
    try:
        legacy_ids = [row[0] for row in LEGACY_ROWS]
        owners = connection.execute(
            f"SELECT user_id FROM transactions WHERE id IN ({','.join('?' * len(legacy_ids))})",
            legacy_ids
        ).fetchall()
    finally:
        connection.close()
    assert owners == [(None,)] * len(LEGACY_ROWS)


def test_migration_leaves_fresh_database_untouched(tmp_path):
    # A database created by init_db.py already has the current schema
    path = tmp_path / "pocketpilot.db"
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    original = path.read_bytes()

    result = migrate(path)

    assert result.changes == []
    assert result.backup is None
    assert path.read_bytes() == original
