# PocketPilot phase 3 handoff log

This phase begins on 14 October 2026 after the Phase 2 handoff for commit b92ef5b, on feature/karim-planning-review. Add implementation, setup, verification and limitations here for the next developer handoff. Entries describe local work and do not imply commit, push or merge. The previously delivered Phase 2 Word document remains unchanged.

## Manual savings including previous savings

### User behavior

Home > Savings now includes Add savings for money already held before using PocketPilot and other contributions not included in monthly confirmations. A positive amount is required; optional label defaults to Previous savings. Manual entries can be edited or removed with confirmation. Total savings is manual contributions plus confirmed completed-month contributions, with separate subtotals shown. Monthly estimates still exclude unconfirmed amounts. Manual entries do not create income/transactions, reduce debt balances or alter monthly confirmations. Copy warns against adding money already counted by monthly confirmation; the app cannot detect that semantic overlap automatically. No withdrawals or live bank synchronization added.

### Implementation

- Backend/app/models/savings.py registers ManualSavings alongside MonthlySavings; models/__init__.py imports both. New manual_savings table stores owner, label, integer AED cents and owner-scoped UUID request key.
- Backend/app/routers/savings.py adds authenticated POST /savings/manual and PUT/DELETE /savings/manual/{id}; each record is scoped to the verified owner. Retrying POST with the same request key returns its existing entry; the unique constraint handles concurrent retries. Amounts are finite, positive, at most AED 1 billion with two decimal places. Readable labels are 1–80 characters. Overview includes manual_entries and manual_total and computes the combined total server-side.
- Mobile/src/components/ManualSavingsPanel.tsx provides input, retry key and synchronous request guard, edit/remove controls, inline errors and explicit delete confirmation. SavingsScreen owns the combined totals; changing entries recomputes totals without altering history. SavingsStyles is external and theme-aware; AED/CNY input uses existing conversion and preserves unchanged editor amounts. New copy supports Arabic and Mandarin. Custom labels stay user text.
- Updated services/savingsService.ts and docs/savings.md. No dependencies, environment variables, secrets or AI calls added.

### Migration and validation

New Backend/migrate_manual_savings.py backs up SQLite before adding only manual_savings plus owner index and is idempotent. Teammates with existing data must run it from Backend; fresh init_db.py creates the registered model. Existing monthly confirmations and all other financial records remain intact. Previous migrations remain as delivered. Updated Savings overview reports missing manual storage as a setup error until migration runs.

Focused backend tests: 22 passed (11 existing monthly tests plus 11 new manual tests) covering CRUD, totals, owner isolation, missing-income independence, same-key retries, invalid values, huge IDs and migration preservation/backup/idempotence. Mobile TypeScript passed; lint remains unavailable because no lint script is configured. Full-suite and local migration results will be appended after completion. Device layout remains unverified. No commit, push or merge performed.

Completed validation: full backend suite 392 passed in 62.81 seconds; final Mobile TypeScript passed. Workspace check-manual-savings.cjs passed CNY input conversion, unchanged CNY edit normalization, default label, request-key retention on retry, same-entry update and explicit removal. Local migration applied successfully after creating pocketpilot.backup-manual-savings-20261014-175313-854865.db. No existing monthly records rewritten. Git whitespace check passed. Actual phone layout remains unverified.

## 14 October 2026 Simplified Add savings button

Removed the manual-savings introduction heading, explanatory paragraph and empty-state text beside Add savings. The collapsed section is now a standalone full-width mint Add savings button using the shared dashboard primaryButton/primaryButtonText styles, matching height, rounded corners and disabled/pressed feedback. The form opens on tap; existing entries retain their edit/remove controls. No empty card renders when there are no manual entries. The short double-counting guidance remains inside the opened form. Manual amounts, API, totals, migration and monthly savings behavior are unchanged.

Mobile TypeScript and the existing mocked manual-savings flow check passed. Lint remains unavailable because no lint script exists. Actual phone layout remains unverified. No backend changes or new migrations. No commit, push or merge.

## 14 October 2026 Always visible Add expense on Spending

Moved the SpendingBreakdown Add an expense action outside its empty-data branch. Home > Spending now shows one Add an expense button beneath the breakdown for empty, populated and loading states. It uses the shared dashboard solid mint primary button and external spendingAddAction layout, matching the app's newer buttons. The existing onAddExpense callback still opens the Transactions add form; no navigation, recording or calculation behavior changed. Removed the old empty-state-only action so there is no duplicate button.

Changed Mobile/src/components/dashboard/SpendingBreakdown.tsx and Mobile/src/styles/DashboardStyles.ts. Mobile TypeScript passed; lint remains unavailable because there is no lint script. Whitespace checks passed. Phone rendering remains unverified. No backend, migration or dependency changes, commit, push or merge.
