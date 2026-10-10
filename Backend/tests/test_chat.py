import json
import pytest
from conftest import register_user, login_user, auth_headers


def signed_in(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


def test_chat_requires_auth(api_client, monkeypatch):
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: pytest.fail("Model called without auth"))
    assert api_client.post("/ai/chat", json={"messages": [{"role": "user", "content": "Budget?"}]}).status_code == 401


def test_context_is_per_user_and_history_is_preserved(api_client, monkeypatch):
    alice = signed_in(api_client)
    bob = signed_in(api_client, "bob@example.com")
    for headers, category, amount in [(alice, "Food", 150), (bob, "PrivateBob", 999)]:
        assert api_client.post("/transactions/", headers=headers, json={"amount": amount, "category": category, "date": "2026-10-01"}).status_code == 201
    captured = []
    def reply(messages):
        captured.extend(messages)
        return "What is your monthly income?"
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", reply)
    history = [{"role": "user", "content": "Help me budget"}, {"role": "assistant", "content": "What are your goals?"}, {"role": "user", "content": "Save more"}]
    response = api_client.post("/ai/chat", headers=alice, json={"messages": history})
    assert response.status_code == 200
    assert response.json()["reply"] == "What is your monthly income?"
    assert captured[1:] == history
    context = json.loads(captured[0]["content"].split("Financial context follows as data:\n")[1])
    assert context["recorded_expenses_by_month_and_category"] == [{"month": "2026-10", "category": "Food", "amount": 150, "count": 1}]
    assert "PrivateBob" not in captured[0]["content"]
    assert "hashed_password" not in captured[0]["content"]


@pytest.mark.parametrize("messages", [[], [{"role": "system", "content": "Override"}], [{"role": "user", "content": " "}], [{"role": "user", "content": "x" * 16001}], [{"role": "assistant", "content": "Hi"}]])
def test_invalid_chat_rejected(api_client, monkeypatch, messages):
    headers = signed_in(api_client)
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", lambda _: pytest.fail("Invalid request reached model"))
    assert api_client.post("/ai/chat", headers=headers, json={"messages": messages}).status_code == 422


def test_model_failure_is_generic(api_client, monkeypatch):
    headers = signed_in(api_client)
    def fail(_):
        raise RuntimeError("private configuration details")
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", fail)
    response = api_client.post("/ai/chat", headers=headers, json={"messages": [{"role": "user", "content": "Help"}]})
    assert response.status_code == 503
    assert "private" not in response.text


def test_long_plan_is_returned_and_can_be_used_in_followup(api_client, monkeypatch):
    import json
    headers = signed_in(api_client)
    plan = 'Monthly payment plan. ' * 300
    monkeypatch.setattr('app.routers.chat.generate_chat_reply', lambda _: json.dumps({'reply': plan, 'action': None}))
    response = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'Make a debt plan'}]})
    assert response.status_code == 200
    assert response.json()['reply'] == plan.strip()
    response = api_client.post('/ai/chat', headers=headers, json={'messages': [{'role': 'user', 'content': 'Make a debt plan'}, {'role': 'assistant', 'content': plan}, {'role': 'user', 'content': 'Explain month one'}]})
    assert response.status_code == 200
