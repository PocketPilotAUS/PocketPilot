# Core calculations and safeguards

- Budgets use saved monthly income and named targets, with legacy percentage support. Actual spending comes from user-owned transactions and remains separate from targets.
- Debt uses fixed amortized estimates and a zero-interest branch. Applied manual/automatic payments reduce outstanding total; see [debts](debts.md).
- Completed-month savings are bounded by max(0, income - spending - paid debt), checked again under lock. Goal progress combines entered starting progress and assigned contributions, not projected allocations.
- Goal contributions derive from remaining amount and contribution months. Budget-backed planning includes derived debt and protects essential categories. Model prose cannot overwrite verified figures.
- Budget fingerprints hash effective month, income and normalized category targets; actual spending is excluded. Monitoring fingerprints cover different, broader facts.
- Proposal gates require write intent, an evidenced monetary amount and matching expense category. Dates are masked before monetary extraction; ambiguous requests require clarification. UAE-relative dates and income periods override conflicting model values.
- Recurring synchronization uses unique occurrence claims and short-month clamping; it runs on requests, not a background banking scheduler.
- Monitoring applies deterministic risk levels and constrained target reductions; see [monitoring](spending-monitoring.md).
- CSV import uses deterministic date/amount parsing, bounded category suggestions, signed preview tokens and atomic duplicate checks; see [import](statement-import.md).

Native Ollama `/api/chat` supplies suggestions, not SQL or authoritative arithmetic. Money storage uses cents, Decimal and legacy float at different boundaries; tests cover round trips. See [testing](testing.md).

## Current planning and interpretation details

Savings availableAfter is capacity after accepted cuts and before the new contribution; remainingAfterSavings subtracts monthlyContribution once. Budget-backed calculations use effective debt-aware targets and do not subtract actual expenses again. See [exact formulas](financial-planning.md).

Debt acceleration uses remaining principal estimated from saved principal/rate and applied payments, fixed monthly reducing-balance amortization and owned snapshots. Annual percentage rate is divided by 1200 for the monthly fraction; it is never treated as a monthly percentage. No fees/variable-rate settlement forecast is supplied.

Semantic routing precedes deterministic financial validation. Only signed incomplete record drafts carry intake fields; a completed proposal cannot contaminate a subsequent expense source. Literal selectors and persisted labels resolve existing proposals conservatively; multiple indistinguishable candidates require clarification.
