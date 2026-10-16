"""Regression tests for Plans recommendations, using the real test account's data.

Account on 16 October 2026: income 10,000; budget Bills 500, Rent 3,000,
Subscriptions 100, Food 1,500, Transport 500; Rent from a recurring schedule;
Food 1,000 + 1,200, Transport 500, Bills 500; iPhone goal 5,000 by
28 February 2027 at 1,000 a month.
"""
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
BUDGET = {"Bills": 500, "Rent": 3000, "Subscriptions": 100, "Food": 1500, "Transport": 500}


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr("app.routers.planning.local_today", lambda: TODAY)
    monkeypatch.setattr("app.routers.recurring.today_local", lambda: TODAY)


def account(client, db, shopping=()):
    register_user(client)
    headers = auth_headers(login_user(client).json()["access_token"])
    client.put("/budget/setup?year=2026&month=10", headers=headers,
               json={"income": 10000, "categories": [{"name": name, "amount": amount} for name, amount in BUDGET.items()]})
    db.add(RecurringExpense(user_id=1, request_key=str(uuid4()), amount_cents=300000, category="Rent", day=16, next_date=TODAY, active=True))
    plan_id = str(uuid4())
    db.add(FinancialPlan(id=plan_id, user_id=1, payload=json.dumps({
        "kind": "savings", "title": "iPhone", "budgetGoalSource": True, "monthlyContribution": 1000,
        "targetAmount": 5000, "savedAmount": 0, "deadline": "2027-02-28", "months": 5})))
    for category, amount in [("Food", 1000), ("Transport", 500), ("Bills", 500), ("Food", 1200)] + [("Shopping", amount) for amount in shopping]:
        db.add(Transaction(user_id=1, amount=amount, category=category, date=TODAY))
    db.commit()
    return headers, plan_id


def ai(monkeypatch, changes, tips=()):
    calls = []
    def answer(context, instructions=None, mode="adjust"):
        calls.append((context, instructions, mode))
        return json.dumps({"changes": changes, "tips": list(tips)})
    monkeypatch.setattr("app.ai.client.generate_budget_adjustment", answer)
    return calls


def status(client, headers):
    return client.get("/planning/status", headers=headers).json()


def propose(client, headers, plan_id=None):
    return client.post("/planning/adjustments/proposal", headers=headers, json={"plan_id": plan_id} if plan_id else {}).json()


# What the AI suggested in the Level 2 phone test: Food "1,500 -> 2,200", and stopping Subscriptions
PHONE_SUGGESTION = [{"category": "Food", "limit": 2200, "reason": "Stop food spending."},
                    {"category": "Subscriptions", "limit": 0, "reason": "Cancel subscriptions for $100."}]


def test_level_two_525_shortfall_gets_realistic_limits(api_client, db_session, monkeypatch):
    headers, plan_id = account(api_client, db_session, shopping=(150, 150, 150, 150))
    before = status(api_client, headers)
    assert before["level"] == 2 and before["shortfall"] == 525
    calls = ai(monkeypatch, PHONE_SUGGESTION)
    plan = propose(api_client, headers, plan_id)
    food = next(change for change in plan["changes"] if change["category"] == "Food")
    # Food can't be held at the 2,200 already spent for 15 more days: at most half of the
    # 2,062.50 still expected is avoidable, so the limit is 3,231.25 with 1,031.25 left to spend
    assert food == {"category": "Food", "budget": 1500.0, "spent": 2200.0, "upcoming": 0.0, "forecast": 4262.5, "limit": 3231.25,
                    "remaining_allowance": 1031.25, "avoided": 1031.25, "budget_after": 1500.0, "reason": "Stop food spending."}
    # The budget is never raised: budget_after stays at the original 1,500
    subs = next(change for change in plan["changes"] if change["category"] == "Subscriptions")
    assert subs["limit"] == 50 and subs["avoided"] == 50 and subs["budget_after"] == 50 and "$" not in subs["reason"]
    assert plan["notes"] and calls[0][2] == "adjust" and calls[0][0]["goal_amount"] == 525
    # Labelled, consistent figures
    assert plan["current_shortfall"] == 0 and plan["forecast_shortfall"] == 525
    assert plan["potential_reduction"] == 1081.25 and plan["remaining_shortfall"] == 0 and plan["covers"] is True
    assert plan["affordability"]["left_after_spending"] == 475 + 1081.25
    assert plan["options"] == [] and "half" in plan["assumption"]


