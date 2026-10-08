from app.algorithms.recommendations import (
    generate_spending_recommendations
)

from app.ai.explanation import (
    prepare_ai_explanation
)

from app.ai.client import (
    generate_ai_explanation
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

    explanation = generate_ai_explanation(prompt)

    print("\nCategory:", recommendation["category"])
    print("AI Explanation:", explanation)