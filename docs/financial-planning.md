# Financial Plans

Two planning paths are implemented. Guided planning collects income, other household income, household size, expenses, typical months, goal amount/deadline and protected categories. Budget-backed AI goal planning uses the saved monthly budget, including derived debt obligations, rather than asking the model to invent allocations.

`/planning/context` provides existing context. Saving `/planning/profile` stores inputs; `/planning/preview` evaluates without saving a plan. `/planning/plans` supports saved guided-plan CRUD. `/planning/budget-plans` creates a reviewed budget-backed plan, its `/{plan_id}` route updates one, and `/planning/budget-plans/preview` recalculates adjustments without persistence.

The backend computes figures deterministically. Goal contributions use remaining goal amount and the applicable contribution months; budget-backed deadlines count the current and target months inclusively. Explicitly unknown starting progress is not an invented contribution. Protected/essential allocations constrain possible reductions. Feasible, adjusted and later-deadline choices are reviewable scenarios, not automatic transfers or investment forecasts.

## Draft lifecycle and fingerprints

AI Chat returns a draft with verified amounts, deadline and budget fingerprint. It is described as prepared and unsaved. Accept explicitly calls the save endpoint; only a successful response marks it saved. Adjust previews changes; Reject calls the backend and rejects that issued review capability, rather than merely hiding the card. Saved plans remain available independently of later chat messages.

Chat generation, adjustment preview and acceptance use the same debt-aware budget baseline. The budget fingerprint covers effective year/month, saved income and normalized category targets including derived Debt. A genuine change returns a stale-budget rejection; refresh the draft rather than bypassing validation. Spending alone is not part of this fingerprint. Stale adjustment choices are dropped when their budget basis changes. Locked writes, exclusive acceptance claims and request-key idempotency protect retries and concurrent requests.

Plan snapshots do not automatically deduct money or record contributions. See [AI Chat](budget-goal-chat.md), [monitoring](spending-monitoring.md) and [savings](savings.md). Offline/model failures can prevent drafting even though manual financial screens remain available.

## Guided inputs and assumptions

Typical historical months must be explicitly confirmed as complete before they supply category averages. Blank costs remain unknown; zero is entered only when a cost does not apply. Household size supplies context, not an invented per-person benchmark. Planning profile income does not overwrite recorded dashboard income. A guided form can save its profile before a separate plan save.

The guided reduction scenario considers up to 30% of unprotected Entertainment, Shopping and Subscriptions where needed; this is a reviewable product assumption, not a universal spending recommendation. Infeasible goals expose shortfalls. Debt goal contributions are extra after stated minimums and do not calculate an exact lender payoff schedule; spending-control goals treat their target as a monthly ceiling. No savings interest or investment growth is assumed. Saved plans survive sign-out; chat conversation state does not.


## Durable review lifecycle

Ready guided, savings/budget and debt drafts are registered in financial_plan_reviews with reviewId/reviewStatus and a 30-minute expiry. POST /planning/reviews/{review_id}/reject rejects a pending review; /accept explicitly accepts it. An internal accepting claim protects in-flight writes; terminal states are rejected, saved or expired. Mobile waits for backend rejection; a failed request leaves the card pending.

Common acceptance uses stored reviewed facts, not arbitrary replacement financial fields. Existing budget/debt save endpoints also verify the registry, original key/token and snapshots. Rejected capabilities cannot be replayed through older endpoints. Completed retries return the same result; concurrent requests cannot create duplicate plans. Consumed capabilities cannot recreate deleted/superseded plans. A fresh proposal requires a fresh review.

Manual guided-plan POST/PUT /planning/plans remains supported explicit CRUD with PlanningInput; this is distinct from conversational acceptance of an issued review. Monitoring adjustment acceptance also uses its own fingerprint/request key.

Chat sends plan_review_ids for the current conversation. Pending/rejected/saved/expired plan references remain distinguishable from transactions after topic switches. New Chat clears client references, not durable safety metadata. Conversational acceptance requests report status and point to controls; they do not apply plans.

## Savings capacity labels and formulas

For a budget-backed savings draft, let I = saved monthly income, B = effective planned allocations (including derived Debt once), C = explicitly accepted proposed cuts and S = proposed monthly savings:

- availableBefore = I - B.
- availableAfter = availableBefore + C: monthly capacity before the contribution.
- remainingAfterSavings = availableAfter - S.

Mobile labels availableAfter as Available before savings and remainingAfterSavings as Remaining after monthly savings. Actual transactions are not subtracted again from this planned-budget calculation. Derived debt replaces the canonical Debt allocation instead of adding it twice; see [budgets](user-budgets.md).

Synthetic regression example: income AED 10,000, non-debt targets AED 6,420 and separate calculated debt installment AED 566.14 give AED 3,013.86 before savings. AED 600 monthly savings leaves AED 2,413.86. A remaining AED 5,000 target requires ceil(5000/600) = 9 contribution months. Starting October 2026 gives June 30, 2027. These are fixed test values, not today's deadline.

Acceptance saves the goal and planned contribution, without creating a savings deposit, income receipt, expense or debt payment. Explicitly accepted budget choices/debt extras affect targets only through supported operations. Current setup requires migrate_plan_reviews.py; old unregistered cards need a new review.