def test_accepting_limits_never_raises_budgets_or_touches_transactions(api_client, db_session, monkeypatch):
    headers, _ = account(api_client, db_session, shopping=(150, 150, 150, 150))
    ai(monkeypatch, PHONE_SUGGESTION)
    plan = propose(api_client, headers)
    body = {"fingerprint": plan["fingerprint"], "request_key": str(uuid4()),
            "changes": [{"category": change["category"], "limit": change["limit"]} for change in plan["changes"]]}
    accepted = api_client.post("/planning/adjustments/accept", headers=headers, json=body).json()
    # Food stays visibly 700 over its unchanged 1,500 budget; Subscriptions is lowered to its 50 limit
    budget = api_client.get("/budget/monthly?year=2026&month=10", headers=headers).json()
    targets = {row["category"]: row["target"] for row in budget["ideal_budget"]["allocations"]}
    assert targets == {"Bills": 500, "Rent": 3000, "Subscriptions": 50, "Food": 1500, "Transport": 500}
    assert accepted["over_budget"] == [{"category": "Food", "budget": 1500.0, "spent": 2200.0, "over": 700.0}]
    # The forecast now assumes the limits are kept, so the goal is no longer at risk
    food = next(row for row in accepted["categories"] if row["category"] == "Food")
    assert food["forecast"] == 3231.25 and food["method"] == "adjusted" and accepted["level"] == 1
    history = {change["category"]: change for change in accepted["adjustments"][0]["changes"]}
    assert history["Food"] == {"category": "Food", "current": 1500.0, "proposed": 1500.0, "limit": 3231.25, "avoided": 1031.25}
    assert budget["spent"] == 6800 and db_session.query(Transaction).count() == 9
    # Persisted: a fresh read gives the same state; the same tap again changes nothing
    assert status(api_client, headers)["fingerprint"] == accepted["fingerprint"]
    assert len(api_client.post("/planning/adjustments/accept", headers=headers, json=body).json()["adjustments"]) == 1


def test_invalid_or_stale_limits_cannot_be_accepted(api_client, db_session, monkeypatch):
    headers, _ = account(api_client, db_session, shopping=(150, 150, 150, 150))
    ai(monkeypatch, PHONE_SUGGESTION)
    plan = propose(api_client, headers)
    def accept(changes, fingerprint=plan["fingerprint"]):
        return api_client.post("/planning/adjustments/accept", headers=headers,
                               json={"fingerprint": fingerprint, "request_key": str(uuid4()), "changes": changes})
    assert accept([{"category": "Food", "limit": 2200}]).status_code == 422       # below the realistic limit
    assert accept([{"category": "Food", "limit": 5000}]).status_code == 422       # above projected spending
    assert accept([{"category": "Rent", "limit": 2000}]).status_code == 422       # fixed bill
    assert accept([{"category": "Holiday", "limit": 10}]).status_code == 422      # not a budget category
    db_session.add(Transaction(user_id=1, amount=20, category="Food", date=TODAY))
    db_session.commit()
    assert accept([{"category": "Food", "limit": 3231.25}]).status_code == 409    # spending changed since the proposal
    # Nothing was applied by any of these, and dismissing is client-side
    assert db_session.query(BudgetPlan).count() == 1 and status(api_client, headers)["adjustments"] == []


def test_level_three_300_shortfall_keeps_shortfalls_separate_and_offers_plan_options(api_client, db_session, monkeypatch):
    headers, plan_id = account(api_client, db_session, shopping=(150, 150, 150, 150, 2500))
    before = status(api_client, headers)
    assert before["level"] == 3 and before["available_committed"] == 700 and before["shortfall"] == 300
    calls = ai(monkeypatch, PHONE_SUGGESTION)
    plan = propose(api_client, headers, plan_id)
    assert calls[0][2] == "recovery" and plan["mode"] == "recovery"
    # A: from recorded spending; B: from projected spending; C: avoidable; D: what is left after C
    assert plan["current_shortfall"] == 300
    assert plan["forecast_shortfall"] == 3025
    assert plan["potential_reduction"] == 1081.25
    assert plan["remaining_shortfall"] == 3025 - 1081.25 and plan["remaining_shortfall"] >= plan["current_shortfall"]
    assert plan["covers"] is False and plan["max_this_month"] == 0
    # Options for the iPhone goal (5,000 left, 1,000 a month, deadline February 2027 = 5 months incl. October)
    assert plan["options"] == [
        {"kind": "catch_up", "this_month": 0.0, "deadline": "2027-02-28", "months": 4, "monthly": 1250.0},
        {"kind": "extend", "this_month": 0.0, "monthly": 1000.0, "deadline": "2027-03-31", "months": 6, "plan_monthly": 833.34}]
    # The plan editor's own calculation for the suggested date gives the same monthly amount
    from app.services.budget_goals import draft_plan
    budget = {"income": 10000, "year": 2026, "month": 10, "ideal_budget": {"allocations": [{"category": name, "target": amount} for name, amount in BUDGET.items()]}}
    assert draft_plan({"goal": "iPhone", "goal_kind": "savings", "target_amount": 5000, "deadline": "2027-03-31"}, budget, TODAY)["monthlyContribution"] == 833.34
    # Nothing about the goal changed
    assert json.loads(db_session.query(FinancialPlan).first().payload)["monthlyContribution"] == 1000


def test_level_one_is_unchanged(api_client, db_session, monkeypatch):
    headers, _ = account(api_client, db_session)
    data = status(api_client, headers)
    assert data["level"] == 1 and data["available_projected"] == 3700
    ai(monkeypatch, PHONE_SUGGESTION, tips=["Plan $50 meals."])
    review = propose(api_client, headers)
    assert review["mode"] == "advice" and review["changes"] == [] and review["tips"] == ["Plan AED 50 meals."]
    assert review["affordability"]["left_after_savings"] == 2700


def test_chat_shows_amounts_in_aed(api_client, db_session, monkeypatch):
    headers, _ = account(api_client, db_session)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda messages: json.dumps({"reply": "Food is $2,200.00 of $1,500.00.", "action": None, "planning": None}))
    reply = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": "How is my food spending?"}]}).json()["reply"]
    assert reply == "Food is AED 2,200.00 of AED 1,500.00."
