from app.ai.explanation import prepare_ai_explanation


def test_prompt_contains_financial_information():
    recommendation = {
        "category": "Food",
        "type": "spending_increase",
        "priority": "high",
        "percentage_change": 50.0,
        "message": "Food spending increased by 50%."
    }

    prompt = prepare_ai_explanation(recommendation)

    assert "Food" in prompt
    assert "50.0%" in prompt
    assert "Food spending increased by 50%." in prompt


def test_prompt_contains_safety_rules():
    recommendation = {
        "category": "Shopping",
        "type": "spending_increase",
        "priority": "high",
        "percentage_change": 25.0,
        "message": "Shopping spending increased by 25%."
    }

    prompt = prepare_ai_explanation(recommendation)

    assert "Do not invent" in prompt
    assert "Do not make assumptions" in prompt

def test_reasoning_is_not_returned():
    from app.ai.client import final_answer
    assert final_answer({"done": True, "message": {"thinking": "Private reasoning", "content": "Hello!"}}) == "Hello!"
    assert final_answer({"done": True, "message": {"content": "<think>Reasoning</think>Final answer"}}) == "Final answer"


def test_incomplete_answers_are_rejected():
    import pytest
    from app.ai.client import final_answer
    for data in [
        {"done": True, "message": {"thinking": "Reasoning", "content": ""}},
        {"done": True, "done_reason": "length", "message": {"content": "Partial"}},
        {"done": True, "message": {"content": "<think>Unfinished"}},
    ]:
        with pytest.raises(ValueError):
            final_answer(data)


def test_native_ollama_request_separates_thinking(monkeypatch):
    from app.ai import client
    calls = []
    def handle(request):
        import json
        calls.append((str(request.url), json.loads(request.content)))
        return client.httpx.Response(200, json={"done": True, "message": {"thinking": "Private", "content": "A reply"}})
    real_client = client.httpx.Client
    monkeypatch.setattr(client.httpx, "Client", lambda **kwargs: real_client(transport=client.httpx.MockTransport(handle), **kwargs))
    monkeypatch.setenv("OLLAMA_URL", "http://localhost:11434/v1")
    assert client.generate_chat_reply([{"role": "user", "content": "Budget?"}]) == "A reply"
    assert client.generate_ai_explanation("Explain spending") == "A reply"
    for url, body in calls:
        assert url == "http://localhost:11434/api/chat"
        assert body["think"] is True
        assert body["stream"] is False
