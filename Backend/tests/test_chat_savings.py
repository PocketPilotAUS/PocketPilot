"""Mocked-model contracts: real budget calculations and conversation grounding."""
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from conftest import register_user, login_user, auth_headers
from app.models.financial_plan import FinancialPlan, PlanningProfile
from app.models.chat_proposal import ChatProposal


@pytest.fixture
def savings(api_client, monkeypatch):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    today = datetime.now(timezone(timedelta(hours=4))).date()
    assert api_client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers,
        json={"income":10000,"categories":[{"name":"Rent","amount":5000},{"name":"Food","amount":1420}]}).status_code == 200
    decision = [dict(intent="plan", topic="savings", continuation=False, kind=None,
        amount_text="1k", category_text=None, category=None, clarification=None, savings_operation="affordability")]
    generated = [dict(goal="iPhone", target_amount=1000, monthly_contribution=1000, deadline_in_months=1)]
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", lambda *_: json.dumps(decision[0]))
    monkeypatch.setattr("app.routers.chat.extract_goal_facts", lambda *_: json.dumps(generated[0]))
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda *_: json.dumps(dict(reply="Let's discuss your savings.", planning=generated[0], action=None)))
    def ask(text, history=(), **fields):
        response = api_client.post("/ai/chat", headers=headers, json={"messages":[*history,{"role":"user","content":text}], **fields})
        assert response.status_code == 200, response.text
        return response.json()
    return ask, decision, generated


@pytest.mark.parametrize("text,token,left", [
    ("Can I save 1k a month?","1k","2,580.00"),
    ("Could I put away 800 every month?","800","2,780.00"),
    ("Would saving 1,500 monthly be realistic?","1,500","2,080.00"),
])
def test_s3_affordability_has_verified_figures_and_no_plan(savings, db_session, text, token, left):
    ask, decision, _ = savings
    decision[0]["amount_text"] = token
    data = ask(text, planning_profile={"goal":"iPhone","target_amount":1000,"monthly_contribution":1000}, goal_planning=True)
    assert data["plan"] is None and data["proposal"] is None and data["planning_profile"] is None
    assert all(n in data["reply"] for n in ("10,000.00","6,420.00","3,580.00",left))
    assert "iPhone" not in data["reply"] and "additional obligations" in data["reply"]
    assert db_session.query(FinancialPlan).count() == 0 and db_session.query(ChatProposal).count() == 0


def test_unspecified_period_clarifies_then_retains_amount(savings):
    ask, decision, _ = savings
    decision[0]["amount_text"] = "2k"
    first = ask("Can I afford to save 2k?")
    assert "each month, or a one-time" in first["reply"] and first["plan"] is None
    # Live Ollama returned the correct amount but an incorrect continuation flag.
    decision[0]["continuation"] = False
    second = ask("Monthly", history=[{"role":"user","content":"Can I afford to save 2k?"},{"role":"assistant","content":first["reply"]}])
    assert "1,580.00" in second["reply"] and second["plan"] is None


def test_s1_real_three_turn_goal_adjustments(savings):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal", amount_text=None)
    history, profile = [], None
    for text, facts, monthly in [
        ("I wanna save 5k for a laptop.", {"goal":"Laptop","goal_kind":"savings","target_amount":5000}, None),
        ("Let's do 800 a month.", {"monthly_contribution":800}, 800),
        ("Actually make it 600 instead.", {"monthly_contribution":600}, 600),
    ]:
        generated[0] = facts
        decision[0]["continuation"] = bool(history)
        data = ask(text, history=history, planning_profile=profile)
        profile = data["planning_profile"]
        assert profile["goal"] == "Laptop" and Decimal(profile["target_amount"]) == 5000
        if monthly:
            assert data["plan"]["monthlyContribution"] == monthly and data["plan"]["targetAmount"] == 5000
        else:
            assert data["plan"] is None
        history.extend([{"role":"user","content":text},{"role":"assistant","content":data["reply"]}])


def test_s2_protected_rent_survives(savings):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal", amount_text=None)
    generated[0] = {"protected_categories":["Rent"]}
    data = ask("I want to save more, but don't change my rent.")
    assert data["plan"] is None and "Rent" in data["budget_goal"]["protected"]
    assert data["budget_goal"]["availableBefore"] == 3580


