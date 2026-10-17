import json
from datetime import date, datetime, timedelta, timezone
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.transaction import Transaction
from app.models.financial_plan import FinancialPlan
from app.models.chat_proposal import ChatProposal
from app.models.income import MonthlyIncome
from app.services.chat_records import normalize_action
from app.routers.chat import Message


@pytest.fixture
def recording(api_client, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 10, 17, 12, tzinfo=timezone(timedelta(hours=4)))
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)
    monkeypatch.setattr("app.routers.chat.datetime", Clock)
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    assert api_client.put("/budget/setup?year=2026&month=10", headers=headers, json={
        "income": 10000, "categories": [{"name": "Food", "amount": 1000}]}).status_code == 200
    return headers


def request(client, monkeypatch, headers, text, action, **extra):
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: json.dumps({
        "reply": "Expense recorded on October 31. Your spending is now AED 250.",
        "action": action, "planning": {"expenses": {"Food": 50}, "goal": "Invented"},
    }))
    response = client.post("/ai/chat", headers=headers, json={
        "messages": [{"role": "user", "content": text}], "require_budget": True, **extra})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("phrase,expected", [
    ("today", "2026-10-17"), ("yesterday", "2026-10-16"), ("tomorrow", "2026-10-18"),
    ("on 2026-09-30", "2026-09-30"), ("on October 5, 2026", "2026-10-05"),
    ("on 5 October 2026", "2026-10-05"), ("on Oct 5, 2026", "2026-10-05"),
])
@pytest.mark.parametrize("operation", ["confirm", "dismiss"])
def test_dates_pending_wording_and_confirmation(api_client, monkeypatch, recording, db_session, phrase, expected, operation):
    result = request(api_client, monkeypatch, recording, "Record an expense of AED 50 for Food " + phrase,
        {"kind": "expense", "amount": 50, "category": "Food", "date": "2026-10-31"})
    proposal = result["proposal"]
    assert proposal["date"] == expected and proposal["status"] == "pending"
    assert result["reply"].startswith("Ready to record AED 50.00 for Food")
    assert "Confirm to save" in result["reply"]
    assert "recorded" not in result["reply"] and "250" not in result["reply"]
    assert result["plan"] is None and result["budget_goal"] is None
    stored = json.loads(db_session.query(ChatProposal).one().payload)
    assert stored["date"] == expected
    assert db_session.query(Transaction).count() == 0
    # Cross-account confirmation cannot apply this user's proposal.
    register_user(api_client, email="bob@example.com")
    bob = auth_headers(login_user(api_client, email="bob@example.com").json()["access_token"])
    path = "/ai/proposals/" + proposal["id"] + "/" + operation
    assert api_client.post(path, headers=bob).status_code == 404
    assert api_client.post(path, headers=recording).status_code == 200
    if operation == "confirm":
        row = db_session.query(Transaction).one()
        assert row.amount == 50 and row.date.isoformat() == expected
    else:
        assert db_session.query(Transaction).count() == 0


@pytest.mark.parametrize("phrase", ["", "last Friday", "on 10/11/2026", "today or yesterday",
    "on 2026-02-30", "today on 2026-10-31"])
def test_ambiguous_dates_never_create_proposals(api_client, monkeypatch, recording, db_session, phrase):
    result = request(api_client, monkeypatch, recording, "Record an expense of AED 50 for Food " + phrase,
        {"kind": "expense", "amount": 50, "category": "Food", "date": "2026-10-31"})
    assert result["proposal"] is None and "clarify" in result["reply"]
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("phrase,year,month", [
    ("this month", 2026, 10), ("last month", 2026, 9), ("next month", 2026, 11),
    ("for September 2025", 2025, 9), ("for 2025-09", 2025, 9), ("", 2026, 10),
])
@pytest.mark.parametrize("operation", ["confirm", "dismiss"])
def test_income_periods_and_confirmation(api_client, monkeypatch, recording, db_session, phrase, year, month, operation):
    result = request(api_client, monkeypatch, recording, "Set my income to AED 8000 " + phrase,
        {"kind": "income", "amount": 8000, "year": 2027, "month": 1})
    proposal = result["proposal"]
    assert (proposal["year"], proposal["month"]) == (year, month)
    assert "Ready to set" in result["reply"] and "Confirm to save" in result["reply"]
    assert "recorded" not in result["reply"]
    assert result["plan"] is None
    path = "/ai/proposals/" + proposal["id"] + "/" + operation
    assert api_client.post(path, headers=recording).status_code == 200
    row = db_session.query(MonthlyIncome).filter_by(year=year, month=month).first()
    if operation == "confirm":
        assert row.amount_cents == 800000
    elif (year, month) == (2026, 10):
        assert row.amount_cents == 1000000
    else:
        assert row is None


