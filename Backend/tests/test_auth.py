from datetime import datetime, timedelta

import jwt
import pytest

from app.core.config import JWT_ALGORITHM
from app.core.security import create_access_token, verify_password
from app.models.user import User
from conftest import auth_headers, login_user, register_user

PASSWORD = "correct-horse-1"
LOGIN_FAILED = {"detail": "Incorrect email or password."}
NOT_AUTHENTICATED = {"detail": "Could not validate credentials."}


def registered_token(client, **user):
    assert register_user(client, **user).status_code == 201
    response = login_user(
        client,
        email=user.get("email", "alice@example.com"),
        password=user.get("password", PASSWORD)
    )
    assert response.status_code == 200
    return response.json()["access_token"]


# Registration

def test_register_success(api_client):
    response = register_user(api_client)

    assert response.status_code == 201

    data = response.json()

    assert set(data) == {"id", "name", "email", "phone", "created_at"}
    assert data["phone"] is None
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert datetime.fromisoformat(data["created_at"]).tzinfo is not None


def test_register_normalizes_email_and_name(api_client, db_session):
    response = register_user(api_client, name="  Alice Smith ", email="  Alice@Example.COM ")

    assert response.status_code == 201
    assert response.json()["email"] == "alice@example.com"
    assert response.json()["name"] == "Alice Smith"
    assert db_session.query(User).one().email == "alice@example.com"


def test_password_stored_as_argon2_hash(api_client, db_session):
    register_user(api_client)

    stored = db_session.query(User).one().hashed_password

    assert stored != PASSWORD
    assert PASSWORD not in stored
    assert stored.startswith("$argon2id$")
    assert verify_password(PASSWORD, stored)


def test_register_response_never_contains_password(api_client):
    body = register_user(api_client).text

    assert PASSWORD not in body
    assert "password" not in body
    assert "$argon2" not in body


@pytest.mark.parametrize("email", [
    "alice@example.com",
    "ALICE@EXAMPLE.COM",
    "Alice@Example.com",
    " alice@example.com "
])
def test_duplicate_email_rejected(api_client, db_session, email):
    register_user(api_client)

    response = register_user(api_client, name="Other", email=email, password="another-pass-2")

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with this email already exists."}
    assert db_session.query(User).count() == 1


def test_duplicate_race_handled_by_database(api_client, db_session, monkeypatch):
    # Simulate two requests passing the duplicate check at the same time
    register_user(api_client)
    monkeypatch.setattr("app.routers.auth.get_user_by_email", lambda db, email: None)

    response = register_user(api_client)

    assert response.status_code == 409
    assert db_session.query(User).count() == 1

    # The API keeps working after the failed insert
    monkeypatch.undo()
    assert register_user(api_client, email="bob@example.com").status_code == 201


@pytest.mark.parametrize("email", [
    "",
    "   ",
    "alice",
    "alice@",
    "@example.com",
    "alice@example",
    "alice example@test.com",
    "alice@@example.com",
    "a" * 250 + "@x.com"
])
def test_invalid_email_rejected(api_client, email):
    assert register_user(api_client, email=email).status_code == 422


@pytest.mark.parametrize("password", ["", "short", "1234567", "x" * 129])
def test_invalid_password_rejected(api_client, password):
    assert register_user(api_client, password=password).status_code == 422


@pytest.mark.parametrize("password", ["12345678", "x" * 128, "pässwörd-日本"])
def test_password_length_boundaries_accepted(api_client, password):
    assert register_user(api_client, password=password).status_code == 201


@pytest.mark.parametrize("name", ["", "   ", "x" * 101, "Alice\nSmith", "Bad\x00Name"])
def test_invalid_name_rejected(api_client, name):
    assert register_user(api_client, name=name).status_code == 422


@pytest.mark.parametrize("missing", ["name", "email", "password"])
def test_missing_register_field_rejected(api_client, missing):
    payload = {"name": "Alice", "email": "alice@example.com", "password": PASSWORD}
    del payload[missing]

    assert api_client.post("/auth/register", json=payload).status_code == 422


@pytest.mark.parametrize("extra", [{"id": 99}, {"hashed_password": "x"}, {"is_admin": True}])
def test_unexpected_register_fields_rejected(api_client, db_session, extra):
    payload = {"name": "Alice", "email": "alice@example.com", "password": PASSWORD, **extra}

    assert api_client.post("/auth/register", json=payload).status_code == 422
    assert db_session.query(User).count() == 0


@pytest.mark.parametrize("path, payload", [
    ("/auth/register", {"name": "Alice", "email": "alice@example.com", "password": "secret7"}),
    # A missing field normally echoes the whole request body
    ("/auth/register", {"name": "Alice", "password": "secret-password"}),
    ("/auth/login", {"password": "secret-password"}),
    ("/auth/login", {"email": "alice@example.com", "password": "secret-" + "x" * 130})
])
def test_validation_errors_do_not_echo_password(api_client, path, payload):
    response = api_client.post(path, json=payload)

    assert response.status_code == 422
    assert "secret" not in response.text
    assert "input" not in response.text
    # Still useful: says which field failed and why
    assert response.json()["detail"][0]["loc"][0] == "body"
    assert response.json()["detail"][0]["msg"]


