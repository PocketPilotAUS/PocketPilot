import json
from datetime import date
from uuid import uuid4
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.transaction import Transaction
from app.models.financial_plan import FinancialPlan
from app.models.recurring import RecurringExpense
from app.models.budget_plan import BudgetPlan

TODAY = date(2026, 10, 16)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("app.routers.planning.local_today", lambda: TODAY)
    monkeypatch.setattr("app.routers.recurring.today_local", lambda: TODAY)


def account(client, db, budget, spent, email="alice@example.com", goal=1000):
    register_user(client, email=email)
    headers = auth_headers(login_user(client, email=email).json()["access_token"])
    user_id = client.get("/auth/me", headers=headers).json()["id"]
    client.put("/budget/setup?year=2026&month=10", headers=headers,
               json={"income": 10000, "categories": [{"name": name, "amount": amount} for name, amount in budget.items()]})
    for category, amount in spent.items():
        db.add(Transaction(user_id=user_id, amount=amount, category=category, date=date(2026, 10, 5)))
    if goal:
        db.add(FinancialPlan(id=str(uuid4()), user_id=user_id, payload=json.dumps(
            {"kind": "savings", "title": "iPhone", "monthlyContribution": goal, "deadline": "2027-03-31", "targetAmount": 5000, "savedAmount": 0})))
    db.commit()
    return headers, user_id


def status(client, headers):
    return client.get("/planning/status", headers=headers).json()


def ai(monkeypatch, changes, tips=()):
    tips = list(tips)
    calls = []
    monkeypatch.setattr("app.ai.client.generate_budget_adjustment", lambda context, instructions=None, mode="adjust": calls.append((context, instructions, mode)) or json.dumps({"changes": changes, "tips": tips}))
    return calls


def credible_history(db, user_id):
    """Two tracked past months, so projections are credible (high confidence)."""
    for month in (8, 9):
        db.add(Transaction(user_id=user_id, amount=4000, category="Rent", date=date(2026, month, 1)))
        for day in (3, 9, 15, 21, 27):
            db.add(Transaction(user_id=user_id, amount=240, category="Food", date=date(2026, month, day)))
        for day in (4, 12, 20, 28):
            db.add(Transaction(user_id=user_id, amount=1500, category="Shopping", date=date(2026, month, day)))
    db.commit()


# Goal at risk: heavy Shopping, in line with the past two months
SCENARIO_B = ({"Rent": 4000, "Food": 1500, "Shopping": 3900}, {"Rent": 4000, "Food": 1000, "Shopping": 3000})


def scenario_b(client, db):
    headers, user_id = account(client, db, *SCENARIO_B)
    # Spread this month's purchases so they set a pace
    db.query(Transaction).filter_by(user_id=user_id).filter(Transaction.category.in_(["Food", "Shopping"])).delete()
    for day in (2, 6, 10, 14):
        db.add(Transaction(user_id=user_id, amount=250, category="Food", date=date(2026, 10, day)))
        db.add(Transaction(user_id=user_id, amount=750, category="Shopping", date=date(2026, 10, day)))
    db.commit()
    credible_history(db, user_id)
    return headers


SCENARIO_A = ({"Rent": 4000, "Food": 1500, "Transport": 100}, {"Rent": 4000, "Food": 2200})


def test_scenario_a_overspending_but_goal_achievable(api_client, db_session):
    headers, _ = account(api_client, db_session, *SCENARIO_A)
    data = status(api_client, headers)
    assert data["level"] == 1
    assert data["over_budget"] == [{"category": "Food", "budget": 1500.0, "spent": 2200.0, "over": 700.0}]
    assert data["recorded_spending"] == 6200 and data["required_contributions"] == 1000
    assert data["available_committed"] == 3800 and data["available_projected"] == 3700 and data["shortfall"] == 0
    # The budget tracker still reports the same overspending, and no budget changed
    budget = api_client.get("/budget/monthly?year=2026&month=10", headers=headers).json()["ideal_budget"]
    assert {row["category"]: row["target"] for row in budget["allocations"]} == {"Rent": 4000, "Food": 1500, "Transport": 100}


def test_scenario_b_goal_at_risk(api_client, db_session):
    headers = scenario_b(api_client, db_session)
    data = status(api_client, headers)
    assert data["forecast_confidence"] == "high" and data["committed"] == 8000 and data["available_committed"] == 2000
    assert data["available_projected"] == pytest.approx(10000 - data["projected_spending"], abs=0.01)
    assert data["level"] == 2 and data["shortfall"] == pytest.approx(1000 - data["available_projected"], abs=0.01)
    assert data["over_budget"] == []


