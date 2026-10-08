from app.algorithms.recommendations import (
    generate_spending_recommendations
)


def test_spending_increase():
    monthly_changes = {"Food": 50.0}

    result = generate_spending_recommendations(monthly_changes)

    assert len(result) == 1
    assert result[0]["category"] == "Food"
    assert result[0]["type"] == "spending_increase"
    assert result[0]["priority"] == "high"


def test_spending_decrease():
    monthly_changes = {"Transport": -25.0}

    result = generate_spending_recommendations(monthly_changes)

    assert len(result) == 1
    assert result[0]["type"] == "spending_decrease"
    assert result[0]["priority"] == "low"


def test_no_significant_change():
    monthly_changes = {"Shopping": 10.0}

    result = generate_spending_recommendations(monthly_changes)

    assert result == []


def test_multiple_categories():
    monthly_changes = {
        "Food": 50.0,
        "Transport": -25.0,
        "Shopping": 10.0
    }

    result = generate_spending_recommendations(monthly_changes)

    assert len(result) == 2


def test_threshold_boundary():
    monthly_changes = {
        "Food": 20.0,
        "Transport": -20.0
    }

    result = generate_spending_recommendations(monthly_changes)

    assert len(result) == 2