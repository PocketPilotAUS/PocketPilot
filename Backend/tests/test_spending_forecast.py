import json
from datetime import date
from decimal import Decimal
from uuid import uuid4
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.transaction import Transaction
from app.models.financial_plan import FinancialPlan
from app.models.recurring import RecurringExpense
from app.services.spending_monitor import spending_status

OCT_16 = date(2026, 10, 16)


@pytest.fixture
def today(monkeypatch):
    current = {"value": OCT_16}
    monkeypatch.setattr("app.routers.recurring.today_local", lambda: current["value"])
    return current


def user(client, db, budget, year=2026, month=10, goals=(1000,), income=10000):
    register_user(client)
    headers = auth_headers(login_user(client).json()["access_token"])
    client.put(f"/budget/setup?year={year}&month={month}", headers=headers,
               json={"income": income, "categories": [{"name": name, "amount": amount} for name, amount in budget.items()]})
    for contribution in goals:
        db.add(FinancialPlan(id=str(uuid4()), user_id=1, payload=json.dumps(
            {"kind": "savings", "title": "Goal", "monthlyContribution": contribution, "deadline": "2027-12-31"})))
    db.commit()
    return headers


def spend(db, category, amount, *days, month=10, year=2026):
    for day in days:
        db.add(Transaction(user_id=1, amount=amount, category=category, date=date(year, month, day)))
    db.commit()


def history(db, months=((2026, 8), (2026, 9)), food=1200, rent=4000):
    """Tracked past months: rent once, food spread over five purchases."""
    for year, month in months:
        spend(db, "Rent", rent, 1, month=month, year=year)
        spend(db, "Food", food / 5, 3, 9, 15, 21, 27, month=month, year=year)


def status(db, today):
    return spending_status(db, 1, today["value"])


def category(data, name):
    return next(row for row in data["categories"] if row["category"] == name)


def test_steady_variable_spending_uses_current_pace(api_client, db_session, today):
    user(api_client, db_session, {"Food": 2000})
    spend(db_session, "Food", 100, 1, 3, 5, 7, 9, 11, 13, 15)
    data = status(db_session, today)
    # 800 over 16 days, 15 days left: 800 / 16 * 15 = 750 more
    assert data["forecast_confidence"] == "moderate"
    assert category(data, "Food")["method"] == "pace" and category(data, "Food")["forecast"] == 1550


def test_one_time_purchase_is_not_extrapolated(api_client, db_session, today):
    user(api_client, db_session, {"Shopping": 5000, "Food": 1000})
    spend(db_session, "Shopping", 100, 2, 5, 8, 11)
    spend(db_session, "Shopping", 3000, 12)
    spend(db_session, "Food", 50, 3, 6, 9, 12)
    data = status(db_session, today)
    # Only the usual 400 sets the pace: 400 / 16 * 15 = 375
    assert category(data, "Shopping")["forecast"] == 3400 + 375


def test_rent_already_paid_versus_still_due(api_client, db_session, today):
    user(api_client, db_session, {"Rent": 4000, "Food": 1500})
    history(db_session)
    due = status(db_session, today)
    assert category(due, "Rent")["method"] == "fixed" and category(due, "Rent")["forecast"] == 4000
    assert due["committed"] == 0  # expected, not yet a known obligation
    spend(db_session, "Rent", 4000, 1)
    paid = status(db_session, today)
    assert category(paid, "Rent")["forecast"] == 4000 and paid["committed"] == 4000


def test_upcoming_recurring_bills_counted_once(api_client, db_session, today):
    user(api_client, db_session, {"Subscriptions": 100, "Gym": 300})
    for name, amount, day in (("Subscriptions", 5000, 5), ("Gym", 30000, 25)):
        db_session.add(RecurringExpense(user_id=1, request_key=str(uuid4()), amount_cents=amount, category=name, day=day, next_date=date(2026, 10, day), active=True))
    db_session.commit()
    data = status(db_session, today)
    # Subscriptions (due on the 5th) is recorded once; Gym (25th) is upcoming once
    assert data["recorded_spending"] == 50 and data["upcoming_bills"] == [{"category": "Gym", "amount": 300.0, "date": "2026-10-25"}]
    assert category(data, "Subscriptions")["forecast"] == 50 and category(data, "Gym")["forecast"] == 300
    assert data["committed"] == 350 and data["projected_spending"] == 350


def test_multiple_months_of_history_are_combined_with_pace(api_client, db_session, today):
    user(api_client, db_session, {"Food": 1500})
    history(db_session, months=((2026, 7), (2026, 8), (2026, 9)), food=1200, rent=4000)
    spend(db_session, "Food", 120, 2, 6, 10, 14)
    data = status(db_session, today)
    pace = Decimal(480) / 16 * 15
    typical = Decimal(1200) * 15 / 31
    expected = (Decimal(480) + ((pace + typical) / 2).quantize(Decimal("0.01"))).quantize(Decimal("0.01"))
    assert data["forecast_confidence"] == "high" and data["history_months"] == 3
    assert category(data, "Food")["method"] == "pace+history" and Decimal(str(category(data, "Food")["forecast"])) == expected


