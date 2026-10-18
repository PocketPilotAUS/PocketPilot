> Historical handoff record. Earlier status and test counts may be superseded. Use the [current documentation index](README.md) for current behavior.

> Current implementation note: earlier claims about local-only rejection, missing draft persistence, placeholder screens or test totals describe their historical milestone. Current AI proposals/reviews have durable status and expiry; setup requires the plan-review migration. See [AI lifecycle](budget-goal-chat.md), [Financial Plans](financial-planning.md), [database](database.md) and [testing](testing.md).

# PocketPilot phase 2 handoff log

This phase starts after the developer handoff for commit `f9c3eb1`. Add each new change here so the next handoff includes implementation details, verification, setup requirements and remaining work. These entries describe local changes; they do not imply a commit, push or merge.

## 13 October 2026 Financial Plans navigation

### Request and resulting behavior

Move My Financial Plans out of AI Chat into its own bottom navigation tab beside AI Chat. The bottom tabs are now Home, Transactions, AI Chat, Plans and Insights. AI Chat no longer includes the Chat and My Financial Plans segmented control. The Plans screen still displays the full My Financial Plans heading and existing saved-plan and guided-form features.

### Implementation

- `Mobile/src/screens/FinancialPlansScreen.tsx` wraps the existing `FinancialPlans` component in a safe-area screen using the existing external AI theme styles.
- `Mobile/src/components/BottomNavigation.tsx` adds the `financialPlans` destination with a Target icon directly after AI Chat. `Mobile/src/preferences/languages.ts` supplies the compact Plans tab label in all 21 selectable languages.
- `Mobile/App.tsx` owns the proposed planning profile and routes it from chat to Plans. The new destination participates in session-expiry handling. The profile is cleared on logout, password-change logout and session expiry, and ordinary entry from another bottom tab opens the saved plans list.
- `Mobile/src/screens/AIChatScreen.tsx` removes its internal plans section and delegates profile review to the app. Chat messages, inline draft plan cards, saving draft plans, transaction proposals and the composer remain available.
- Plan with AI Chat returns to the existing app-level conversation and fills the planning prompt. Guided previews and saved plans still use the existing chat-session preview callback. Saved plans are reloaded by the existing component when the destination mounts.

### Setup and data impact

Frontend changes only. No new dependency, environment variable, backend route or database migration. Preserve each developer's existing API address. Existing saved financial plans are not deleted or changed by moving the screen. Guided form state still follows the existing screen-state navigation lifecycle and should be checked when switching tabs with unsaved edits.

### Validation

- TypeScript `node node_modules/typescript/bin/tsc --noEmit` passed.
- Local mocked component check `check-plans-tab.cjs` passed: five-tab order, selected Plans tab, navigation callback, all 21 tab translations, no embedded plans tab in Chat, proposed profile forwarding, retained chat composer and standalone Plans callback forwarding. This check resides in the Codex workspace rather than the repository test suite.
- `git diff --check` passed for the modified tracked navigation and chat files.
- `npm.cmd run lint` could not run because `Mobile/package.json` has no lint script. No lint tooling was installed.
- Device layout and live backend interactions were not exercised for this navigation change.

### Team review checklist

Check the five-tab layout on a narrow phone, Arabic and Mandarin labels, theme appearance and keyboard visibility. Open saved plans; create, edit and delete a plan; review a profile proposed in chat; return using Plan with AI Chat; verify the conversation persists and session expiry returns to login. Agree on the navigation before merging into main.

## 13 October 2026 Chinese yuan currency support

### Request and resulting behavior

Add Chinese yuan to Currency settings and convert previous history and all supported financial records when selected. AED and CNY are selectable. Original records remain AED; CNY displays history, income, budgets, recurring payments, plan amounts and charts using a dated reference rate. New monetary form entries use the selected currency. Currency choice is remembered per device, and switching back to AED leaves original values intact.

### Implementation and setup

