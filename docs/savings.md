# Monthly savings

Home > Savings shows manual savings plus confirmed completed-month savings, a selected month's estimate and monthly confirmation history. Users can add savings held before installing the app and other contributions not included in monthly confirmations. It is a cumulative contribution tracker, not a live bank balance; withdrawals and automatic rollover are not supported.

## Manual savings

Add savings accepts a positive selected-currency amount and optional label (defaults to Previous savings). Values are converted to AED and stored as integer cents. The total card separates manual contributions from confirmed monthly contributions. Entries can be edited or removed; monthly estimates, income, expenses, debt balances and confirmations are unchanged. Do not enter money already covered by a monthly confirmation. Editing unchanged CNY amounts preserves stored AED values. Saved custom labels remain user text.

Authenticated POST `/savings/manual` creates an entry with label, amount and UUID request_key; repeated request keys are scoped to the owner and return the same entry instead of adding twice. PUT/DELETE `/savings/manual/{id}` edits/removes owner-only entries; unknown or other-owner IDs return 404. Amounts must be finite, positive, at most AED 1 billion and up to two decimal places; labels are readable and 1–80 characters.

New setup requirement for existing databases: run `./venv/Scripts/python.exe migrate_manual_savings.py` from Backend. It backs up first, adds only manual_savings and its owner index, and is idempotent. Existing monthly_savings records are preserved. Fresh init_db.py creates both tables. Updated Savings overview expects the manual table and returns a setup error if absent. The original migrate_savings.py remains required on older installations; neither old migration was rewritten.

Estimate = monthly income minus all recorded spending minus actual debt payments not already recorded in spending. Recorded spending already includes any debt payment entered as a transaction, regardless of category. The user enters missing actual debt payments separately (default zero); loan balances and estimated installments on the Debt page are never deducted automatically. Extra payments entered here do not create expense transactions or reduce saved debt balances.

Current month is an estimate only. Select a past month to confirm that all costs were entered and its leftover was actually saved. Missing income blocks confirmation; negative leftover is stored as a shortfall and contributes zero savings. Income for any selected period can be edited through Spending's budget setup. One confirmation per owner/month: updating replaces that month's amount, never adds it twice. Confirmed records are snapshots, not recalculated silently when income/transactions change. Tap history to review the month and explicitly update. Confirmations require matching displayed income/spending; stale views return 409 and require refresh.

All stored amounts are AED integer cents; CNY uses the existing display/input conversion and reference rate. Period cutoff uses UAE time (UTC+4). Backend syncs recurring expenses using the existing budget behavior before taking the snapshot.

## Setup and API

Existing installations: stop the backend if possible and run `./venv/Scripts/python.exe migrate_savings.py` from Backend, then restart. The migration creates a timestamped SQLite backup and adds only monthly_savings and its owner index; running again is safe. Fresh init_db.py creates the registered model. No dependencies, secrets or environment variables added. Missing table returns a setup error.

Authenticated GET `/savings?year=YYYY&month=M` returns selected income/spending, confirmation eligibility, total and owner-only history. PUT `/savings/confirm` accepts year, month, extra_debt_payments, expected_income and expected_spent. Server computes and stores savings; client cannot supply a saved total. SQLite confirmation uses a write lock around snapshot checks and unique owner/month upsert.

Validation: 22 focused savings tests cover monthly confirmations and manual CRUD/totals, owner isolation, idempotent retries, validation and backup/idempotent migrations. Mobile typecheck and full-suite results are recorded in the phase logs. Phone rendering remains a manual check.
