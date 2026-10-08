
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    # Separate in-memory database for each test
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    TestingSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSession()
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
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_create_transaction(client):
    response = client.post(
        "/transactions/",
        json={
            "amount": 45.5,
            "category": "Food",
            "description": "Lunch",
            "date": "2026-10-08"
        }
    )

    assert response.status_code == 201
    assert response.json()["amount"] == 45.5
    assert response.json()["category"] == "Food"
    assert "id" in response.json()


def test_get_transactions(client):
    client.post(
        "/transactions/",
        json={
            "amount": 25,
            "category": "Transport",
            "description": "Taxi",
            "date": "2026-10-08"
        }
    )

    response = client.get("/transactions/")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["category"] == "Transport"


def test_delete_transaction(client):
    create_response = client.post(
        "/transactions/",
        json={
            "amount": 60,
            "category": "Shopping",
            "description": "Clothes",
            "date": "2026-10-08"
        }
    )

    transaction_id = create_response.json()["id"]

    delete_response = client.delete(
        f"/transactions/{transaction_id}"
    )

    assert delete_response.status_code == 200

    get_response = client.get("/transactions/")
    assert get_response.json() == []


def test_delete_nonexistent_transaction(client):
    response = client.delete("/transactions/99999")

    assert response.status_code == 404


def test_reject_negative_amount(client):
    response = client.post(
        "/transactions/",
        json={
            "amount": -50,
            "category": "Food",
            "description": "Invalid expense",
            "date": "2026-10-08"
        }
    )

    assert response.status_code == 422