- New `Mobile/src/preferences/currency.ts` provides rate validation, persisted preference parsing, display/input conversion, draft rounding and planning profile normalization. `PreferencesContext.tsx` saves selection and rate atomically; `App.tsx` waits for restoration before rendering financial forms.
- Settings selects AED/CNY and can refresh the reference rate. `services/currencyService.ts` uses the public AED ExchangeRate-API feed with timeout and daily caching. `CurrencyNotice.tsx` and `CurrencyStyles.ts` show the rate/date and required provider link. First-time CNY selection requires internet; previously selected CNY can use an expired cached rate offline with a visible Cached rate label.
- `LocalizedNative.tsx` converts canonical AED money text with Mandarin/Arabic localization. Separate helpers convert unlabeled chart values and already-CNY budget review amounts without multiplying twice. The currency settings copy is localized too.
- Financial overview, legacy income card, budget setup, expense entry, recurring schedule editing, planning forms and transaction amount filters normalize selected-currency inputs before saving/comparing AED values. Form validation still rejects blank/invalid drafts. Unchanged edit amounts preserve original values when possible. Dates, percentages and household size retain their units.
- Backend `app/core/currency.py` projects financial context into CNY and normalizes structured model drafts to AED. `/ai/chat` accepts selected currency/rate, keeps old message units explicit, and retains confirmation before writing expenses/income. Other backend data APIs continue to use AED.
- Updated `docs/account-settings.md` to describe CNY and the Home-only settings entry. Added `docs/currency-display.md` with units, rounding, caching, attribution, request compatibility and verification details.

No database migration, paid exchange-service subscription, API key or new dependency was added. Run the matching frontend/backend revisions together; restart the backend if auto-reload is disabled. The existing account-settings migration is unrelated to this change.

### Verification and remaining review

Backend pytest: **341 passed**. TypeScript and local currency/preference/form component checks passed. The live public AED rate endpoint returned a valid CNY rate. Checks cover invalid rates/currencies, confirmation-only writes, original context preservation, planning draft units, no double conversion, locale catalogs, cached rates, failed storage/network requests, budget review/save, expense/monthly saves, recurring edits and planning fields. Local frontend check scripts are kept in the Codex workspace and are not a committed test runner. Lint remains unavailable because there is no package lint script.

Amounts use the current/cached reference rate for every historical record; transaction-day historical rates are not implemented. Conversions are approximate and round to cents. Device layout and live Ollama understanding of CNY need a manual check. Check Settings currency switching/restart, history totals, income/budget edits, recurring and planning forms, CNY amount filters and confirmed AI proposals. No commit, push or merge was performed for these changes.

The user asked about performance, then explicitly requested keeping CNY support. Rate requests occur on currency selection/refresh after cache expiry, not per record or screen. Monetary formatting is local, conversion patterns are compiled once, and no additional model request is made. A laptop formatting microbenchmark was run; it is not a native-phone render measurement. Do not describe mobile performance as device-verified.

## 13 October 2026 CSV bank statement import

### Request and delivered scope

Start small with statement upload and AI-assisted distinction of expenses, income and transfers. Transactions now includes Import bank statement, opening a file/review modal. The first version accepts UTF-8 CSV only, with 50 transaction rows and 128 KB limits. The user chooses the statement's actual currency, date order and single-column debit sign convention before choosing the file. Parsed dates/amounts are fixed; AI suggests labels/categories. Preview never saves data. Only selected debit expenses are imported after confirmation; credits, income and transfers are not automatically imported.

### Implementation

- `Mobile/src/screens/StatementImportScreen.tsx`: picker, configuration, row review, category editing, inclusion controls, duplicate opt-in and explicit save. Copied picker files are cleaned only within the app cache. `StatementImportStyles.ts` supplies external theme-aware layout.
- `TransactionsScreen.tsx` hosts the import modal and refreshes history after success. `TransactionHistoryScreen.tsx` adds the import action. Existing manual expense entry remains available.
- `services/statementService.ts`: authenticated preview/confirm requests with timeout. Currency choice is separate from the statement currency; converted amounts stay canonical AED. `CurrencyNotice.tsx` can show the reference rate pinned for the import. New UI copy includes Mandarin and Arabic translations.
- `Backend/app/services/statement_import.py`: deterministic CSV parsing, required headers and aliases, directions, date/currency/precision/size checks, row errors, duplicate flags and transfer guards.
- `Backend/app/ai/statement.py`: one qwen3:4b classification request with constrained schema, thinking disabled, 2200-token cap and 25-second timeout. Only IDs, truncated descriptions and money direction are sent, not full CSV headers, dates or amounts. Failed or incomplete suggestions allow manual review.
- `Backend/app/routers/statement_import.py` and `app/main.py`: preview and confirmation routes. A user-bound signed 20-minute preview fixes financial facts. Confirm rejects invalid ownership/selection and credits, serializes SQLite writes, skips exact duplicates and commits atomically. No new table or database migration.
- Added `docs/statement-import.md` and the synthetic `docs/examples/statement-sample.csv` for teammates.

