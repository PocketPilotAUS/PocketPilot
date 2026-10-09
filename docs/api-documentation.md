
# PocketPilot API Documentation

## Overview

PocketPilot uses FastAPI to provide user accounts, transaction management, spending analysis, financial recommendations, and AI-generated explanations.

Every financial endpoint requires a logged-in user, and each user can only see and change their own data.

Base URL during local development:

http://127.0.0.1:8000

Interactive documentation:

http://127.0.0.1:8000/docs

To call protected endpoints from Swagger: log in with `POST /auth/login`, copy the `access_token`, click **Authorize**, and paste the token (without the word `Bearer`).

## Authentication

PocketPilot uses **JWT Bearer tokens**.

1. Register once with `POST /auth/register`.
2. Log in with `POST /auth/login` to receive an `access_token`.
3. Send the token on every protected request:

```http
Authorization: Bearer <access_token>
```

Tokens expire after `expires_in` seconds (30 minutes by default). After that, protected endpoints return **HTTP 401** and the user must log in again. There are no refresh tokens yet.

### Endpoint access

| Endpoint | Login required |
|---|---|
| `GET /` | No |
| `POST /auth/register`, `POST /auth/login` | No |
| `GET /auth/me` | Yes |
| All `/transactions/`, `/spending/` and `/recommendations/` endpoints | Yes |

### Data isolation

- A new transaction always belongs to the logged-in user. The owner is taken from the token, never from the request body.
- Lists, summaries, comparisons and recommendations only use the logged-in user's transactions.
- Asking for another user's transaction returns the same **HTTP 404** as a transaction that does not exist.
- Transactions created before user accounts existed have no owner. They stay in the database but are not visible to any user. See the README section on database migration.

### Error responses

Errors use FastAPI's standard format: `{"detail": ...}`.

| Status | Meaning |
|---|---|
| 401 | Missing, invalid, tampered or expired token, or incorrect email or password at login. The response includes a `WWW-Authenticate: Bearer` header. |
| 404 | Transaction not found (or it belongs to another user) |
| 409 | Email already registered |
| 422 | Invalid request data (`detail` lists each invalid field) |
| 503 | Server configuration problem (e.g. `JWT_SECRET_KEY` not set), or AI server unavailable |

Every authentication failure on a protected endpoint returns the same response:

```json
{
  "detail": "Could not validate credentials."
}
```

For `/auth/` endpoints, 422 responses never repeat the submitted values (so passwords are never echoed back).

## 1. Backend Status

**GET /**

Returns a message confirming that the backend is running. No login required.

Example response:

```json
{
  "message": "PocketPilot API is running"
}
```

## 2. Register

**POST /auth/register**

Creates a user account. No login required. This does **not** log the user in; call `POST /auth/login` next.

Example request:

```json
{
  "name": "Alice Smith",
  "email": "alice@example.com",
  "password": "correct-horse-1"
}
```

Rules:

| Field | Rules |
|---|---|
| `name` | 1–100 characters after trimming spaces; no control characters |
| `email` | Valid format (`name@domain.tld`, no spaces), up to 254 characters. Trimmed and stored in lowercase, so `Alice@Example.com` and `alice@example.com` are the same account. |
| `password` | 8–128 characters. Spaces are kept as typed. |

Any other field (for example `id` or `is_admin`) is rejected with HTTP 422.

Successful response: HTTP 201.

```json
{
  "id": 1,
  "name": "Alice Smith",
  "email": "alice@example.com",
  "created_at": "2026-10-09T12:02:51.945488Z"
}
```

`created_at` is in UTC. The password and its hash are never returned.

Errors:

- HTTP 409 if the email is already registered:

```json
{
  "detail": "An account with this email already exists."
}
```

- HTTP 422 for invalid fields, for example:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "password"],
      "msg": "String should have at least 8 characters",
      "ctx": {"min_length": 8}
    }
  ]
}
```

## 3. Log In

**POST /auth/login**

Checks the email and password and returns an access token. No login required. The email is case-insensitive; the password is case-sensitive.

Example request:

```json
{
  "email": "alice@example.com",
  "password": "correct-horse-1"
}
```

Successful response: HTTP 200.

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

`expires_in` is the token lifetime in seconds.

A wrong password and an unknown email return the same HTTP 401 response, so the API does not reveal which emails are registered:

```json
{
  "detail": "Incorrect email or password."
}
```

## 4. Current User

**GET /auth/me** (login required)

Returns the logged-in user's profile, in the same format as the register response.

```json
{
  "id": 1,
  "name": "Alice Smith",
  "email": "alice@example.com",
  "created_at": "2026-10-09T12:02:51.945488Z"
}
```

## 5. Create Transaction

**POST /transactions/** (login required)

Creates a transaction owned by the logged-in user and stores it in SQLite.

Example request:

```json
{
  "amount": 45.5,
  "category": "Food",
  "description": "Lunch",
  "date": "2026-10-08"
}
```

`amount` must be a number greater than 0 and at most 1,000,000,000. `description` is optional and may be `null`.

Only these four fields are accepted. Any other field, including `user_id`, is rejected with HTTP 422:

```json
{
  "detail": [
    {
      "type": "extra_forbidden",
      "loc": ["body", "user_id"],
      "msg": "Extra inputs are not permitted",
      "input": 3
    }
  ]
}
```

Successful response: HTTP 201, with the same format as items in section 6.

Invalid transaction data returns HTTP 422.

## 6. Retrieve Transactions

**GET /transactions/** (login required)

Returns all of the logged-in user's transactions, ordered by ID.

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

A user with no transactions receives `[]`.

## 7. Delete Transaction

**DELETE /transactions/{transaction_id}** (login required)

Deletes one of the logged-in user's transactions.

Successful response: HTTP 200.

Example:

```json
{
  "message": "Transaction deleted successfully"
}
```

If the transaction does not exist **or belongs to another user**, the API returns HTTP 404:

```json
{
  "detail": "Transaction not found"
}
```

## 8. Spending Summary

**GET /spending/summary** (login required)

Calculates total spending, spending by category, and category percentages using the logged-in user's transactions.

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

A user with no transactions receives zeros and empty objects.

## 9. Monthly Spending Comparison

**GET /spending/compare** (login required)

Compares the logged-in user's spending in the selected month with the previous month.

Query parameters:

- `year`: Selected year (2–9999).
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

An invalid year or month returns HTTP 422.

## 10. Financial Recommendations

**GET /recommendations/** (login required)

Query parameters:

- `year`
- `month`

Example:

`/recommendations/?year=2026&month=10`

Returns rule-based recommendations based on the logged-in user's monthly spending changes.

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

## 11. AI Recommendations

**GET /recommendations/ai** (login required)

Query parameters:

- `year`
- `month`

Example:

`/recommendations/ai?year=2026&month=10`

Generates AI explanations of the logged-in user's financial recommendations.

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

The user's spending categories and percentage changes are sent to the server configured in `OLLAMA_URL`. Keep it pointed at a local or trusted server.

## Current API Limitations

- No limit on login attempts (no rate limiting or account lockout).
- No logout, token revocation, refresh tokens, password change or password reset.
- Registration reveals whether an email is already registered (HTTP 409).
- Unowned transactions from before user accounts existed cannot yet be assigned to a user.
- No transaction editing endpoint.
- No pagination for transaction retrieval.
- No income transaction support.
- No budgeting or debt planning endpoints.
- AI explanations are not automatically verified.

These endpoints are intended for local development and testing. Production use requires HTTPS; see the README's security section.
