# API reference

This inventory is checked against the registered FastAPI OpenAPI schema. Run the backend and use `/docs` or `/openapi.json` for field constraints and response schemas. Paths below are relative to the API base URL.

Authentication routes register/login/refresh/logout and health are not Bearer-protected; refresh/logout require an opaque refresh token body. Financial/account routes require an access JWT. Missing, invalid or cross-user resources are rejected. GET operations can synchronize due recurring/debt entries; see the module guides.

| Method | Path | Body schema | Required query |
| --- | --- | --- | --- |
| POST | `/auth/register` | `UserCreate` | - |
| POST | `/auth/login` | `UserLogin` | - |
| POST | `/auth/refresh` | `RefreshRequest` | - |
| POST | `/auth/logout` | `RefreshRequest` | - |
| GET | `/auth/me` | `-` | - |
| PATCH | `/auth/me` | `ProfileUpdate` | - |
| POST | `/auth/password` | `PasswordChange` | - |
| POST | `/ai/chat` | `ChatRequest` | - |
| GET | `/budget/monthly` | `-` | year, month |
| PUT | `/budget/income` | `IncomeInput` | year, month |
| PUT | `/budget/setup` | `BudgetSetup` | year, month |
| PUT | `/budget/plan` | `PlanInput` | year, month |
| POST | `/ai/proposals/{proposal_id}/confirm` | `-` | - |
| POST | `/ai/proposals/{proposal_id}/dismiss` | `-` | - |
| GET | `/recurring/` | `-` | - |
| POST | `/recurring/` | `CreateSchedule` | - |
| PUT | `/recurring/{schedule_id}` | `ScheduleInput` | - |
| POST | `/recurring/{schedule_id}/stop` | `-` | - |
| GET | `/planning/context` | `-` | - |
| PUT | `/planning/profile` | `PlanningInput` | - |
| POST | `/planning/preview` | `PlanningInput` | - |
| GET | `/planning/plans` | `-` | - |
| POST | `/planning/plans` | `PlanningInput` | - |
| PUT | `/planning/plans/{plan_id}` | `PlanningInput` | - |
| DELETE | `/planning/plans/{plan_id}` | `-` | - |
| POST | `/planning/debt-plans/preview` | `DebtGoalPreview` | - |
| POST | `/planning/debt-plans` | `DebtGoalSave` | - |
| PUT | `/planning/debt-plans/{plan_id}` | `DebtGoalSave` | - |
| POST | `/planning/budget-plans` | `BudgetGoalSave` | - |
| PUT | `/planning/budget-plans/{plan_id}` | `BudgetGoalSave` | - |
| POST | `/planning/budget-plans/preview` | `BudgetGoalSave` | - |
| GET | `/planning/status` | `-` | - |
| POST | `/planning/adjustments/proposal` | `AdjustmentRequest` | - |
| POST | `/planning/adjustments/accept` | `AdjustmentAccept` | - |
| POST | `/planning/reviews/{review_id}/reject` | `-` | - |
| POST | `/planning/reviews/{review_id}/accept` | `ReviewAccept` | - |
| POST | `/transactions/import/preview` | `PreviewInput` | - |
| POST | `/transactions/import/confirm` | `ConfirmInput` | - |
| GET | `/debts/payments` | `-` | - |
| POST | `/debts/{debt_id}/payments` | `PaymentInput` | - |
| DELETE | `/debts/payments/{payment_id}` | `-` | - |
| GET | `/debts` | `-` | - |
| POST | `/debts` | `DebtInput` | - |
| PUT | `/debts/{debt_id}` | `DebtInput` | - |
| DELETE | `/debts/{debt_id}` | `-` | - |
| GET | `/savings` | `-` | year, month |
| PUT | `/savings/confirm` | `Confirmation` | - |
| POST | `/savings/manual` | `ManualCreate` | - |
| PUT | `/savings/manual/{entry_id}` | `ManualInput` | - |
| DELETE | `/savings/manual/{entry_id}` | `-` | - |
| GET | `/` | `-` | - |
| GET | `/transactions/` | `-` | - |
| POST | `/transactions/` | `TransactionCreate` | - |
| DELETE | `/transactions/{transaction_id}` | `-` | - |
| GET | `/spending/summary` | `-` | - |
| GET | `/spending/compare` | `-` | year, month |
| GET | `/recommendations/` | `-` | year, month |
| GET | `/recommendations/ai` | `-` | year, month |

## Workflow notes

- Chat generates drafts/proposals; it does not automatically accept them. Transaction confirmation/dismissal uses `/ai/proposals`; plan persistence uses `/planning`.
- Budget-backed plan save/update/preview require the reviewed budget fingerprint and validated profile/choices. A stale budget returns 409 rather than bypassing review.
- Adjustment acceptance uses its own monitoring fingerprint and request key; month-end savings checks its snapshot independently.
- CSV preview accepts JSON CSV text, not arbitrary file upload; confirmation uses an owner-bound expiring preview token.
- Transaction CRUD is add/list/delete only. There is no generic update endpoint or AI savings-contribution write.

See [AI Chat](budget-goal-chat.md), [planning](financial-planning.md), [budgets](user-budgets.md), [debts](debts.md), [savings](savings.md) and [CSV import](statement-import.md).

## Current chat and plan contracts

ChatRequest carries messages plus optional signed record_state/debt_state, goal/profile context, currency/rate, active_proposal_id, proposal_ids and plan_review_ids. IDs are owner-verified; references are limited to IDs supplied by that conversation. ChatResponse separates proposal/proposal_updates from plan/plan_updates. Read-only or ambiguous turns do not create recording proposals.

Ready Financial Plans include reviewId/reviewStatus. Common acceptance uses stored reviewed facts. ReviewAccept supports optional apply_to_budget and plan_id for supported flows, not arbitrary replacement amounts. Reviews enforce owner, 30-minute expiry, terminal status and concurrency guards. Original budget/debt endpoints also enforce registered capability state and stale snapshots.

Preview may persist review metadata while saving no FinancialPlan, deposit or transaction. Saving /planning/profile explicitly persists inputs. Manual guided CRUD and monitoring adjustment acceptance remain separate supported operations.

Typical errors: 401 authentication, 404 unknown/foreign resources, 409 stale/conflicting/terminal capabilities, 422 invalid fields/signed drafts. Consult live OpenAPI for endpoint-specific responses; these are not universal code rules.
