# Automatic debt payments

Run `python migrate_automatic_debts.py` with the backend stopped. The migration backs up SQLite and is repeatable. Fresh databases register the new columns through the existing models.

Automatic payments are opt-in per loan. Choose a monthly day and a first due date today or later. Short months clamp to their last day. These are assumed payments, not bank transfers or verified bank activity. Due entries catch up on debt/payment and monthly-budget reads; no background service is required. The original estimated monthly amount stays fixed, with the final payment capped at the remaining total.

The loan's estimated total (principal plus estimated interest) is a starting repayment total. New payments reduce that total by their full amount. The total does not recompute interest after every payment. Principal remains a lender-input reference, not an amortized balance. Existing payment history is not applied again during migration, because users may already have manually updated their balances. Changing balance, rate or term establishes a new baseline and clears older payments' balance deductions while preserving those payments in spending/savings history.

Auto entries use deterministic request keys and a conditional schedule advance inside a transaction. Manual payments for the loan in the instalment month reduce the auto amount. A manual entry after an auto entry for that month is rejected; remove the automatic entry before entering its replacement. Removing a payment restores only its applied amount and does not recreate that same automatic due date. A fully paid schedule stops; restoring a removed final payment requires re-enabling the schedule if desired.

Home and the overview sum remaining loan totals. Spending and Savings use the same DebtPayment ledger, without creating duplicate Transactions. Manually entering the same payment as an unrelated Transaction remains outside automatic duplicate detection.
