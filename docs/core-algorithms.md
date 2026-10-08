
# PocketPilot Core Algorithms

This document explains the financial calculations and recommendation logic currently implemented in PocketPilot.

## 1. Spending Analysis

File: `Backend/app/algorithms/spending_analysis.py`

### 1.1 Total Spending

Calculates the sum of transaction amounts.

Formula:

Total Spending = Sum of all transaction amounts

### 1.2 Spending by Category

Groups transactions by category and calculates the total spending for each category.

Example:

- Food: AED 750
- Transport: AED 200
- Shopping: AED 500

### 1.3 Category Percentages

Calculates the percentage of total spending represented by each category.

Formula:

Category Percentage = (Category Spending / Total Spending) × 100

### 1.4 Monthly Spending Comparison

Compares category spending between two months.

Formula:

Percentage Change = ((Current - Previous) / Previous) × 100

A positive value indicates increased spending.

A negative value indicates decreased spending.

Categories with zero previous-month spending are currently excluded from percentage-change calculations.

## 2. Recommendation Engine

File: `Backend/app/algorithms/recommendations.py`

The recommendation engine uses monthly spending changes to identify significant differences.

### Rules

| Condition | Result | Priority |
|---|---|---|
| Increase >= 20% | Spending increase recommendation | High |
| Decrease <= -20% | Spending decrease notification | Low |
| Between -20% and +20% | No recommendation | None |

The 20% threshold is a provisional development assumption that requires Finance team review.

Recommendations contain:

- Category
- Recommendation type
- Priority
- Percentage change
- Message

## 3. Database Integration

File: `Backend/app/database.py`

Transactions are stored in SQLite using SQLAlchemy.

The application retrieves transaction records and converts them into the format expected by the spending-analysis functions.

This allows the existing algorithms to operate on saved transaction data without duplicating their calculation logic.

## 4. AI Explanation System

Files:

- `Backend/app/ai/explanation.py`
- `Backend/app/ai/client.py`

The AI explanation system converts calculated financial recommendations into natural-language explanations.

The backend uses Qwen3 4B through Ollama's OpenAI-compatible API.

### Workflow

1. Retrieve saved transactions.
2. Calculate monthly spending changes.
3. Generate rule-based recommendations.
4. Prepare an AI prompt containing the verified calculations.
5. Send the prompt to Qwen3 4B.
6. Return the generated explanation.

### AI Safety Instructions

The AI model is instructed to:

- Use only supplied financial information.
- Avoid inventing amounts or percentages.
- Avoid unsupported assumptions.
- Avoid claiming to know why spending changed.
- Avoid making financial guarantees.

These instructions reduce risk but do not guarantee accuracy.

## 5. Current Limitations

- Financial amounts currently use floating-point representation.
- Categories are not automatically normalized.
- New categories without previous-month spending are excluded from percentage comparisons.
- AI-generated explanations are not independently validated.
- Budgeting and debt planning algorithms are not yet implemented.
