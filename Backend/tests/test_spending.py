from app.algorithms.spending_analysis import (
    calculate_total_spending,
    calculate_category_spending,
    calculate_category_percentages,
    compare_monthly_spending
)


def test_total_spending():
    transactions = [
        {"category": "Food", "amount": 100},
        {"category": "Transport", "amount": 50},
        {"category": "Food", "amount": 25}
    ]

    assert calculate_total_spending(transactions) == 175


def test_category_spending():
    transactions = [
        {"category": "Food", "amount": 100},
        {"category": "Transport", "amount": 50},
        {"category": "Food", "amount": 25}
    ]

    result = calculate_category_spending(transactions)

    assert result["Food"] == 125
    assert result["Transport"] == 50


def test_category_percentages():
    transactions = [
        {"category": "Food", "amount": 75},
        {"category": "Transport", "amount": 25}
    ]

    result = calculate_category_percentages(transactions)

    assert result["Food"] == 75
    assert result["Transport"] == 25