def test_insufficient_history_never_escalates_on_projection_alone(api_client, db_session, today):
    today["value"] = date(2026, 10, 3)
    user(api_client, db_session, {"Rent": 4000, "Shopping": 5500})
    spend(db_session, "Shopping", 500, 2)
    data = status(db_session, today)
    # The uncertain projection never raises a warning by itself...
    assert data["forecast_confidence"] == "low" and data["available_projected"] == 500
    assert "projection" not in data["risk_reasons"]
    # ...but this budget itself doesn't fit the goal: 8,500 is left after protecting savings,
    # while the budget still needs 9,000 (Rent 4,000 unpaid, Shopping 5,000 left)
    assert data["buffer"] == 8500 and data["still_needed"] == 9000
    assert data["level"] == 2 and data["risk_reasons"] == ["low_buffer"]


def test_overspending_is_not_capped_at_budget(api_client, db_session, today):
    user(api_client, db_session, {"Food": 500})
    history(db_session)
    spend(db_session, "Food", 200, 2, 5, 8, 11, 14)
    data = status(db_session, today)
    assert data["over_budget"] == [{"category": "Food", "budget": 500.0, "spent": 1000.0, "over": 500.0}]
    assert category(data, "Food")["forecast"] > 1000


def test_credible_level_two(api_client, db_session, today):
    user(api_client, db_session, {"Rent": 4000, "Food": 1500, "Shopping": 3000})
    history(db_session, food=1200)
    for year, month in ((2026, 8), (2026, 9)):
        spend(db_session, "Shopping", 1000, 4, 12, 20, 28, month=month, year=year)
    spend(db_session, "Rent", 4000, 1)
    spend(db_session, "Shopping", 500, 2, 5, 8, 11, 14)
    spend(db_session, "Food", 100, 3, 7, 11, 15)
    data = status(db_session, today)
    assert data["forecast_confidence"] == "high"
    assert data["projected_spending"] > data["committed"]
    assert data["level"] == 2 and data["shortfall"] == pytest.approx(1000 - (10000 - data["projected_spending"]), abs=0.01)
    assert data["available_committed"] >= 1000


def test_confirmed_level_three_even_with_low_confidence(api_client, db_session, today):
    user(api_client, db_session, {"Rent": 4000, "Shopping": 5000})
    spend(db_session, "Rent", 4000, 1)
    spend(db_session, "Shopping", 5000, 2)
    db_session.add(RecurringExpense(user_id=1, request_key=str(uuid4()), amount_cents=50000, category="Gym", day=25, next_date=date(2026, 10, 25), active=True))
    db_session.commit()
    data = status(db_session, today)
    assert data["forecast_confidence"] == "low"
    assert data["committed"] == 9500 and data["level"] == 3 and data["shortfall"] == 500


def test_multiple_goals_add_their_contributions(api_client, db_session, today):
    user(api_client, db_session, {"Rent": 4000, "Shopping": 5000}, goals=(600, 700))
    spend(db_session, "Rent", 4000, 1)
    spend(db_session, "Shopping", 5000, 2)
    data = status(db_session, today)
    # 10,000 - 9,000 recorded leaves 1,000 for 1,300 of contributions
    assert data["required_contributions"] == 1300 and data["level"] == 3 and data["shortfall"] == 300


def test_month_transition_uses_new_month_and_history(api_client, db_session, today):
    today["value"] = date(2026, 11, 1)
    user(api_client, db_session, {"Rent": 4000, "Food": 1500}, month=11)
    history(db_session, months=((2026, 9), (2026, 10)))
    spend(db_session, "Food", 2500, 5, month=10)  # October's overspending stays in October
    data = status(db_session, today)
    assert data["over_budget"] == [] and data["recorded_spending"] == 0 and data["days_left"] == 29
    # Rent is habitually paid once a month and not yet paid in November
    assert category(data, "Rent")["forecast"] == 4000 and category(data, "Food")["method"] == "history"


def test_my_food_overspending_account(api_client, db_session, today):
    """The real test account: everything recorded on 16 October, Rent from a recurring schedule."""
    user(api_client, db_session, {"Bills": 500, "Rent": 3000, "Subscriptions": 100, "Food": 1500, "Transport": 500})
    db_session.add(RecurringExpense(user_id=1, request_key=str(uuid4()), amount_cents=300000, category="Rent", day=16, next_date=date(2026, 10, 16), active=True))
    db_session.commit()
    for name, amount in (("Food", 1000), ("Transport", 500), ("Bills", 500), ("Food", 1200)):
        spend(db_session, name, amount, 16)
    data = status(db_session, today)
    assert data["recorded_spending"] == 6200 and data["over_budget"] == [{"category": "Food", "budget": 1500.0, "spent": 2200.0, "over": 700.0}]
    assert category(data, "Rent")["method"] == "fixed" and category(data, "Rent")["forecast"] == 3000
    assert data["forecast_confidence"] == "low" and data["available_committed"] == 3800
    assert data["level"] == 1 and data["shortfall"] == 0