### Setup and verification

Expo document-picker and file-system dependencies were installed using the SDK 57 compatibility installer. The first installer attempt hit a restricted Expo cache; the offline compatibility path used the local SDK manifest and npm completed installation. Teammates should run `npm.cmd ci`, restart Metro and run the matching backend revision. Existing custom development builds require rebuilding for the native modules; matching Expo Go includes them. Existing OLLAMA_URL/qwen3:4b and JWT configuration are reused. No new external AI provider or paid service was added.

Full backend suite: **356 passed**. Final focused statement tests: **15 passed**, including the date-bounded confirmation lookup. TypeScript passed; lint is still unavailable because package.json has no lint script. Mocked mobile flow checks passed for required bank currency, file read/cache cleanup, read-only preview, conservative defaults, credit exclusion, category/type correction, duplicate opt-in and explicit confirmation. A live Ollama smoke check with two synthetic rows returned the expected Food expense and salary income suggestions. Actual phone picking/layout and a real bank export still need team testing.

### Limits for the next handoff

CSV English headers must be on the first row; bank-specific mapping, PDF/OCR, income/refund/transfer import, bank reference IDs and larger batches are future work. Invalid rows are explicitly reported and above-limit files are rejected without truncation. Exact duplicate matching can also skip genuinely separate identical purchases, which must currently be added manually. CNY records use a pinned approximate reference rate; original date/amount/source currency remain visible in review. The preview expires after 20 minutes. No changes were committed, pushed or merged for this phase.

## 13 October 2026 Clearer financial plan comparison bars

The user reported that the category bars were difficult to understand. FinancialPlanCard now gives every category the same bordered layout: Current label and monthly amount above the grey bar, Proposed label and monthly amount above the mint bar, then an explicit No change proposed, Suggested reduction or Proposed increase message. Both tracks occupy the same full width with matching height and spacing. The existing common numerical scale remains the largest current/proposed category amount; a caption explains what a full bar means and visible zero/midpoint/maximum labels show the shared scale. Equal current/proposed values produce equal lengths. Comparison scale and amounts use the selected currency through the existing currency layer. This is a comparison of monthly category estimates, not a savings or payment-progress indicator.

Changed FinancialPlanCard.tsx, external PlanningStyles.ts and Mandarin/Arabic UI copy. Plan calculations, saved records and backend routes are unchanged. TypeScript and diff checks are the validation for this presentation change; phone layout remains a manual review item. No new dependencies, migration, commit, push or merge.

## 13 October 2026 Home sections and Spending page

### Requested scope and behavior

Home keeps Financial Overview and presents three section buttons in the professor's requested order: Debt, Spending, Savings. Spending opens a separate screen containing the existing Spending Breakdown and Budget Tracker. Debt and Savings are disabled placeholders labelled Coming soon. This change implements only the buttons and the relocation of existing spending features; no debt balances, savings records, month-end calculation or rollover was added.

The user stated the intended future savings rule: remaining money after debt and spending at month end should count as savings. Record this as future product intent, not implemented behavior in this change. Existing Remaining figures continue to use their current calculations.

### Implementation and compatibility

- `Mobile/src/components/dashboard/HomeSections.tsx` provides the ordered Home buttons with icons and clear disabled states. `HomeSectionsStyles.ts` supplies external theme-aware layout.
- `Mobile/src/screens/SpendingScreen.tsx` reuses the existing SpendingBreakdown and BudgetTracker with the current data, loading/error feedback and callbacks. The screen has a Back to Home button and remains inside bottom navigation with Home selected as its parent area.
- `Mobile/App.tsx` adds the spending screen state, moves the two components out of Home, refreshes monthly data on entering Home or Spending and includes Spending in session-expiry handling. Income editing stays on Home. Add Expense still opens the Transactions form. Budget setup/editing updates shared dashboard data and AI review still opens the existing chat session for the selected period.
- Mandarin/Arabic labels were added, and `docs/user-budgets.md` now describes entry through Spending.

Frontend-only change with no dependency, database migration, backend API or stored record change. TypeScript passed and diff checks were run. Lint remains unavailable because there is no lint script. Actual phone layout is not verified; check the button order, placeholder disabled states, Spending/back navigation, budget setup/edit, expense entry, AI review and AED/CNY display on the device. No commit, push or merge performed.

