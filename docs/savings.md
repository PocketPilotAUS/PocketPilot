# Savings goals and contributions

The Savings screen combines recorded manual savings and confirmed month-end savings. These are user-entered ledger values, not a verified bank balance. Saved Financial Plans can represent savings goals; a plan's monthly contribution is an allocation, not proof that money was saved.

Manual contributions support create, edit and delete with amount, label and optional saved-goal identifier. Creation uses a request key to prevent duplicate retries. A contribution can be assigned to one goal. Goal progress combines starting progress entered in the plan with assigned manual contributions; aggregate monthly savings are not automatically assigned to every goal. Do not add goal progress to total savings, because values can overlap.

`GET /savings` returns a requested year/month's context. `PUT /savings/confirm` confirms a completed UAE-local month, never the current/future month. The server calculates maximum available savings as max(0, income - transaction spending - actual debt payments). Users may confirm a smaller actual saved amount. A changed income/spending/debt snapshot returns 409 under a write lock rather than silently accepting stale figures.

Confirmation is unique per user/month and updates that month's snapshot on repeat confirmation. Later ledger edits do not silently rewrite an already confirmed month. Contributions are separate from the month-end snapshot; enter values deliberately to avoid representing the same savings twice.

Missing goal-assignment columns require an inspected additive migration, not a reset. See [database maintenance](database.md). AI Chat can describe scoped goals and contributions, but recording a savings contribution uses this dedicated workflow rather than pretending it is an expense.

## Goal proposals versus actual savings

Savings affordability is informational and creates no acceptable plan without a grounded goal/target. Natural contribution follow-ups can refine a named goal, but a new chat cannot inherit an unrelated goal. A monthly contribution is never classified as income simply because it is a monetary amount.

Ready plans use the durable acceptance/rejection lifecycle in [Financial Plans](financial-planning.md). Accepting a goal saves its target and planned monthly contribution without income, expense or completed-savings entries. Manual contributions and completed-month confirmation remain separate explicit operations. The plan card distinguishes Available before savings from Remaining after monthly savings; see that guide for formulas and debt double-counting rules.
