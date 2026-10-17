# Debt payment ledger

`POST /debts/{debt_id}/payments` creates a user-owned payment with an idempotency request key. Future payment dates are rejected. Applied payments reduce the debt's remaining total due. Listing and deletion use `/debts/payments`; deleting an applied payment restores the corresponding outstanding amount.

The ledger is separate from transactions. Spending/savings services account for paid debt explicitly; the backend does not insert a duplicate expense transaction. A user manually entering the same payment as an unrelated expense can still double-count it, so keep these records distinct.

Automatic debt synchronization uses unique due occurrences and caps the month's payment after manual entries and the remaining balance. Deleted automatic occurrences are not recreated merely by refreshing. Debt deletion preserves payment history for past-month reporting. This is bookkeeping, not an actual lender payment.

See [debt calculations](debts.md), [budget targets](user-budgets.md) and [month-end savings](savings.md).
