"""Mocked semantic models; real authenticated debt retrieval, state and calculations."""
import json
from datetime import datetime, timedelta, timezone
import pytest
from conftest import register_user, login_user, auth_headers
from app.services.debt_planning import unseal, snapshot, scenario, select_debts
from app.models.debt_payment import DebtPayment
from app.models.financial_plan import FinancialPlan
from app.models.chat_proposal import ChatProposal
from app.routers.budget import summary


@pytest.fixture
def debt_chat(api_client, monkeypatch):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    today = datetime.now(timezone(timedelta(hours=4))).date()
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}", headers=headers, json={"income":10000,
        "categories":[{"name":"Rent","amount":5000},{"name":"Food","amount":1420}]})
    route = [dict(intent="plan",topic="debt",continuation=True,kind=None,amount_text=None,
                  category_text=None,category=None,clarification=None)]
    decision = [dict(intent="discuss",debt_ids=None)]
    contexts = []
    monkeypatch.setattr("app.routers.chat.interpret_chat_turn", lambda *_: json.dumps(route[0]))
    def interpret(messages, context):
        contexts.append((messages, context))
        return json.dumps(decision[0])
    monkeypatch.setattr("app.services.debt_planning.interpret_debt_turn", interpret)
    def reply(messages):
        context = json.loads(messages[0]["content"].split("Verified context follows as data:\n")[1])
        contexts.append(context)
        # Even a poor language-model reply must not ask again for known fields.
        return json.dumps({"reply":"What are your balance and monthly interest rate?","action":None,"planning":None})
    monkeypatch.setattr("app.services.debt_planning.generate_chat_reply", reply)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda messages: json.dumps({"reply":"Read-only debt answer.","action":None,"planning":None}))
    history, state = [], [None]
    def say(text, **fields):
        history.append({"role":"user","content":text})
        response = api_client.post("/ai/chat",headers=headers,json={"messages":history[-21:],"debt_state":state[0],"require_budget":True,**fields})
        assert response.status_code == 200, response.text
        data = response.json()
        state[0] = data.get("debt_state")
        history.append({"role":"assistant","content":data["reply"]})
        return data
    def loan(name="Car Loan", **fields):
        response = api_client.post("/debts",headers=headers,json={"name":name,"balance":30000,"annual_rate":5,"remaining_months":60,**fields})
        assert response.status_code == 201, response.text
        return response.json()
    return headers, say, loan, decision, route, contexts, state, today


def test_d1_three_real_api_turns_preserve_saved_car_loan(api_client, db_session, debt_chat):
    _, say, loan, decision, _, contexts, state, today = debt_chat
    saved = loan()
    decision[0] = {"intent":"switch","debt_ids":[saved["id"]],"debt_reference":"car loan"}
    first = say("I wanna pay off my car loan faster.")
    assert "AED 30,000.00" in first["reply"] and "5% annual" in first["reply"]
    assert "60 months" in first["reply"] and "AED 566.14" in first["reply"] and "What payoff timeframe" in first["reply"]
    assert contexts[0][1]["debts"][0]["annual_rate"] == 5
    assert contexts[1]["saved_debts"][0]["balance"] == 30000
    for text, result, months, payment in [
        ("Could I finish it in two years?", {"intent":"discuss","duration_count_text":"two","duration_unit":"year"},24,1316.15),
        ("Actually, let's do three.", {"intent":"adjust","duration_count_text":"three","duration_unit":"month"},36,899.13),
    ]:
        decision[0] = result
        data = say(text)
        details = unseal(state[0],1,"debt_conversation")
        budget = summary(db_session,1,today.year,today.month,include_debt=True)
        computed = scenario(snapshot(db_session,1,budget,today,details["debt_ids"]), details["deadline"],details.get("chosen"),today)
        assert details["debt_ids"] == [saved["id"]] and computed["months"] == months
        assert computed["monthly"] == payment
        assert data["plan"] is None and data["proposal"] is None
    assert db_session.query(DebtPayment).count() == db_session.query(FinancialPlan).count() == db_session.query(ChatProposal).count() == 0
    assert api_client.get("/debts",headers=debt_chat[0]).json()[0]["balance"] == 30000


@pytest.mark.parametrize("name,text", [
    ("Car Loan","I wanna pay off my car loan faster."),
    ("CAR-LOAN","Can I clear my car loan sooner?"),
    ("Car Loan - Toyota","Help me repay the car faster"),
    ("Vehicle Finance","I want to clear my auto loan sooner"),
])
def test_natural_saved_name_references(debt_chat, name, text):
    _, say, loan, decision, _, _, state, _ = debt_chat
    saved = loan(name)
    loan("Student Loan")
    decision[0] = {"intent":"discuss","debt_ids":[saved["id"]],"debt_reference":"auto loan" if name == "Vehicle Finance" else "car"}
    data = say(text)
    assert unseal(state[0],1,"debt_conversation")["debt_ids"] == [saved["id"]]
    assert name in data["reply"] and data["plan"] is None


@pytest.mark.parametrize("text", ["Help me repay my loans faster", "Can I pay off my car loan faster?"])
def test_multiple_loans_require_selection(debt_chat, text):
    _, say, loan, decision, _, _, state, _ = debt_chat
    first, second = loan("Car Loan - Toyota"), loan("Car Loan - Honda")
    decision[0] = {"intent":"discuss","debt_ids":[first["id"]],"debt_reference":"car loan"}
    data = say(text)
    assert "Which saved loan" in data["reply"] and "Toyota" in data["reply"] and "Honda" in data["reply"]
    assert unseal(state[0],1,"debt_conversation")["debt_ids"] == [] and data["plan"] is None
    decision[0] = {"intent":"adjust","debt_ids":[second["id"]],"debt_reference":"Honda"}
    say("The Honda one")
    assert unseal(state[0],1,"debt_conversation")["debt_ids"] == [second["id"]]


