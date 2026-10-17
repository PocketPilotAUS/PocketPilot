# Financial Plans

Two planning paths are implemented. Guided planning collects income, other household income, household size, expenses, typical months, goal amount/deadline and protected categories. Budget-backed AI goal planning uses the saved monthly budget, including derived debt obligations, rather than asking the model to invent allocations.

`/planning/context` provides existing context. Saving `/planning/profile` stores inputs; `/planning/preview` evaluates without saving a plan. `/planning/plans` supports saved guided-plan CRUD. `/planning/budget-plans` creates a reviewed budget-backed plan, its `/{plan_id}` route updates one, and `/planning/budget-plans/preview` recalculates adjustments without persistence.

The backend computes figures deterministically. Goal contributions use remaining goal amount and the applicable contribution months; budget-backed deadlines count the current and target months inclusively. Explicitly unknown starting progress is not an invented contribution. Protected/essential allocations constrain possible reductions. Feasible, adjusted and later-deadline choices are reviewable scenarios, not automatic transfers or investment forecasts.

## Draft lifecycle and fingerprints

AI Chat returns a draft with verified amounts, deadline and budget fingerprint. It is described as prepared and unsaved. Accept explicitly calls the save endpoint; only a successful response marks it saved. Adjust previews changes; Reject declines the local draft. Saved plans remain available independently of later chat messages.

Chat generation, adjustment preview and acceptance use the same debt-aware budget baseline. The budget fingerprint covers effective year/month, saved income and normalized category targets including derived Debt. A genuine change returns a stale-budget rejection; refresh the draft rather than bypassing validation. Spending alone is not part of this fingerprint. Stale adjustment choices are dropped when their budget basis changes. Locked writes and request-key idempotency protect retries.

Plan snapshots do not automatically deduct money or record contributions. See [AI Chat](budget-goal-chat.md), [monitoring](spending-monitoring.md) and [savings](savings.md). Offline/model failures can prevent drafting even though manual financial screens remain available.

## Guided inputs and assumptions

Typical historical months must be explicitly confirmed as complete before they supply category averages. Blank costs remain unknown; zero is entered only when a cost does not apply. Household size supplies context, not an invented per-person benchmark. Planning profile income does not overwrite recorded dashboard income. A guided form can save its profile before a separate plan save.

The guided reduction scenario considers up to 30% of unprotected Entertainment, Shopping and Subscriptions where needed; this is a reviewable product assumption, not a universal spending recommendation. Infeasible goals expose shortfalls. Debt goal contributions are extra after stated minimums and do not calculate an exact lender payoff schedule; spending-control goals treat their target as a monthly ceiling. No savings interest or investment growth is assumed. Saved plans survive sign-out; chat conversation state does not.