@pytest.mark.parametrize("facts", [
    {"goal":"iPhone","target_amount":1000,"monthly_contribution":1000},
    {"goal":"Laptop","target_amount":1000,"monthly_contribution":1000},
    {"goal":"Laptop","target_amount":9999,"monthly_contribution":1000,"deadline_in_months":1},
])
def test_model_misclassification_cannot_invent_a_saveable_goal(savings, facts):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal")
    generated[0] = facts
    data = ask("Can I save 1k a month?", goal_planning=True,
        planning_profile={"goal":"iPhone","target_amount":1000,"monthly_contribution":1000,"deadline":"2026-10-31"})
    assert data["plan"] is None
    assert not data["planning_profile"].get("goal") and not data["planning_profile"].get("target_amount")


def test_saved_profile_is_not_a_new_chat_goal(savings, db_session):
    ask, decision, generated = savings
    db_session.add(PlanningProfile(user_id=1,payload=json.dumps({"goal":"iPhone","target_amount":5000,"monthly_contribution":1000})))
    db_session.commit()
    decision[0].update(savings_operation="goal")
    generated[0] = {"monthly_contribution":1000}
    data = ask("Can I save 1k a month?")
    assert data["plan"] is None and not data["planning_profile"].get("goal")


@pytest.mark.parametrize("mode", ["goal", "affordability"])
def test_s2_semantic_protection_does_not_depend_on_reply_extraction(savings, mode):
    ask, decision, generated = savings
    decision[0].update(savings_operation=mode, amount_text=None, protected_categories=["Rent", "Food"])
    generated[0] = {}
    data = ask("I want to save more, but don't change my rent.")
    assert "3,580.00" in data["reply"] and "Rent unchanged" in data["reply"]
    assert data["budget_goal"]["protected"] == ["Rent"]
    assert data["plan"] is None


def test_invented_contribution_and_duration_cannot_complete_a_goal(savings):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal", amount_text=None)
    generated[0] = {"goal":"Laptop","target_amount":5000,"monthly_contribution":5000,"deadline_in_months":1,"deadline":"2090-01-01"}
    data = ask("I want to save 5k for a laptop")
    assert data["plan"] is None and data["planning_profile"]["monthly_contribution"] is None
    assert data["planning_profile"]["deadline"] is None


def test_savings_affordability_uses_currency_conversion(savings):
    ask, decision, _ = savings
    decision[0]["amount_text"] = "7k"
    data = ask("Could I save 7k monthly?", currency="CNY", aed_to_cny=7)
    assert "CNY 70,000.00" in data["reply"] and "CNY 18,060.00" in data["reply"]
    assert data["plan"] is None


def test_topic_switch_does_not_extract_previous_goal(savings):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal", continuation=False)
    generated[0] = {"goal":"Laptop","target_amount":5000,"monthly_contribution":1000}
    data = ask("Can I save 1k a month?", history=[{"role":"user","content":"I want to save 5000 for a Laptop"},
        {"role":"assistant","content":"How much monthly?"}], planning_profile={"goal":"Laptop","target_amount":5000})
    assert data["plan"] is None and not data["planning_profile"].get("goal")


def test_assistant_monthly_suggestion_is_not_user_consent(savings):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal", amount_text=None, continuation=True)
    generated[0] = {"monthly_contribution":5000}
    data = ask("I'm not sure", history=[{"role":"user","content":"I want to save 5k for a laptop"},
        {"role":"assistant","content":"Would 5000 monthly work?"}], planning_profile={"goal":"Laptop","target_amount":5000})
    assert data["plan"] is None and data["planning_profile"]["monthly_contribution"] is None


def test_incomplete_goal_reply_cannot_invent_monthly_arithmetic(savings, monkeypatch):
    ask, decision, generated = savings
    decision[0].update(savings_operation="goal", amount_text=None)
    generated[0] = {"goal":"Laptop","target_amount":5000}
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda *_: json.dumps({"reply":"You need 1420 a month for 4 months.","planning":None,"action":None}))
    data = ask("I wanna save 5k for a laptop.")
    assert "1,420" not in data["reply"] and "1420" not in data["reply"] and "4 months" not in data["reply"]
    assert "how much" in data["reply"] and data["plan"] is None
