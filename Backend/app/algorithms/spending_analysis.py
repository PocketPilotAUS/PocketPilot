transactions = [
    {"category": "Food", "amount": 450},
    {"category": "Transport", "amount": 200},
    {"category": "Subscriptions", "amount": 100},
    {"category": "Shopping", "amount": 500},
    {"category": "Entertainment", "amount": 150},
    {"category": "Food", "amount": 300},
]

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

def calculate_total_spending(transactions):
    total = 0

    for transaction in transactions:
        total += transaction["amount"]

    return total


def calculate_category_spending(transactions):
    category_totals = {}

    for transaction in transactions:
        category = transaction["category"]
        amount = transaction["amount"]

        if category in category_totals:
            category_totals[category] += amount
        else:
            category_totals[category] = amount

    return category_totals

def calculate_category_percentages(transactions):
    total_spending = calculate_total_spending(transactions)
    category_spending = calculate_category_spending(transactions)

    percentages = {}

    for category, amount in category_spending.items():
        percentages[category] = round((amount / total_spending) * 100, 2)

    return percentages

def compare_monthly_spending(current_transactions, previous_transactions):
    current_spending = calculate_category_spending(current_transactions)
    previous_spending = calculate_category_spending(previous_transactions)

    changes = {}

    for category, current_amount in current_spending.items():
        previous_amount = previous_spending.get(category, 0)

        if previous_amount > 0:
            percentage_change = (
                (current_amount - previous_amount) / previous_amount
            ) * 100

            changes[category] = round(percentage_change, 2)

    return changes

total = calculate_total_spending(transactions)
categories = calculate_category_spending(transactions)
percentages = calculate_category_percentages(transactions)

if __name__ == "__main__":
    print(f"Total Spending: AED {total}")

    print("\nCategory Spending:")
    for category, amount in categories.items():
        print(f"{category}: AED {amount}")

    print("\nCategory Percentages:")
    for category, percentage in percentages.items():
        print(f"{category}: {percentage}%")

    monthly_changes = compare_monthly_spending(
        current_month_transactions,
        last_month_transactions
    )
    print("\nMonthly Spending Changes:")
    for category, percentage in monthly_changes.items():
        print(f"{category}: {percentage}%")