## 13 October 2026 Debt tracking

Home > Debt is now enabled and opens a separate account-owned debt page with total outstanding principal, estimated combined monthly payments and estimated remaining interest. Users can add, edit and delete named debts. Required inputs: outstanding principal, annual interest rate and remaining years plus extra months; original principal is optional. Zero outstanding balance is supported. Original principal minus outstanding is labelled Principal reduced; if outstanding exceeds original, show explanatory text instead of a progress bar. No automatic balance reductions or transaction/budget/savings writes.

Implementation: new Debt SQLAlchemy model, authenticated /debts CRUD router with owner isolation and Decimal validation, mobile DebtScreen/debtService/external DebtStyles, HomeSections/App navigation and Mandarin/Arabic copy. Reuses existing theme, metallic glass cards, currency conversion and session-expiry handling. Values stored in AED; CNY editor amounts convert through existing rate and preserve unchanged AED values. Estimates use fixed-rate reducing-balance monthly amortization, with an explicit zero-interest branch; excludes fees and variable/flat-rate arrangements.

Setup: new Backend/migrate_debts.py backs up an existing SQLite database and adds only debts plus owner index, idempotently. Run from Backend before using Debt on other installations; fresh init_db.py creates it through registered models. Local migration applied successfully on 13 October: pocketpilot.backup-debts-20261013-212400-220641.db created first. No existing data rewritten, no dependency/env changes. Missing debt storage returns a setup error rather than a generic database crash.

Validation: 14 focused backend tests passed, covering known estimates, zero/small rates, CRUD, owner isolation, authentication, invalid inputs and migration backup/idempotence. Mobile TypeScript passed; lint remains unavailable because no lint script exists. Phone layout remains unverified. See docs/debts.md for API, assumptions and teammate setup. No commit, push or merge.
Full backend regression suite completed: 370 passed in 58.12 seconds.

## 13 October 2026 Debt UI consistency fix

Replaced the Debt page gradient/blur cards and oversized repeated headings with the same shared DashboardStyles used by Home Financial Overview and Spending. Total debt now uses the shared hero amount; combined monthly payments and remaining interest appear in the familiar raised stat tiles. Each debt repeats this visual hierarchy with compact labels, the shared progress track and a mint icon badge. Your debts section has a matching Add debt pill; editing uses a neutral Pencil action and deletion a red Trash action with the existing confirmation.

Form inputs now follow the Home income editor: dark/light theme-aware surfaces, currency prefixes, percentage suffix, shared solid mint Save and neutral Cancel buttons, aligned years/months fields, disabled/pressed feedback. Validation errors appear inside the form. Added matching empty/loading/error states and Mandarin/Arabic labels for the new headings. External DebtStyles contains only Debt-specific layout; core card/typography/input/button/progress styles are shared directly with the dashboard.

Changed only Mobile/src/screens/DebtScreen.tsx, Mobile/src/styles/DebtStyles.ts, Mobile/src/preferences/uiTranslations.ts and this log. Debt CRUD, saved amounts, calculations, API and database remain as implemented. TypeScript passed. Lint unavailable (no configured lint script). Actual phone rendering remains unverified; check light/dark, Arabic, long names/large amounts and form layout in Expo Go. No migration, dependency, commit, push or merge for this UI fix.

## 13 October 2026 Consistent left-side back buttons

Added shared Mobile/src/components/BackButton.tsx and external NavigationStyles.ts. All screen back arrows now use the same 44px square, 14px rounded corners, 22px left arrow, border, pressed/disabled feedback and translated accessibility label. Spending and Debt now put the arrow before the heading on the physical left. Settings, Personal Details, Login and Register use the same component. Header/toolbar direction is explicitly LTR to keep the requested physical-left placement in Arabic; text retains its existing language direction. Auth buttons use the existing auth palette, with matching geometry and spacing.

Preserved navigation destinations, Settings subsection behavior, Personal Details unsaved-change confirmation and busy guards. Modal close X controls remain close controls. No new back routes added to primary bottom-navigation tabs. TypeScript passed; lint unavailable because no lint script is configured. Phone appearance still needs an Expo Go check. No backend, database, dependencies, commit, push or merge changes.

## 13 October 2026 Compact financial plan list and separate details

