# Debt management

The Debt screen and [debt router](../Backend/app/routers/debts.py) support user-scoped create/list/update/delete. Inputs describe principal, annual interest, term and optional automatic payment schedule. Displayed obligations are estimates, not lender statements.

The monthly installment uses amortization: monthly rate = APR / 1200; payment = principal * rate / (1 - (1 + rate)^(-months)). With zero interest, payment is principal / months. Estimated total interest is payment * months - principal. The stored baseline total due and fixed installment support subsequent payment accounting; remaining total reflects applied payments rather than repeatedly treating remaining principal as a fresh loan.

Debt-aware budget summaries derive the Debt allocation from monthly obligations. The target remains stable for that budget month even when a payment changes the remaining balance, preventing normal payment entry from unexpectedly rewriting a reviewed monthly target. Changes to derived obligations can still invalidate draft budget plans.

Automatic entries are opt-in with a payment day and next due date. Requests synchronize due entries, clamp short months, cap payments at the remaining amount, and stop paid debts. Manual payments offset the same month's automatic obligation. There is no background banking or money transfer. Deleting a debt preserves payment history. See [payment rules](debt-payments.md).

## AI repayment planning

AI Chat retrieves saved account-owned loans, including name, principal, annual rate, remaining term and estimated payment. It asks only for missing selection/timeframe/amount and preserves active debt context across short follow-ups (two years = 24 months; three = 36). Read-only debt questions and topic switches do not record payments.

The dedicated debt-planning service uses saved principal adjusted for recorded payments and fixed-rate monthly reducing-balance estimates. It includes other active goal commitments in affordability and avoids counting already-applied debt extras twice. This is more specific than a guided generic debt goal, which is an extra-contribution scenario. Fees, variable rates and lender settlement terms are excluded.

A ready debt plan is an owner-bound reviewed capability. Explicit acceptance can save the plan and, only with the supported apply-to-budget choice, apply its extra target. It never records a lender payment. Rejection/expiry invalidates acceptance, and changed debt/budget snapshots require fresh review. See [Financial Plans](financial-planning.md).
