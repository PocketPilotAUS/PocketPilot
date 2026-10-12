import json
import pytest
from conftest import register_user, login_user, auth_headers


URL = "?year=2026&month=10"
BODY = {"income": "5000.00", "categories": [{"name": "Food", "amount": "1000.00"}, {"name": " Gym ", "amount": "200.00"}, {"name": "家人", "amount": "100.00"}]}


def signed_in(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


def test_setup_required_and_custom_budget_persists(api_client):
    headers = signed_in(api_client)
    assert api_client.get("/budget/monthly" + URL, headers=headers).json()["ideal_budget"] is None
    assert api_client.put("/budget/income" + URL, headers=headers, json={"amount": 5000}).json()["ideal_budget"] is None
    saved = api_client.put("/budget/setup" + URL, headers=headers, json=BODY)
    assert saved.status_code == 200
    budget = saved.json()["ideal_budget"]
    assert budget["mode"] == "amounts"
    assert budget["planned_total"] == 1300
    assert budget["planned_remaining"] == 3700
    assert [(row["category"], row["target"]) for row in budget["allocations"]] == [("Food", 1000), ("Gym", 200), ("家人", 100)]
    assert api_client.get("/budget/monthly" + URL, headers=headers).json()["ideal_budget"] == budget
    assert api_client.get("/transactions/", headers=headers).json() == []
    assert api_client.get("/budget/monthly?year=2026&month=11", headers=headers).json()["ideal_budget"] is None


def test_custom_actuals_unbudgeted_costs_and_user_isolation(api_client):
    alice = signed_in(api_client)
    bob = signed_in(api_client, "bob@example.com")
    assert api_client.put("/budget/setup" + URL, json=BODY).status_code == 401
    api_client.put("/budget/setup" + URL, headers=alice, json=BODY)
    for category, amount in [("gym", 80), ("Car repairs", 50)]:
        api_client.post("/transactions/", headers=alice, json={"amount": amount, "category": category, "date": "2026-10-01"})
    summary = api_client.get("/budget/monthly" + URL, headers=alice).json()
    assert summary["spent"] == 130
    assert summary["ideal_budget"]["allocations"][1]["spent"] == 80
    assert summary["ideal_budget"]["unbudgeted"] == [{"category": "Car repairs", "spent": 50}]
    assert api_client.get("/budget/monthly" + URL, headers=bob).json()["ideal_budget"] is None
    assert api_client.get("/budget/monthly" + URL, headers=bob).json()["income"] is None


@pytest.mark.parametrize("categories", [[], [{"name": " ", "amount": 1}], [{"name": "Gym", "amount": -1}], [{"name": "Gym", "amount": "1.001"}], [{"name": "Gym", "amount": 1}, {"name": " gym ", "amount": 2}], [{"name": "x" * 41, "amount": 1}], [{"name": f"Category {i}", "amount": 1} for i in range(51)]])
def test_invalid_setup_rejected_without_changing_saved_data(api_client, categories):
    headers = signed_in(api_client)
    api_client.put("/budget/setup" + URL, headers=headers, json=BODY)
    response = api_client.put("/budget/setup" + URL, headers=headers, json={"income": 999, "categories": categories})
    assert response.status_code == 422
    summary = api_client.get("/budget/monthly" + URL, headers=headers).json()
    assert summary["income"] == 5000
    assert summary["ideal_budget"]["planned_total"] == 1300


def test_zero_income_and_infeasible_budget_are_explicit(api_client):
    headers = signed_in(api_client)
    result = api_client.put("/budget/setup" + URL, headers=headers, json={"income": 0, "categories": [{"name": "Gym", "amount": 100}]}).json()
    assert result["ideal_budget"]["planned_remaining"] == -100
    assert result["ideal_budget"]["allocations"][0]["target"] == 100


def test_ai_review_uses_saved_budget_and_cannot_write_actions(api_client, monkeypatch):
    headers = signed_in(api_client)
    api_client.put("/budget/setup" + URL, headers=headers, json=BODY)
    captured = []
    def generate(messages):
        captured.extend(messages)
        return json.dumps({"reply": "Review Gym costs and missing bills.", "action": {"kind": "expense", "amount": 99, "category": "Gym", "date": "2026-10-01"}, "planning": None})
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", generate)
    before = api_client.get("/budget/monthly" + URL, headers=headers).json()
    response = api_client.post("/ai/chat", headers=headers, json={"review_budget": {"year": 2026, "month": 10}, "messages": [{"role": "user", "content": "Review my budget"}]})
    assert response.status_code == 200
    assert response.json()["proposal"] is None
    assert response.json()["plan"] is None
    context = json.loads(captured[0]["content"].split("Financial context follows as data:\n")[1])
    assert context["saved_monthly_budget"]["budget"]["allocations"][1]["category"] == "Gym"
    assert context["saved_monthly_budget"]["income"] == 5000
    assert api_client.get("/budget/monthly" + URL, headers=headers).json() == before
    assert api_client.get("/transactions/", headers=headers).json() == []


def test_review_rejects_unsaved_budget(api_client, monkeypatch):
    headers = signed_in(api_client)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: pytest.fail("No budget should reach model"))
    assert api_client.post("/ai/chat", headers=headers, json={"review_budget": {"year": 2026, "month": 10}, "messages": [{"role": "user", "content": "Review budget"}]}).status_code == 422
