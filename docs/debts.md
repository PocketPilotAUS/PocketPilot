# Debt management

The Debt screen and [debt router](../Backend/app/routers/debts.py) support user-scoped create/list/update/delete. Inputs describe principal, annual interest, term and optional automatic payment schedule. Displayed obligations are estimates, not lender statements.

The monthly installment uses amortization: monthly rate = APR / 1200; payment = principal * rate / (1 - (1 + rate)^(-months)). With zero interest, payment is principal / months. Estimated total interest is payment * months - principal. The stored baseline total due and fixed installment support subsequent payment accounting; remaining total reflects applied payments rather than repeatedly treating remaining principal as a fresh loan.

Debt-aware budget summaries derive the Debt allocation from monthly obligations. The target remains stable for that budget month even when a payment changes the remaining balance, preventing normal payment entry from unexpectedly rewriting a reviewed monthly target. Changes to derived obligations can still invalidate draft budget plans.

Automatic entries are opt-in with a payment day and next due date. Requests synchronize due entries, clamp short months, cap payments at the remaining amount, and stop paid debts. Manual payments offset the same month's automatic obligation. There is no background banking or money transfer. Deleting a debt preserves payment history. See [payment rules](debt-payments.md).
