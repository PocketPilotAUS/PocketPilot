# AI Chat, recording and goal planning

[chat.py](../Backend/app/routers/chat.py) handles `POST /ai/chat`. The request includes conversation messages, display currency/language and optional carried planning context. Backend facts are scoped to the authenticated user: saved monthly budget, actual spending, debt balances/obligations and saved goals/contributions. Planned savings, actual contributions and outstanding debt are labeled separately.

## Intent and recording

[chat_context.py](../Backend/app/services/chat_context.py) gates intent server-side. Read-only income, budget, spending, debt and savings questions cannot create pending actions merely because Ollama returns an action. Current-month English income/budget lookups use saved values directly; other informational answers use scoped context and remain model-generated. Ambiguous write intent asks whether the user wants to view or record data.

Explicit supported income/expense recording takes precedence over carried goal mode while preserving goal context. A valid action becomes a user-owned pending proposal, never an immediate ledger change. Null, malformed or unsupported model actions receive controlled clarification rather than arbitrary internal model commentary. Model output containing both a transaction action and planning data cannot create two competing confirmation controls.

For expenses the action amount must match one monetary amount evidenced by the request. Dates are masked before amount extraction; multiple monetary values require clarification. Category evidence must match the proposal using existing aliases (for example groceries -> Food and transportation -> Transport) or an explicit custom label. Missing/ambiguous categories and conflicting proposed amounts are not guessed.

[chat_records.py](../Backend/app/services/chat_records.py) resolves today/yesterday/tomorrow using UAE UTC+4 and overrides conflicting model dates. Valid explicit dates are retained; ambiguous dates request clarification. Income this/last/next month is resolved deterministically. These transaction rules do not replace separate goal-deadline calculations.

Pending replies are built from validated proposal data: amount, category and exact date/month. They say confirmation is required and do not claim saved totals. `/ai/proposals/{proposal_id}/confirm` persists the validated action; `/dismiss` rejects it. Confirmation and ownership checks remain server-side. Requests to edit transactions or record savings contributions are redirected to supported workflows rather than converted to new expenses.

## Goal planning

Goal extraction merges supplied planning fields without interpreting generated empty defaults as user deletion. Budget-backed plans use saved income and debt-aware category targets; the backend computes the actual draft. The response reconciles wording with draft figures and explicitly says nothing has been saved.

Accept, Adjust and Reject are distinct from transaction confirmation. Preview/accept enforce the same budget fingerprint; stale drafts require refresh. Sending a new message does not accept an older plan. Mobile separates general chat busy state from the specific plan being saved; only that plan's actual acceptance displays Saving. Older cards remain in history. A transaction proposal suppresses plan controls on its own response.

Model instructions request `action: null` for informational questions, but server intent/validation is the safeguard. Natural-language coverage remains limited; monetary/category parsing is conservative and mainly English. Read-only generated prose is not independently verified in every case. See [planning](financial-planning.md), [security assessment](security-self-assessment.md) and [tests](testing.md).