@pytest.mark.parametrize("carried_mode", [False, True])
def test_recording_preserves_goal_context_without_extracting_plan(api_client, monkeypatch, recording, db_session, carried_mode):
    from app.schemas.planning import CATEGORIES
    profile = {"income": 10000, "other_income": 0, "household_size": 1, "current_amount": 0,
        "expenses": dict.fromkeys(CATEGORIES, 0),
        "goal": "Vacation", "goal_kind": "savings", "target_amount": 5000, "deadline": "2090-01-01"}
    monkeypatch.setattr("app.routers.chat.extract_goal_facts", lambda _: pytest.fail("Recording must not extract a goal"))
    result = request(api_client, monkeypatch, recording, "Record an expense of AED 50 for Food today",
        {"kind": "expense", "amount": 50, "category": "Food", "date": "2026-10-31"},
        goal_planning=carried_mode, planning_profile=profile)
    assert result["proposal"]["date"] == "2026-10-17"
    assert result["plan"] is None and result["budget_goal"] is None
    assert result["planning_profile"]["goal"] == "Vacation"
    assert result["goal_planning"] == carried_mode
    assert db_session.query(FinancialPlan).count() == 0


@pytest.mark.parametrize("text", [
    "Edit my existing Food transaction to AED 50 today",
    "Delete an expense", "Update my expense to AED 50",
    "Record a savings contribution of AED 50 today",
    "Add AED 50 to my savings goal", "Record a contribution of AED 50",
    "Save AED 50 into my goal", "Add AED 50 to my goal today",
])
def test_unsupported_operations_do_not_call_model(api_client, monkeypatch, recording, db_session, text):
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: pytest.fail("Unsupported operation must not reach Ollama"))
    response = api_client.post("/ai/chat", headers=recording, json={
        "messages": [{"role": "user", "content": text}], "goal_planning": True})
    assert response.status_code == 200
    assert "cannot" in response.json()["reply"] and response.json()["proposal"] is None
    assert db_session.query(ChatProposal).count() == 0


def test_relative_boundaries_and_uae_midnight(monkeypatch, api_client, recording):
    raw = {"kind": "income", "amount": 8000}
    assert normalize_action(raw, [Message(role="user", content="Set income to 8000 last month")],
        date(2026, 1, 1))["year"] == 2025
    assert normalize_action({"kind": "expense", "amount": 50}, [
        Message(role="user", content="Record 50 for Food yesterday")], date(2026, 1, 1))["date"] == "2025-12-31"
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            instant = cls(2026, 10, 16, 21, tzinfo=timezone.utc)
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)
    monkeypatch.setattr("app.routers.chat.datetime", Clock)
    result = request(api_client, monkeypatch, recording, "Record an expense of AED 50 for Food today",
        {"kind": "expense", "amount": 50, "category": "Food", "date": "2026-10-16"})
    assert result["proposal"]["date"] == "2026-10-17"


def test_relative_date_does_not_require_a_model_date(api_client, monkeypatch, recording):
    result = request(api_client, monkeypatch, recording, "Record AED 50 for Food today",
        {"kind": "expense", "amount": 50, "category": "Food"})
    assert result["proposal"]["date"] == "2026-10-17"


