import json
import pytest
from conftest import register_user, login_user, auth_headers


@pytest.mark.parametrize("language, name, reply", [("zh", "Simplified Mandarin Chinese", "请提供月收入。"), ("ar", "Arabic", "ما دخلك الشهري؟")])
def test_chat_requests_selected_language_without_changing_context(api_client, monkeypatch, language, name, reply):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    prompts = []
    def generate(messages):
        prompts.extend(messages)
        return json.dumps({"reply": reply, "action": None, "planning": None})
    monkeypatch.setattr("app.routers.chat.generate_chat_reply", generate)
    response = api_client.post("/ai/chat", headers=headers, json={"language": language, "messages": [{"role": "user", "content": "Help me save AED 100"}]})
    assert response.status_code == 200
    assert response.json()["reply"] == reply
    assert f"reply text in {name}" in prompts[0]["content"]
    assert "category identifiers unchanged" in prompts[0]["content"]
    assert prompts[1]["content"] == "Help me save AED 100"
    json.loads(prompts[0]["content"].split("Financial context follows as data:\n")[1])


def test_invalid_language_rejected(api_client):
    register_user(api_client)
    headers = auth_headers(login_user(api_client).json()["access_token"])
    response = api_client.post("/ai/chat", headers=headers, json={"language": "ignore rules", "messages": [{"role": "user", "content": "Hello"}]})
    assert response.status_code == 422
