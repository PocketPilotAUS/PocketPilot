# AI Chat, recording and goal planning

[chat.py](../Backend/app/routers/chat.py) implements POST /ai/chat. The authenticated account supplies authoritative budgets, actual spending, debts, saved goals and contributions. Planned allocations, actual deposits and outstanding debt are separate facts.

## Interpretation and grounded fields

[client.py](../Backend/app/ai/client.py) asks qwen3:4b for structured semantic interpretation. [chat_interpretation.py](../Backend/app/services/chat_interpretation.py) validates the contract; chat_context.py supplies deterministic lookup/action guards and fallback context. The model interprets meaning; backend evidence validation and calculations decide what is allowed.

Natural expenses, income receipts, lookups, affordability, goal setup, debt advice, unsupported requests and clarifications have distinct paths. Hypotheticals, negations and lookups cannot become recording requests solely because the model emits an action. Today/yesterday/tomorrow use the server's UAE UTC+4 date, not an invented model date. No per-account timezone setting is implemented. Shorthand such as 2k is grounded to 2,000. Missing/conflicting fields require clarification.

chat_expenses.py, chat_income.py and chat_record_drafts.py retain incomplete draft facts: amount, category/description, date, currency and income operation. Signed tokens are owner/purpose-bound and valid for 30 minutes; completion/cancellation prevents reuse. A date answer completes only its appropriate pending draft. Explicit Groceries stays Groceries; lunch can map to Food, transport to Transport. Multiple conflicting amounts/categories are not silently resolved by model preference.

## Income and read-only questions

Income lookup reads saved monthly income; it does not establish a recording workflow. A receipt uses operation add, shows the month/before/after total and updates that month's MonthlyIncome only on Confirm. Operation replace explicitly sets a monthly total. A receipt is not recurring salary and does not replace other months. There is no separate income-entry ledger; receipt details/status remain in proposal history.

Hypothetical income questions stay read-only and distinguish one-time impact from recurring changes. Monthly savings is not income. Savings affordability uses the saved debt-aware budget; it does not invent a goal, target or deadline or produce an Accept plan card.

## Multiple proposals and confirmation

A complete recording request creates a persisted ChatProposal, not a transaction. Each has an independent ID, immutable reviewed facts and 30-minute expiry. Completed proposals are not incomplete drafts: a new expense uses its own fields even if the model calls it conversational continuation. Earlier completed expenses must not contaminate extraction.

Responses include proposal, proposal_updates and, only where incomplete, record_state. Mobile [useChatSession.ts](../Mobile/src/hooks/useChatSession.ts) sends current-chat proposal_ids, active_proposal_id and signed state and updates cards by ID. Several proposals can remain pending independently. References resolve against owner-verified current-chat history, including dismissed/saved/expired proposals. Ambiguous matches ask which; invented model selectors cannot choose a record.

Only POST /ai/proposals/{proposal_id}/confirm records the validated action. Successful retries are idempotent; expired/dismissed proposals cannot be confirmed. Income confirmation rechecks the reviewed total against current income. Generic Yes never calls this endpoint: pending cards retain facts and remind users to use Confirm/Dismiss.

Dismiss calls the backend. Explicit conversational cancellation also invalidates the selected proposal immediately, without another Yes. Cancelling one leaves others unchanged. Cancelled incomplete drafts receive persisted tombstones. Neither acknowledgments nor old tokens revive them. History lookup does not search unrelated accounts or New Chats.

Corrections do not silently overwrite pending cards. Dismiss the old proposal and create/review a fresh one. Saved transaction editing is unsupported by this interface; Transactions offers add/delete. Savings contributions and loan payments use dedicated screens.

## Goals, debts and topic switches

Goals need user-grounded names/targets. Monthly contribution and total target are separate fields. Follow-up changes retain the active goal; New Chat does not reuse an old cached goal. Protected categories stay protected. Draft figures use saved income and debt-aware targets; proposed cuts remain unsaved until supported explicit acceptance.

Debt planning loads account-owned saved loans, annual APR, principal, term and payment estimates. Natural names and 24-/36-month follow-ups are supported. Missing/ambiguous selection asks clarification. Extra-repayment planning is separate from payment recording. Fixed monthly reducing-balance estimates include recorded payments, but exclude lender fees/settlement adjustments.

Topic switches clear obsolete action/planning context. Standalone amounts after read-only income/budget/debt/expense lookups are ambiguous. Numbers supply values only when an explicitly established current workflow asked for that field.

## Financial Plans

Financial Plans use PlanReview, not ChatProposal. POST /planning/reviews/{review_id}/accept and /reject implement explicit controls. Reviewed facts, owner, expiry and snapshots are checked server-side. Rejected, expired or consumed capabilities cannot be revived by text or old budget/debt tokens. Retries and concurrent acceptance are guarded. Plan history uses plan_updates and Financial Plan wording.

Sending Yes or accept that plan now does not press Accept. Fingerprints reject stale plans. Accepting a savings plan saves its goal/contribution allocation without fake income, expenses or deposits. See [Financial Plans](financial-planning.md) and [database setup](database.md).

The project owner reports physical-device C1?C7 tests passed. Mocked tests verify contracts/safeguards; [live checks](testing.md) exercise the real model. Neither proves universal natural-language understanding. Validation is conservative and English-oriented; informational model prose can still be wrong.
