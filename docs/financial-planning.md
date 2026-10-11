# Financial planning

My Financial Plans now supports a guided form and persisted per-user plans. Chat and the form share a planning profile; saving a plan is a separate explicit action. Planned costs never become paid transactions through these endpoints.

## Setup

From Backend, run `venv\Scripts\python.exe init_db.py` once after updating to create the additive `planning_profiles` and `financial_plans` tables. Existing records are preserved. Restart FastAPI and reload Expo Go. No new mobile dependencies are required.

## User flow

Open AI Chat → My Financial Plans → Create a Plan. Review household income, additional income, number of people supported, the main goal, target and deadline. Review monthly estimates and choose recorded past months only if they are complete and typical. Blank costs remain unknown unless those months are explicitly confirmed; enter zero only for costs that do not apply. Active recurring bills are suggestions and are not added twice to recorded expenses.

Review My Plan saves the planning profile and calculates a draft. The card explains income, costs, category targets, proposed cuts, shortfall, assumptions and historical comparisons. Save Plan persists the snapshot. The draft also appears in chat; saving it through the form updates its card. Saved plans can be edited or deleted. They persist across sign-out/app restart; conversation history does not.

In chat, extracted planning facts are unconfirmed drafts carried through follow-up turns. The UI links to a prefilled review form. Only an explicit form or plan save updates the persistent profile; model extraction never silently overwrites it. Missing facts are requested. Once the profile is complete, chat can return a server-calculated draft; Save Plan confirms it. Saving or updating income in a planning profile does not change the dashboard's recorded income.

## Calculations and limitations

Income is take-home income plus explicitly supplied additional household income. Baseline expenses are user estimates or category averages from confirmed typical months. Essential categories and user-protected categories are not automatically cut. The first scenario considers reductions of up to 30% across unprotected entertainment, shopping and subscriptions, proportional to their amounts, only where needed to fund the goal. This is an editable product scenario, not a universal recommended spending level. A goal can remain infeasible; the app exposes that shortfall rather than fabricating affordable amounts.

Goal contributions are counted once per calendar month starting in the current month and including the deadline month. Savings growth is not assumed. Debt goal contributions are extra payments after entered minimums; interest/amortization and exact payoff dates are not calculated. A spending-control goal uses its target as a monthly expense ceiling. Household size provides context; the calculator does not invent a per-person food or housing benchmark.

Confirmed history is used for baseline and month-to-month change prompts. Higher essential costs prompt questions rather than automatic cuts. History can be incomplete even when records exist. Users must confirm selected months. Changes to a saved plan's assumptions recalculate it; old saved plans are snapshots rather than automatically refreshed commitments.

## API

All routes require authentication and isolate data by user:

- GET `/planning/context`: saved profile, current income, past month totals and recurring obligations.
- PUT `/planning/profile`: validate/save profile and return a draft or missing fields.
- POST `/planning/preview`: evaluate without saving.
- GET/POST `/planning/plans`: list/save plan snapshots.
- PUT/DELETE `/planning/plans/{id}`: recalculate an owned plan or delete it.

Chat responses add optional `planning_profile` and `plan` fields. The model returns optional `planning` changes; they are validated before use. Financial calculations remain in backend code. Model extraction and live Ollama quality still require manual testing; API tests simulate model replies.