def test_income_request_without_amount_must_clarify(api_client, monkeypatch, recording, db_session):
    result = request(api_client, monkeypatch, recording, "Set my income for this month",
        {"kind": "income", "amount": 8000, "year": 2027, "month": 1})
    assert result["proposal"] is None and "clarify" in result["reply"]
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("period", ["for September", "for this month or last month", "for 2026-13"])
def test_ambiguous_or_invalid_income_period(api_client, monkeypatch, recording, db_session, period):
    result = request(api_client, monkeypatch, recording, "Set my income to AED 8000 " + period,
        {"kind": "income", "amount": 8000, "year": 2027, "month": 1})
    assert result["proposal"] is None
    assert db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("answer,expected", [
    ("Which category did you pay?", None),
    ("Expense recorded. Your spending is now 250.", None),
    ("This is a test to ensure the system works correctly. The expected output is a JSON with action and planning set to null.", None),
])
def test_no_action_never_claims_success(api_client, monkeypatch, recording, db_session, answer, expected):
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: json.dumps({
        "reply": answer, "action": None, "planning": {"goal": "Unwanted"}}))
    response = api_client.post("/ai/chat", headers=recording, json={
        "messages": [{"role": "user", "content": "Record AED 50 today"}]})
    result = response.json()
    assert result["proposal"] is None and result["plan"] is None
    if expected:
        assert result["reply"] == expected
    else:
        assert "clarify" in result["reply"]
    assert db_session.query(ChatProposal).count() == 0


def test_mobile_date_clarification_followup(api_client, monkeypatch, recording):
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: json.dumps({
        "reply": "Saved on October 31.", "action": {"kind": "expense", "amount": 50,
            "category": "Food", "date": "2026-10-31"}, "planning": None}))
    response = api_client.post("/ai/chat", headers=recording, json={"messages": [
        {"role": "user", "content": "Record AED 50 for Food\n[Currency for untagged amounts in this message: AED]"},
        {"role": "assistant", "content": "When did you pay?"},
        {"role": "user", "content": "today\n[Currency for untagged amounts in this message: AED]"},
    ]})
    assert response.status_code == 200
    assert response.json()["proposal"]["date"] == "2026-10-17"


@pytest.mark.parametrize("text", [
    "Update my financial plan", "Adjust my financial plan expense targets",
    "Save more", "Save 5000 for a phone by February 2027",
])
def test_planning_intent_stays_separate(text):
    from app.services.chat_context import intent
    from app.services.chat_records import unsupported_operation
    assert intent([Message(role="user", content=text)]) == "plan"
    assert unsupported_operation(text) is None


def test_pending_vacation_then_recording_never_accepts_plan(api_client, monkeypatch, recording, db_session):
    from app.routers import planning
    from decimal import Decimal
    calls = []
    original = planning.persist_budget_goal
    def persist(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(planning, "persist_budget_goal", persist)
    monkeypatch.setattr("app.routers.chat.extract_goal_facts", lambda _: json.dumps({
        "goal": "Vacation", "goal_kind": "savings", "target_amount": 4500,
        "current_amount": 0, "deadline": "2027-08-31", "deadline_in_months": None}))
    output = {"reply": "Your vacation plan is already set and saved.", "action": None, "planning": None}
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: json.dumps(output))
    first_question = "Create a savings plan for a vacation costing AED 4,500 by August 2027."
    draft = api_client.post("/ai/chat", headers=recording, json={
        "messages": [{"role": "user", "content": first_question}], "require_budget": True}).json()
    plan = draft["plan"]
    assert plan["ready"] and "id" not in plan
    assert "draft Vacation" in draft["reply"] and "AED 4,500.00" in draft["reply"]
    assert "August 31, 2027" in draft["reply"] and "AED 409.10" in draft["reply"]
    assert plan["monthlyContribution"] == float((Decimal(4500) / 11).quantize(Decimal(".01"), rounding="ROUND_UP"))
    assert "already set" not in draft["reply"] and "Nothing has been saved" in draft["reply"]
    assert calls == [] and db_session.query(FinancialPlan).count() == 0
    payload = {
        "messages": [{"role": "user", "content": first_question},
            {"role": "assistant", "content": draft["reply"]},
            {"role": "user", "content": "Record an expense of AED 25 for Food today."}],
        "require_budget": True, "goal_planning": True,
        "planning_profile": draft["planning_profile"],
        "budget_draft_fingerprint": plan["draftFingerprint"], "budget_draft_status": "draft"}
    internal = "This is a test to ensure the system works correctly. The expected output is a JSON with action and planning set to null."
    output["reply"] = internal
    result = api_client.post("/ai/chat", headers=recording, json=payload).json()
    assert "clarify" in result["reply"] and internal not in result["reply"]
    assert result["proposal"] is None and result["plan"] is None
    assert result["planning_profile"]["goal"] == "Vacation"
    assert calls == [] and db_session.query(FinancialPlan).count() == 0
    output["action"] = {"kind": "expense", "amount": 25, "category": "Food", "date": "2026-10-31"}
    result = api_client.post("/ai/chat", headers=recording, json=payload).json()
    assert result["proposal"]["status"] == "pending" and result["proposal"]["date"] == "2026-10-17"
    assert result["reply"].startswith("Ready to record AED 25.00")
    assert result["plan"] is None and calls == []
    assert db_session.query(Transaction).count() == db_session.query(FinancialPlan).count() == 0
    accepted = api_client.post("/planning/budget-plans", headers=recording, json={
        "profile": plan["profile"], "choices": plan["budgetChoices"],
        "budget_fingerprint": plan["budgetFingerprint"], "request_key": plan["confirmationKey"]})
    assert accepted.status_code == 201, accepted.text
    assert len(calls) == 1 and accepted.json()["id"]
    assert db_session.query(FinancialPlan).count() == 1


