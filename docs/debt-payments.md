# Actual debt payments

Debt now provides Record payment for each saved debt: positive selected-currency amount and actual payment date (YYYY-MM-DD, no future dates). Values are stored in AED cents. Payment history supports removal to correct mistakes. Loan balances and estimated installments remain separate; recording a payment does not change principal or create an expense transaction.

Savings reads the authenticated user's payments within the selected calendar month. Confirmation calculates income minus spending minus actual debt payments under the SQLite write lock. The displayed payment total is checked on confirmation; changed payments require refresh. Existing confirmed snapshots stay unchanged until explicitly updated. The historical extra_debt_cents storage column now holds the confirmed actual payment deduction; old snapshots are preserved. The legacy extra_debt_payments request field remains validated for older clients but no longer controls deductions.

Existing databases: stop the backend and run `./venv/Scripts/python.exe migrate_debt_payments.py` from Backend. The additive migration backs up first and preserves existing records; rerunning is safe. New databases register the payment model through models/__init__.py and init_db.py.

Authenticated GET /debts/payments lists owner-only history, POST /debts/{id}/payments records an owned loan's payment with an owner-scoped UUID retry key, and DELETE /debts/payments/{id} removes it. Payment history retains the loan's name even if the loan is deleted. Reusing a retry key with different facts is rejected.

Double-counting against expenses is intentionally deferred: a payment separately entered as an expense is currently deducted twice. Current-month estimates and completed-month confirmation behavior remain unchanged pending the next discussion.

Validation: full backend suite 402 passed; Mobile TypeScript and Git whitespace checks passed. Local additive migration completed with a database backup. Actual phone and Chrome layout remain unverified. Mobile has no configured lint script.
