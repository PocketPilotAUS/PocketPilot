"""Proactive Level 2 when the savings-protected buffer is too small (real test account data).

Buffer = income - recorded spending - debt paid - upcoming bills - unpaid instalments - goal savings.
Level 2 when the buffer is smaller than what the budget still needs this month;
Level 3 only when the buffer is negative.
"""
import json
from datetime import date
from uuid import uuid4
import pytest
from test_plan_recommendations import account, ai, status, propose, TODAY, PHONE_SUGGESTION
from app.models.financial_plan import FinancialPlan
from app.models.recurring import RecurringExpense

# Budget still needed on 16 October: Food 1,500 x 15/31 = 725.81 (over budget, but everyday),
# Subscriptions 100 left; Rent is recurring, Bills and Transport were settled by one payment
STILL_NEEDED = 825.81


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("app.routers.planning.local_today", lambda: TODAY)
    monkeypatch.setattr("app.routers.recurring.today_local", lambda: TODAY)


def bill(db, amount, day=25):
    db.add(RecurringExpense(user_id=1, request_key=str(uuid4()), amount_cents=amount * 100, category="Gym", day=day, next_date=date(2026, 10, day), active=True))
    db.commit()


def test_8700_recorded_is_proactive_level_two(api_client, db_session):
    headers, _ = account(api_client, db_session, shopping=(2500,))
    data = status(api_client, headers)
    assert data["recorded_spending"] == 8700 and data["available_committed"] == 1300
    assert data["forecast_confidence"] == "low"   # limited history doesn't hide the risk
    assert data["level"] == 2 and data["risk_reasons"] == ["low_buffer"]
    assert data["buffer"] == 300 and data["still_needed"] == STILL_NEEDED and data["daily_allowance"] == 20
    assert data["shortfall"] == pytest.approx(STILL_NEEDED - 300, abs=0.01)


def test_9300_recorded_stays_level_three_with_300_shortfall(api_client, db_session):
    headers, _ = account(api_client, db_session, shopping=(150, 150, 150, 150, 2500))
    data = status(api_client, headers)
    assert data["level"] == 3 and data["shortfall"] == 300 and data["buffer"] == -300 and data["risk_reasons"] == []


def test_normal_account_stays_level_one(api_client, db_session):
    headers, _ = account(api_client, db_session)
    data = status(api_client, headers)
    assert data["level"] == 1 and data["risk_reasons"] == []
    assert data["buffer"] == 2800 and data["still_needed"] == STILL_NEEDED and data["daily_allowance"] == pytest.approx(186.67)


def test_upcoming_bills_reduce_the_buffer(api_client, db_session):
    headers, _ = account(api_client, db_session)
    bill(db_session, 2000)
    data = status(api_client, headers)
    assert data["committed"] == 8200 and data["buffer"] == 800
    assert data["level"] == 2 and data["risk_reasons"] == ["low_buffer"]
    bill(db_session, 900, day=28)
    data = status(api_client, headers)
    assert data["buffer"] == -100 and data["level"] == 3 and data["shortfall"] == 100


def test_zero_savings_goals(api_client, db_session):
    headers, _ = account(api_client, db_session, shopping=(3100,))
    db_session.query(FinancialPlan).delete()
    db_session.commit()
    data = status(api_client, headers)
    # 700 left of income, while the budget still needs 825.81
    assert data["required_contributions"] == 0 and data["buffer"] == 700
    assert data["level"] == 2 and data["risk_reasons"] == ["low_buffer"]


def test_low_buffer_proposal_is_consistent(api_client, db_session, monkeypatch):
    headers, plan_id = account(api_client, db_session, shopping=(2500,))
    ai(monkeypatch, PHONE_SUGGESTION, tips=["Cut subscriptions by AED 50."])
    plan = propose(api_client, headers, plan_id)
    # Food is already over budget with no reliable forecast: nothing realistic to avoid there.
    # Subscriptions' 100 can be limited to 50.
    assert [(change["category"], change["limit"], change["avoided"]) for change in plan["changes"]] == [("Subscriptions", 50.0, 50.0)]
    assert plan["spending_gap"] == pytest.approx(STILL_NEEDED - 300, abs=0.01)
    assert plan["remaining_shortfall"] == pytest.approx(STILL_NEEDED - 300 - 50, abs=0.01) and plan["covers"] is False
    assert plan["buffer"] == 300 and plan["daily_allowance"] == 20
    # No free text that could contradict the checked limits; no AI numbers
    assert plan["tips"] == [] and all(change["reason"] == "" or not any(c.isdigit() for c in change["reason"]) for change in plan["changes"])


def test_level_three_recovery_has_no_contradicting_text(api_client, db_session, monkeypatch):
    headers, plan_id = account(api_client, db_session, shopping=(150, 150, 150, 150, 2500))
    ai(monkeypatch, [], tips=["Cut subscriptions by AED 50."])
    plan = propose(api_client, headers, plan_id)
    # No limits suggested: no tips or notes recommending cuts either
    assert plan["changes"] == [] and plan["tips"] == [] and plan["notes"] == []
    assert plan["current_shortfall"] == 300 and plan["potential_reduction"] == 0 and plan["options"]
