import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def jwt_secret(monkeypatch):
    # Random per test, so no real or shared secret is ever needed
    secret = secrets.token_urlsafe(64)
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)
    return secret


@pytest.fixture(autouse=True)
def default_ai_settings(monkeypatch):
    # Tests check the team defaults, not a developer's local Backend/.env
    monkeypatch.delenv("OLLAMA_THINK", raising=False)


@pytest.fixture(autouse=True)
def no_goal_extraction(monkeypatch):
    # Chat tests mock the model reply; the separate goal-fact extraction never
    # reaches a real Ollama server unless a test replaces this stub.
    def unavailable(messages):
        raise ValueError("Goal extraction is not available in tests")
    monkeypatch.setattr("app.routers.chat.extract_goal_facts", unavailable)


@pytest.fixture
def session_factory():
    # Separate in-memory database for each test
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=test_engine)

    try:
        yield sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    finally:
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


@pytest.fixture
def db_session(session_factory):
    # For checking what the API stored
    session = session_factory()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(session_factory, jwt_secret):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def register_user(client, name="Alice", email="alice@example.com", password="correct-horse-1"):
    return client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password}
    )


def login_user(client, email="alice@example.com", password="correct-horse-1"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password}
    )


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}