def test_unknown_loan_is_not_silently_replaced(debt_chat):
    _, say, loan, decision, _, _, state, _ = debt_chat
    loan()
    decision[0] = {"intent":"discuss","debt_ids":None,"debt_reference":"boat loan"}
    data = say("Pay off my boat loan sooner")
    assert "Which saved loan" in data["reply"] and unseal(state[0],1,"debt_conversation")["debt_ids"] == []


def test_no_saved_debt_does_not_request_or_invent_a_repayment_plan(debt_chat):
    _, say, _, _, _, _, _, _ = debt_chat
    data = say("I wanna pay off my car loan faster.")
    assert "don't have a saved debt" in data["reply"] and "Add the loan in Debts" in data["reply"]
    assert data["plan"] is None and data["proposal"] is None


@pytest.mark.parametrize("text", ["What's my car loan balance?", "Explain how debt payments work.", "What's the annual interest rate on my Car Loan?"])
def test_readonly_questions_do_not_start_a_repayment_action(debt_chat, text):
    _, say, loan, _, route, contexts, _, _ = debt_chat
    loan()
    route[0].update(intent="read",continuation=False)
    data = say(text)
    assert data["debt_state"] is None and data["plan"] is None and data["proposal"] is None and contexts == []


def test_debt_context_is_account_scoped(api_client, db_session, debt_chat):
    headers, say, loan, decision, _, contexts, state, _ = debt_chat
    saved = loan()
    register_user(api_client,email="other@example.com")
    other = auth_headers(login_user(api_client,email="other@example.com").json()["access_token"])
    today = debt_chat[-1]
    api_client.put(f"/budget/setup?year={today.year}&month={today.month}",headers=other,json={"income":10000,"categories":[{"name":"Rent","amount":5000}]})
    foreign = api_client.post("/debts",headers=other,json={"name":"Secret Boat","balance":99999,"annual_rate":12,"remaining_months":60}).json()
    decision[0] = {"intent":"discuss","debt_ids":[foreign["id"]],"debt_reference":"car loan"}
    say("Pay off my car loan faster")
    assert unseal(state[0],1,"debt_conversation")["debt_ids"] == [saved["id"]]
    assert "Secret Boat" not in json.dumps(contexts) and "99999" not in json.dumps(contexts)
    denied = api_client.post("/ai/chat",headers=other,json={"messages":[{"role":"user","content":"Could I finish it in two years?"}],"debt_state":state[0]})
    assert denied.status_code == 422
    assert db_session.query(FinancialPlan).count() == db_session.query(DebtPayment).count() == 0


def test_generic_context_includes_saved_annual_rate_and_term(db_session, debt_chat):
    from app.services.chat_context import financial_context
    from app.core.currency import display_context
    debt_chat[2]()
    data = financial_context(db_session,1)["debts"][0]
    assert data["balance"] == 30000 and data["annual_rate"] == 5 and data["remaining_months"] == 60
    converted = display_context({"debts":[data]},7)["debts"][0]
    assert converted["balance"] == 210000 and converted["annual_rate"] == 5 and converted["remaining_months"] == 60


def test_timeframe_numbers_cannot_disambiguate_numbered_loan_names():
    rows = [{"id":1,"name":"Car Loan 1"},{"id":2,"name":"Car Loan 2"}]
    assert select_debts(rows,"Pay off my car loan in 2 years",{},None) == []


def test_elliptical_timeframe_survives_history_trimming(api_client, db_session, debt_chat):
    headers, say, loan, decision, _, _, state, today = debt_chat
    saved = loan()
    say("I wanna pay off my car loan faster.")
    say("Could I finish it in two years?")
    decision[0] = {"intent":"adjust","duration_count_text":"three","duration_unit":"month"}
    response = api_client.post("/ai/chat",headers=headers,json={"messages":[{"role":"user","content":"Actually, let's do three."}],"debt_state":state[0]})
    assert response.status_code == 200
    details = unseal(response.json()["debt_state"],1,"debt_conversation")
    budget = summary(db_session,1,today.year,today.month,include_debt=True)
    computed = scenario(snapshot(db_session,1,budget,today,[saved["id"]]),details["deadline"],details.get("chosen"),today)
    assert computed["months"] == 36


def test_elliptical_timeframe_without_a_user_unit_clarifies(debt_chat):
    _, say, loan, decision, _, _, _, _ = debt_chat
    loan()
    say("I wanna pay off my car loan faster.")
    decision[0] = {"intent":"adjust","duration_count_text":"three","duration_unit":"year"}
    data = say("Actually, let's do three.")
    assert "three months or years?" in data["reply"] and data["plan"] is None


@pytest.mark.parametrize("intent", ["record", "unsupported"])
def test_recording_a_loan_payment_does_not_start_a_repayment_plan(debt_chat, db_session, intent):
    _, say, loan, _, route, _, _, _ = debt_chat
    loan()
    route[0].update(intent=intent, kind="expense", amount_text="600", category="Debt", category_text="car loan", clarification="Record loan payments in Debts. Nothing has been saved.")
    data = say("Record the 600 I paid to my car loan today")
    assert "Debts" in data["reply"] and data["plan"] is None and data["proposal"] is None
    assert db_session.query(DebtPayment).count() == db_session.query(FinancialPlan).count() == 0