def test_spending_summary_with_transactions(client):
    client.post(
        "/transactions/",
        json={
            "amount": 100,
            "category": "Food",
            "description": "Groceries",
            "date": "2026-10-08"
        }
    )

    client.post(
        "/transactions/",
        json={
            "amount": 50,
            "category": "Transport",
            "description": "Fuel",
            "date": "2026-10-08"
        }
    )

    client.post(
        "/transactions/",
        json={
            "amount": 150,
            "category": "Food",
            "description": "Restaurant",
            "date": "2026-10-08"
        }
    )

    response = client.get("/spending/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["total_spending"] == 300
    assert data["category_spending"]["Food"] == 250
    assert data["category_spending"]["Transport"] == 50
    assert data["category_percentages"]["Food"] == 83.33
    assert data["category_percentages"]["Transport"] == 16.67


def test_spending_summary_empty_database(client):
    response = client.get("/spending/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_spending": 0,
        "category_spending": {},
        "category_percentages": {}
    }


def test_spending_summary_after_deletion(client):
    response = client.post(
        "/transactions/",
        json={
            "amount": 200,
            "category": "Shopping",
            "description": "Clothes",
            "date": "2026-10-08"
        }
    )

    transaction_id = response.json()["id"]

    client.delete(f"/transactions/{transaction_id}")

    summary = client.get("/spending/summary")

    assert summary.status_code == 200
    assert summary.json()["total_spending"] == 0



def test_monthly_spending_comparison(client):
    transactions = [
        {"amount": 500, "category": "Food", "date": "2026-09-15"},
        {"amount": 250, "category": "Transport", "date": "2026-09-20"},
        {"amount": 750, "category": "Food", "date": "2026-10-08"},
        {"amount": 200, "category": "Transport", "date": "2026-10-08"}
    ]

    for transaction in transactions:
        response = client.post("/transactions/", json=transaction)
        assert response.status_code == 201

    response = client.get("/spending/compare?year=2026&month=10")

    assert response.status_code == 200

    data = response.json()

    assert data["current_spending"]["Food"] == 750
    assert data["previous_spending"]["Food"] == 500
    assert data["percentage_changes"]["Food"] == 50.0
    assert data["percentage_changes"]["Transport"] == -20.0


def test_monthly_comparison_january(client):
    response = client.get("/spending/compare?year=2026&month=1")

    assert response.status_code == 200
    assert response.json()["previous_year"] == 2025
    assert response.json()["previous_month"] == 12


def test_monthly_comparison_invalid_month(client):
    response = client.get("/spending/compare?year=2026&month=13")

    assert response.status_code == 422


def test_monthly_comparison_no_transactions(client):
    response = client.get("/spending/compare?year=2026&month=10")

    assert response.status_code == 200
    assert response.json()["percentage_changes"] == {}



def test_recommendations_from_saved_transactions(client):
    transactions = [
        {"amount": 500, "category": "Food", "date": "2026-09-15"},
        {"amount": 250, "category": "Transport", "date": "2026-09-20"},
        {"amount": 750, "category": "Food", "date": "2026-10-08"},
        {"amount": 200, "category": "Transport", "date": "2026-10-08"}
    ]

    for transaction in transactions:
        response = client.post("/transactions/", json=transaction)
        assert response.status_code == 201

    response = client.get("/recommendations/?year=2026&month=10")

    assert response.status_code == 200

    recommendations = response.json()["recommendations"]

    assert len(recommendations) == 2

    food = next(r for r in recommendations if r["category"] == "Food")
    transport = next(r for r in recommendations if r["category"] == "Transport")

    assert food["type"] == "spending_increase"
    assert food["priority"] == "high"
    assert food["percentage_change"] == 50.0

    assert transport["type"] == "spending_decrease"
    assert transport["priority"] == "low"
    assert transport["percentage_change"] == -20.0


def test_recommendations_below_threshold(client):
    transactions = [
        {"amount": 100, "category": "Food", "date": "2026-09-15"},
        {"amount": 110, "category": "Food", "date": "2026-10-08"}
    ]

    for transaction in transactions:
        client.post("/transactions/", json=transaction)

    response = client.get("/recommendations/?year=2026&month=10")

    assert response.status_code == 200
    assert response.json()["recommendations"] == []


def test_recommendations_invalid_month(client):
    response = client.get("/recommendations/?year=2026&month=13")

    assert response.status_code == 422


def test_ai_recommendations_success(client, monkeypatch):
    # Replace the actual Ollama call with a fake response
    def fake_ai_explanation(prompt):
        return "Your food spending increased. Consider reviewing your expenses."

    monkeypatch.setattr(
        "app.main.generate_ai_explanation",
        fake_ai_explanation
    )

    transactions = [
        {"amount": 100, "category": "Food", "date": "2026-09-15"},
        {"amount": 150, "category": "Food", "date": "2026-10-08"}
    ]

    for transaction in transactions:
        response = client.post("/transactions/", json=transaction)
        assert response.status_code == 201

    response = client.get("/recommendations/ai?year=2026&month=10")

    assert response.status_code == 200

    recommendations = response.json()["ai_recommendations"]

    assert len(recommendations) == 1
    assert recommendations[0]["category"] == "Food"
    assert recommendations[0]["percentage_change"] == 50.0
    assert recommendations[0]["ai_explanation"] == (
        "Your food spending increased. Consider reviewing your expenses."
    )


def test_ai_recommendations_no_significant_changes(client, monkeypatch):
    def fake_ai_explanation(prompt):
        raise AssertionError("AI should not be called")

    monkeypatch.setattr(
        "app.main.generate_ai_explanation",
        fake_ai_explanation
    )

    transactions = [
        {"amount": 100, "category": "Food", "date": "2026-09-15"},
        {"amount": 110, "category": "Food", "date": "2026-10-08"}
    ]

    for transaction in transactions:
        client.post("/transactions/", json=transaction)

    response = client.get("/recommendations/ai?year=2026&month=10")

    assert response.status_code == 200
    assert response.json()["ai_recommendations"] == []


def test_ai_recommendations_ollama_unavailable(client, monkeypatch):
    def fake_ai_explanation(prompt):
        raise ConnectionError("Ollama unavailable")

    monkeypatch.setattr(
        "app.main.generate_ai_explanation",
        fake_ai_explanation
    )

    transactions = [
        {"amount": 100, "category": "Food", "date": "2026-09-15"},
        {"amount": 150, "category": "Food", "date": "2026-10-08"}
    ]

    for transaction in transactions:
        client.post("/transactions/", json=transaction)

    response = client.get("/recommendations/ai?year=2026&month=10")

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