def test_other_endpoints_keep_default_validation_errors(api_client):
    token = registered_token(api_client)

    response = api_client.post(
        "/transactions/",
        json={"amount": -50, "category": "Food", "date": "2026-10-08"},
        headers=auth_headers(token)
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["input"] == -50


# Login

def test_login_success(api_client, jwt_secret):
    user_id = register_user(api_client).json()["id"]

    response = login_user(api_client)

    assert response.status_code == 200

    data = response.json()

    assert set(data) == {"access_token", "token_type", "expires_in"}
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 30 * 60

    claims = jwt.decode(data["access_token"], jwt_secret, algorithms=[JWT_ALGORITHM])
    assert claims["sub"] == str(user_id)


def test_login_email_is_case_insensitive(api_client):
    register_user(api_client)

    assert login_user(api_client, email="  ALICE@example.com ").status_code == 200


def test_login_password_is_case_sensitive(api_client):
    register_user(api_client)

    assert login_user(api_client, password=PASSWORD.upper()).status_code == 401


def test_wrong_password_and_unknown_email_look_identical(api_client):
    register_user(api_client)

    wrong_password = login_user(api_client, password="wrong-password")
    unknown_email = login_user(api_client, email="nobody@example.com")

    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json() == LOGIN_FAILED
        assert response.headers["WWW-Authenticate"] == "Bearer"


def test_unknown_email_still_checks_a_password(api_client, monkeypatch):
    # Timing protection: a hash is verified even when the user doesn't exist
    calls = []
    monkeypatch.setattr("app.routers.auth.simulate_password_check", calls.append)

    login_user(api_client, email="nobody@example.com", password="guess-1234")

    assert calls == ["guess-1234"]


@pytest.mark.parametrize("payload", [
    {},
    {"email": "alice@example.com"},
    {"password": PASSWORD},
    {"email": "", "password": PASSWORD},
    {"email": "alice@example.com", "password": ""},
    {"email": "alice@example.com", "password": "x" * 129},
    {"email": "alice@example.com", "password": PASSWORD, "extra": 1}
])
def test_invalid_login_payload_rejected(api_client, payload):
    assert api_client.post("/auth/login", json=payload).status_code == 422


def test_login_without_secret_fails_safely(api_client, monkeypatch, caplog):
    register_user(api_client)
    monkeypatch.delenv("JWT_SECRET_KEY")

    response = login_user(api_client)

    assert response.status_code == 503
    assert response.json() == {"detail": "Authentication is not configured on the server."}
    assert "JWT_SECRET_KEY" in caplog.text


# Current user (/auth/me)

def test_me_returns_authenticated_user(api_client):
    token = registered_token(api_client)

    response = api_client.get("/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"
    assert set(response.json()) == {"id", "name", "email", "phone", "created_at"}


def test_me_identifies_each_user_correctly(api_client):
    alice = registered_token(api_client)
    bob = registered_token(api_client, name="Bob", email="bob@example.com", password="bob-password-2")

    alice_me = api_client.get("/auth/me", headers=auth_headers(alice)).json()
    bob_me = api_client.get("/auth/me", headers=auth_headers(bob)).json()

    assert alice_me["email"] == "alice@example.com"
    assert bob_me["email"] == "bob@example.com"
    assert alice_me["id"] != bob_me["id"]


@pytest.mark.parametrize("headers", [
    {},
    {"Authorization": ""},
    {"Authorization": "Bearer"},
    {"Authorization": "Bearer "},
    {"Authorization": "Basic YWxpY2U6cGFzc3dvcmQ="},
    {"Authorization": "Token abc"},
    {"Authorization": "Bearer not-a-real-token"}
])
def test_me_rejects_missing_or_malformed_credentials(api_client, headers):
    response = api_client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_me_rejects_expired_token(api_client):
    user_id = register_user(api_client).json()["id"]
    token = create_access_token(user_id, expires_delta=timedelta(seconds=-1))

    response = api_client.get("/auth/me", headers=auth_headers(token))

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


def test_me_rejects_tampered_token(api_client):
    token = registered_token(api_client)
    header, payload, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]

    response = api_client.get("/auth/me", headers=auth_headers(f"{header}.{payload}.{flipped}"))

    assert response.status_code == 401


def test_me_rejects_token_from_other_secret(api_client, monkeypatch):
    user_id = register_user(api_client).json()["id"]
    token = jwt.encode(
        {"sub": str(user_id), "type": "access", "iat": 1, "exp": 9999999999},
        "y" * 64,
        algorithm=JWT_ALGORITHM
    )

    assert api_client.get("/auth/me", headers=auth_headers(token)).status_code == 401


def test_me_rejects_token_for_nonexistent_user(api_client):
    token = create_access_token(999)

    response = api_client.get("/auth/me", headers=auth_headers(token))

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


def test_me_rejects_token_after_user_removed(api_client, db_session):
    token = registered_token(api_client)
    db_session.query(User).delete()
    db_session.commit()

    assert api_client.get("/auth/me", headers=auth_headers(token)).status_code == 401


def test_me_rejects_old_tokens_after_secret_rotation(api_client, monkeypatch):
    token = registered_token(api_client)
    monkeypatch.setenv("JWT_SECRET_KEY", "z" * 64)

    assert api_client.get("/auth/me", headers=auth_headers(token)).status_code == 401


# Existing functionality

def test_health_check_still_public(api_client):
    # Financial endpoints require a login (see test_user_isolation.py)
    assert api_client.get("/").status_code == 200


def test_openapi_documents_bearer_auth(api_client):
    schema = api_client.get("/openapi.json").json()

    assert {"/auth/register", "/auth/login", "/auth/me"} <= set(schema["paths"])
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
