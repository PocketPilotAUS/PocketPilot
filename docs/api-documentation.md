
# PocketPilot API Documentation

## Overview

PocketPilot uses FastAPI to provide transaction management, spending analysis, financial recommendations, and AI-generated explanations.

Base URL during local development:

http://127.0.0.1:8000

Interactive documentation:

http://127.0.0.1:8000/docs

## 1. Backend Status

**GET /**

Returns a message confirming that the backend is running.

Example response:

```json
{
  "message": "PocketPilot API is running"
}
```

## 2. Create Transaction

**POST /transactions/**

Creates a transaction and stores it in SQLite.

Example request:

```json
{
  "amount": 45.5,
  "category": "Food",
  "description": "Lunch",
  "date": "2026-10-08"
}
```

Successful response: HTTP 201.

Invalid transaction data returns HTTP 422.

## 3. Retrieve Transactions

**GET /transactions/**

Returns all saved transactions.

Example response:

```json
[
  {
    "amount": 45.5,
    "category": "Food",
    "description": "Lunch",
    "date": "2026-10-08",
    "id": 1
  }
]
```

## 4. Delete Transaction

**DELETE /transactions/{transaction_id}**

Deletes the transaction identified by its ID.

Successful response: HTTP 200.

Example:

```json
{
  "message": "Transaction deleted successfully"
}
```

If the transaction does not exist, the API returns HTTP 404.

## 5. Spending Summary

**GET /spending/summary**

Calculates total spending, spending by category, and category percentages using stored transactions.

Example response:

```json
{
  "total_spending": 300,
  "category_spending": {
    "Food": 250,
    "Transport": 50
  },
  "category_percentages": {
    "Food": 83.33,
    "Transport": 16.67
  }
}
```

The current endpoint includes all saved transactions.

## 6. Monthly Spending Comparison

**GET /spending/compare**

Query parameters:

- `year`: Selected year.
- `month`: Selected month (1–12).

Example:

`/spending/compare?year=2026&month=10`

Example response:

```json
{
  "year": 2026,
  "month": 10,
  "previous_year": 2026,
  "previous_month": 9,
  "current_spending": {
    "Food": 750
  },
  "previous_spending": {
    "Food": 500
  },
  "percentage_changes": {
    "Food": 50.0
  }
}
```

## 7. Financial Recommendations

**GET /recommendations/**

Query parameters:

- `year`
- `month`

Example:

`/recommendations/?year=2026&month=10`

Returns rule-based recommendations based on monthly spending changes.

Example response:

```json
{
  "year": 2026,
  "month": 10,
  "recommendations": [
    {
      "category": "Food",
      "type": "spending_increase",
      "priority": "high",
      "percentage_change": 50.0,
      "message": "Your food spending increased by 50.0% compared with last month. Consider reviewing these expenses."
    }
  ]
}
```

## 8. AI Recommendations

**GET /recommendations/ai**

Query parameters:

- `year`
- `month`

Example:

`/recommendations/ai?year=2026&month=10`

Generates AI explanations of financial recommendations.

Example response:

```json
{
  "year": 2026,
  "month": 10,
  "ai_recommendations": [
    {
      "category": "Food",
      "priority": "high",
      "percentage_change": 50.0,
      "recommendation": "Your food spending increased by 50.0% compared with last month. Consider reviewing these expenses.",
      "ai_explanation": "Your food spending increased compared with last month. Consider reviewing your recent food expenses."
    }
  ]
}
```

The AI-generated text may vary between requests.

If Ollama is unavailable, the endpoint returns HTTP 503.

## Current API Limitations

- No authentication or authorization.
- No user-specific transaction isolation.
- No transaction editing endpoint.
- No pagination for transaction retrieval.
- No income transaction support.
- No budgeting or debt planning endpoints.
- AI explanations are not automatically verified.

These endpoints are intended for local development and testing.
