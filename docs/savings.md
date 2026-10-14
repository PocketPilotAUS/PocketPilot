# Monthly savings

Home > Savings shows the sum of confirmed completed-month savings, a selected month's estimate and monthly confirmation history. It is a cumulative contribution tracker, not a live bank balance: withdrawals, opening savings balances and automatic rollover are not supported in this first version.

Estimate = monthly income minus all recorded spending minus actual debt payments not already recorded in spending. Recorded spending already includes any debt payment entered as a transaction, regardless of category. The user enters missing actual debt payments separately (default zero); loan balances and estimated installments on the Debt page are never deducted automatically. Extra payments entered here do not create expense transactions or reduce saved debt balances.

Current month is an estimate only. Select a past month to confirm that all costs were entered and its leftover was actually saved. Missing income blocks confirmation; negative leftover is stored as a shortfall and contributes zero savings. Income for any selected period can be edited through Spending's budget setup. One confirmation per owner/month: updating replaces that month's amount, never adds it twice. Confirmed records are snapshots, not recalculated silently when income/transactions change. Tap history to review the month and explicitly update. Confirmations require matching displayed income/spending; stale views return 409 and require refresh.

All stored amounts are AED integer cents; CNY uses the existing display/input conversion and reference rate. Period cutoff uses UAE time (UTC+4). Backend syncs recurring expenses using the existing budget behavior before taking the snapshot.

## Setup and API

Existing installations: stop the backend if possible and run `./venv/Scripts/python.exe migrate_savings.py` from Backend, then restart. The migration creates a timestamped SQLite backup and adds only monthly_savings and its owner index; running again is safe. Fresh init_db.py creates the registered model. No dependencies, secrets or environment variables added. Missing table returns a setup error.

Authenticated GET `/savings?year=YYYY&month=M` returns selected income/spending, confirmation eligibility, total and owner-only history. PUT `/savings/confirm` accepts year, month, extra_debt_payments, expected_income and expected_spent. Server computes and stores savings; client cannot supply a saved total. SQLite confirmation uses a write lock around snapshot checks and unique owner/month upsert.

Validation: 11 focused tests cover confirmed versus estimated totals, debt counted once, debt estimates ignored, duplicate confirmation/updating, shortfall, missing income, changed records, ownership/authentication, invalid values, month-end guard and backup/idempotent migration. Mobile typecheck and full-suite results recorded in the phase log. Phone rendering remains a manual check.
