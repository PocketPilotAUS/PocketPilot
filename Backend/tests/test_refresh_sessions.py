import time
from concurrent.futures import ThreadPoolExecutor

from app.models.refresh_session import RefreshSession, RefreshToken
from app.services.refresh_sessions import digest
from conftest import register_user, login_user, auth_headers


def signed_in(client):
    assert register_user(client).status_code == 201
    result = login_user(client)
    assert result.status_code == 200
    assert result.headers["cache-control"] == "no-store"
    return result.json()


def refresh(client, token):
    return client.post("/auth/refresh", json={"refresh_token": token})


def test_rotation_and_hashed_storage(api_client, db_session):
    first = signed_in(api_client)
    stored = db_session.query(RefreshToken).one()
    assert stored.token_hash == digest(first["refresh_token"])
    assert stored.token_hash != first["refresh_token"]
    original_expiry = db_session.query(RefreshSession).one().expires_at
    response = refresh(api_client, first["refresh_token"])
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    second = response.json()
    assert first["refresh_token"] != second["refresh_token"]
    assert second["expires_in"] == 1800
    assert api_client.get("/auth/me", headers=auth_headers(second["access_token"])).status_code == 200
    db_session.expire_all()
    assert db_session.query(RefreshSession).one().expires_at == original_expiry


def test_replay_revokes_descendants_and_access(api_client):
    first = signed_in(api_client)
    second = refresh(api_client, first["refresh_token"]).json()
    assert refresh(api_client, first["refresh_token"]).status_code == 401
    assert refresh(api_client, second["refresh_token"]).status_code == 401
    assert api_client.get("/auth/me", headers=auth_headers(second["access_token"])).status_code == 401


def test_logout_with_consumed_token_revokes_only_its_family(api_client):
    first = signed_in(api_client)
    other_device = login_user(api_client).json()
    current = refresh(api_client, first["refresh_token"]).json()
    body = {"refresh_token": first["refresh_token"]}
    assert api_client.post("/auth/logout", json=body).status_code == 204
    assert api_client.post("/auth/logout", json=body).status_code == 204
    assert refresh(api_client, current["refresh_token"]).status_code == 401
    assert api_client.get("/auth/me", headers=auth_headers(current["access_token"])).status_code == 401
    assert refresh(api_client, other_device["refresh_token"]).status_code == 200


def test_password_change_revokes_all_sessions(api_client):
    first = signed_in(api_client)
    second = login_user(api_client).json()
    response = api_client.post("/auth/password", headers=auth_headers(first["access_token"]), json={
        "current_password": "correct-horse-1", "new_password": "a-new-password-2"})
    assert response.status_code == 204
    for pair in (first, second):
        assert refresh(api_client, pair["refresh_token"]).status_code == 401
        assert api_client.get("/auth/me", headers=auth_headers(pair["access_token"])).status_code == 401


def test_absolute_expiry(api_client, db_session):
    pair = signed_in(api_client)
    db_session.query(RefreshSession).update({RefreshSession.expires_at: int(time.time()) - 1})
    db_session.commit()
    assert refresh(api_client, pair["refresh_token"]).status_code == 401
    assert api_client.get("/auth/me", headers=auth_headers(pair["access_token"])).status_code == 401


def test_refresh_does_not_require_valid_access_token(api_client, monkeypatch):
    pair = signed_in(api_client)
    monkeypatch.setattr("app.core.security.jwt.decode", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Should not decode access JWT")))
    assert refresh(api_client, pair["refresh_token"]).status_code == 200


def test_token_types_not_interchangeable(api_client):
    pair = signed_in(api_client)
    assert api_client.get("/auth/me", headers=auth_headers(pair["refresh_token"])).status_code == 401
    assert refresh(api_client, pair["access_token"]).status_code == 422
    assert refresh(api_client, "x" * 64).status_code == 401
    assert refresh(api_client, "\u00e9" * 64).status_code == 422


def test_migration_preserves_data_and_is_repeatable(tmp_path):
    import sqlite3
    from migrate_refresh_sessions import migrate
    path = tmp_path / "test.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        db.execute("INSERT INTO users VALUES (7)")
    migrate(path)
    migrate(path)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT id FROM users").fetchall() == [(7,)]
        assert db.execute("SELECT count(*) FROM refresh_tokens").fetchone() == (0,)
    assert len(list(tmp_path.glob("*.backup-refresh-*.db"))) == 1


def test_concurrent_refresh_is_single_use(tmp_path, jwt_secret):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from fastapi import HTTPException
    from app.database import Base
    from app.models.user import User
    from app.services.refresh_sessions import start_session, rotate
    from threading import Barrier
    engine = create_engine("sqlite:///" + (tmp_path / "race.db").as_posix(), connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        user = User(name="Test", email="race@example.com", hashed_password="unused")
        db.add(user)
        db.commit()
        pair = start_session(db, user)
    barrier = Barrier(2)
    def attempt():
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                rotate(db, pair.refresh_token)
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))
    assert sorted(results) == [200, 401]
    with factory() as db:
        assert db.query(RefreshSession).one().revoked
    engine.dispose()