def test_scenario_c_goal_unaffordable(api_client, db_session):
    headers, user_id = account(api_client, db_session, {"Rent": 4000, "Food": 1500, "Shopping": 4000}, {"Rent": 4000, "Food": 1500, "Shopping": 3500})
    db_session.add(RecurringExpense(user_id=user_id, request_key=str(uuid4()), amount_cents=50000, category="Gym", day=25, next_date=date(2026, 10, 25), active=True))
    db_session.commit()
    data = status(api_client, headers)
    assert data["committed"] == 9500 and data["available_committed"] == 500
    assert data["level"] == 3 and data["shortfall"] == 500
    assert data["upcoming_bills"] == [{"category": "Gym", "amount": 500.0, "date": "2026-10-25"}]


def test_recorded_recurring_and_debt_are_counted_once(api_client, db_session):
    from app.models.debt import Debt
    from app.models.debt_payment import DebtPayment
    from app.routers.debts import estimate
    headers, user_id = account(api_client, db_session, *SCENARIO_A)
    db_session.add(Debt(user_id=user_id, name="Car", balance=12000, annual_rate=0, remaining_months=12))
    db_session.commit()
    due = estimate(12000, 0, 12)[0]
    data = status(api_client, headers)
    assert data["unpaid_debt_due"] == due and data["committed"] == 6200 + due
    debt_id = db_session.query(Debt).first().id
    db_session.add(DebtPayment(user_id=user_id, debt_id=debt_id, debt_name="Car", amount_cents=int(due * 100), paid_on=date(2026, 10, 10), request_key=str(uuid4())))
    db_session.commit()
    data = status(api_client, headers)
    assert data["unpaid_debt_due"] == 0 and data["debt_paid"] == due and data["committed"] == 6200 + due


def test_no_goals_no_income_and_isolation(api_client, db_session):
    headers, _ = account(api_client, db_session, *SCENARIO_A, goal=0)
    data = status(api_client, headers)
    assert data["level"] == 1 and data["required_contributions"] == 0
    other, _ = account(api_client, db_session, {"Rent": 1000}, {}, email="bob@example.com", goal=0)
    assert status(api_client, other)["over_budget"] == [] and status(api_client, other)["level"] == 0


def test_level_one_review_is_advice_without_budget_or_savings_changes(api_client, db_session, monkeypatch):
    """Income 10,000, planned 5,600, Food 700 over: expected 6,300, 3,700 left, 2,700 after the 1,000 goal."""
    headers, _ = account(api_client, db_session, *SCENARIO_A)
    calls = ai(monkeypatch, [{"category": "Transport", "new_budget": 0, "reason": "cut"}], tips=["Cook at home for the rest of the month."])
    review = api_client.post("/planning/adjustments/proposal", headers=headers, json={}).json()
    assert calls[0][2] == "advice" and calls[0][0]["goal_amount"] == 0
    assert review["mode"] == "advice" and review["changes"] == [] and review["covers"] is True
    assert review["tips"] == ["Cook at home for the rest of the month."]
    assert review["affordability"] == {"income": 10000.0, "expected_spending": 6300.0, "left_after_spending": 3700.0,
                                       "required_contributions": 1000.0, "left_after_savings": 2700.0}
    assert "max_this_month" not in review and "remaining_shortfall" not in review


def test_no_proposal_without_need_or_when_ai_fails(api_client, db_session, monkeypatch):
    headers, _ = account(api_client, db_session, {"Rent": 4000, "Food": 1500}, {"Rent": 4000})
    assert api_client.post("/planning/adjustments/proposal", headers=headers, json={}).status_code == 422
    monkeypatch.setattr("app.ai.client.generate_budget_adjustment", lambda context, instructions=None, mode="adjust": "not json")
    # Level 1 still gets the verified breakdown without AI tips
    headers, _ = account(api_client, db_session, *SCENARIO_A, email="bob@example.com")
    review = api_client.post("/planning/adjustments/proposal", headers=headers, json={})
    assert review.status_code == 200 and review.json()["tips"] == [] and review.json()["affordability"]["left_after_savings"] == 2700


@pytest.mark.parametrize("spent, flagged", [(500, False), (500.01, False), (525, False), (525.01, True)])
def test_category_warning_requires_more_than_five_percent(api_client, db_session, spent, flagged):
    headers, _ = account(api_client, db_session, {"Shopping":500}, {"Shopping":spent}, goal=0)
    data = status(api_client, headers)
    assert bool(data["over_budget"]) is flagged
    assert data["level"] == (1 if flagged else 0)
    assert data["recorded_spending"] == spent