My Financial Plans now lists compact tappable rows containing the plan name, Saved plan status and a chevron. Full FinancialPlanCard charts, category bars and recommendations mount only in the selected plan's detail view, instead of every saved plan being expanded in the list. FlatList virtualizes the compact rows. Plan names remain user text, with up to two visible lines. Create a Plan and Plan with AI Chat remain available above the list, alongside loading/error/retry and empty states.

The plan view owns a dynamic header: My Financial Plans on the list; Plan details on a selected saved plan or draft preview; Create a Plan/Edit plan for the form. Details and forms use the shared left BackButton. Selecting a plan uses the already-loaded record; no additional request per tap. Saved-plan edit and delete controls remain in details. Cancelling an edit returns to that saved plan. Preview retains Save and Adjust Details; successful save/update opens the returned saved record and updates its list row without duplicating the plan. Successful delete returns to the reduced list. PlanningForm reports request activity to disable header back while generating a preview. Existing chat preview callbacks remain unchanged. Drafts still follow the existing review/save flow; this change adds no draft persistence or new database fields.

Files: components/ai/FinancialPlans.tsx, components/ai/PlanningForm.tsx, screens/FinancialPlansScreen.tsx, styles/PlanningStyles.ts and preferences/uiTranslations.ts. New heading/hint/status copy includes Arabic and Mandarin. All styles remain external and theme-aware.

Validation: TypeScript passed. Workspace mocked-component navigation check passed for compact list without chart cards, tap/detail/back, edit/cancel, preview/update keeping the same ID and delete returning to list. Lint unavailable because no lint script exists. Actual phone layout remains unverified; check several plans, long titles, Arabic, preview and back navigation in Expo Go. No backend/API/database/dependency changes, migration, commit, push or merge.

## 14 October 2026 Monthly Savings page

Enabled Home > Savings with the existing Debt, Spending, Savings order and matching dashboard cards, shared left BackButton, theme-aware inputs/stat tiles and bottom-navigation Home parent state. Added SavingsScreen, external SavingsStyles and savingsService; Arabic/Mandarin copy accompanies the new page. Savings has a total confirmed savings card, current/selected month's estimate, month navigation and confirmed monthly history. Tap history to review/update a month.

Calculation: income minus recorded monthly spending minus actual debt payments missing from spending (user-entered, default zero). Recorded spending includes any already-entered debt payment and is subtracted once. Debt-page loan balances/estimated payments are not assumed to be paid. The missing-debt-payments field explicitly explains this; it does not create transactions or change debt balances. Current month remains estimated until completed, then an explicit confirmation dialog asks whether all costs are entered and the leftover was actually saved. Negative leftover is a shortfall with zero saved contribution; missing monthly income blocks confirmation. Total is cumulative confirmed contributions, not a bank balance, opening savings balance or withdrawal tracker.

Backend: account-owned MonthlySavings table stores income/spent/extra debt/saved snapshot integer AED cents with a unique owner/year/month constraint. GET /savings returns selected monthly actuals, eligibility, confirmed total and history. PUT /savings/confirm computes saved amount server-side and replaces the same month's confirmation idempotently. UAE UTC+4 month-end cutoff; client sends expected income/spent and stale records produce 409 requiring refresh. Recurring expenses sync through existing budget behavior before the locked confirmation snapshot. SQLite BEGIN IMMEDIATE guards snapshot/upsert; owner comes exclusively from verified authentication. Confirmed months do not silently change after transaction/income edits; user must review/update explicitly. CNY uses existing conversion, preserving unchanged extra-debt AED values.

Setup: Backend/migrate_savings.py is additive/idempotent, backs up SQLite before adding monthly_savings plus owner index, and leaves other data untouched. Applied locally: pocketpilot.backup-savings-20261014-114654-411850.db created before migration. Teammates must run the migration from Backend for existing databases; fresh init_db.py creates the registered table. No new dependencies, environment variables or secrets. See docs/savings.md.

Validation: 11 focused backend tests passed for confirmation, double counting, idempotent updates, shortfalls, missing income, stale snapshot/history stability, ownership/auth, invalid values, current-month guard and migration backup/idempotence. Mobile TypeScript passed. Workspace mocked UI flow passed current-month guard, past-month navigation, missing debt amount, explicit dialog, confirmed total/history update and invalid/shortfall feedback. Lint unavailable because no lint script exists. Phone layout still needs Expo Go review. No commit, push or merge.
Full backend regression suite completed: 381 passed in 99.34 seconds. Final TypeScript and diff checks passed.
