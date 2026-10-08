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