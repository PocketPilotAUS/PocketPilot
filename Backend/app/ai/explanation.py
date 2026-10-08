def prepare_ai_explanation(recommendation):
    category = recommendation["category"]
    percentage = recommendation["percentage_change"]
    message = recommendation["message"]

    prompt = f"""
You are PocketPilot, a personal finance assistant.

Explain the following spending information to the user
in a friendly, clear, and helpful way.

Verified financial information:
- Spending category: {category}
- Percentage change: {percentage}%
- Recommendation: {message}

Rules:
1. Only use the financial information provided.
2. Do not invent amounts, balances, or percentages.
3. Do not make assumptions about the user's income.
4. Keep the explanation short and understandable.
5. Suggest practical actions without making guarantees.
6. Do not claim to know why spending changed.

Generate a short explanation.
"""

    return prompt

if __name__ == "__main__":
    from app.algorithms.recommendations import (
        generate_spending_recommendations
    )

    monthly_changes = {
        "Food": 50.0,
        "Transport": -20.0
    }

    recommendations = generate_spending_recommendations(
        monthly_changes
    )

    for recommendation in recommendations:
        prompt = prepare_ai_explanation(recommendation)

        print("\nAI Explanation Prompt:\n")
        print(prompt)