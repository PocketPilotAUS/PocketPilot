def generate_spending_recommendations(monthly_changes):
    recommendations = []

    for category, percentage_change in monthly_changes.items():

        if percentage_change >= 20:
            recommendations.append({
                "category": category,
                "type": "spending_increase",
                "priority": "high",
                "percentage_change": percentage_change,
                "message": (
                    f"Your {category.lower()} spending increased by "
                    f"{percentage_change}% compared with last month. "
                    f"Consider reviewing these expenses."
                )
            })

        elif percentage_change <= -20:
            recommendations.append({
                "category": category,
                "type": "spending_decrease",
                "priority": "low",
                "percentage_change": percentage_change,
                "message": (
                    f"Your {category.lower()} spending decreased by "
                    f"{abs(percentage_change)}% compared with last month."
                )
            })

    return recommendations

if __name__ == "__main__":
    from spending_analysis import (
        compare_monthly_spending
    )

    last_month_transactions = [
        {"category": "Food", "amount": 500},
        {"category": "Transport", "amount": 250},
        {"category": "Shopping", "amount": 300},
        {"category": "Entertainment", "amount": 200},
    ]

    current_month_transactions = [
        {"category": "Food", "amount": 750},
        {"category": "Transport", "amount": 200},
        {"category": "Shopping", "amount": 500},
        {"category": "Entertainment", "amount": 150},
    ]

    monthly_changes = compare_monthly_spending(
        current_month_transactions,
        last_month_transactions
    )

    recommendations = generate_spending_recommendations(
        monthly_changes
    )

    print("\nPocketPilot Recommendations:\n")

    for recommendation in recommendations:
        print(recommendation["message"])