@pytest.mark.parametrize("action", [None, {}, {"kind": "expense", "amount": "invalid"}])
def test_invalid_record_action_does_not_leak_commentary(api_client, monkeypatch, recording, db_session, action):
    internal = "The expected output is JSON with action and planning set to null."
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: json.dumps({
        "reply": internal, "action": action, "planning": None}))
    response = api_client.post("/ai/chat", headers=recording, json={
        "messages": [{"role": "user", "content": "Record an expense of AED 25 for Food today."}]})
    data = response.json()
    assert "clarify" in data["reply"] and internal not in data["reply"]
    assert data["proposal"] is None and db_session.query(ChatProposal).count() == 0


@pytest.mark.parametrize("text,amount,category,accepted", [
    ("Record an expense of AED 50 for Food on 2026-10-17", 50, "Food", True),
    ("Record an expense of AED 50 for Food on 2026-10-17", 2026, "Food", False),
    ("Record an expense of AED 50 for Food on 2026-10-17", 50, "Shopping", False),
    ("Record AED 50 for Food for 2 people today", 2, "Food", False),
    ("Record AED 50 for Food for 2 people today", 50, "Food", True),
    ("Record AED 50 or AED 25 for Food today", 50, "Food", False),
    ("Record 50 or 25 for Food today", 25, "Food", False),
    ("Record AED 50 for Food and Shopping today", 50, "Food", False),
    ("Record AED 50 for Food or Shopping today", 50, "Shopping", False),
    ("Record AED 50 today", 50, "Food", False),
    ('Record AED 50 for "Food" or "Shopping" today', 50, "Food", False),
    ('Record AED 50 for "School fees" today', 50, "School fees", True),
    ("I paid 50 for groceries today", 50, "Food", True),
    ("I paid AED 50 for transportation today", 50, "Transport", True),
    ("Record AED 50 for School fees today", 50, "School fees", True),
    ("Record AED 50 for School fees today", 50, "Shopping", False),
    ("I paid AED 3000 rent today", 3000, "Rent", True),
    ("I paid 50 yuan for Food today", 50, "Food", True),
    ("Record AED 50 for Food on October 17, 2026", 17, "Food", False),
    ("Record an expense for Food on 2026-10-17", 2026, "Food", False),
])
def test_requested_amount_and_category_validation(api_client, monkeypatch, recording, db_session, text, amount, category, accepted):
    result = request(api_client, monkeypatch, recording, text,
        {"kind": "expense", "amount": amount, "category": category, "date": "2026-10-17"})
    if accepted:
        assert result["proposal"]["status"] == "pending"
    else:
        assert result["proposal"] is None and "clarify" in result["reply"]
    assert db_session.query(ChatProposal).count() == int(accepted)
    assert db_session.query(Transaction).count() == 0
