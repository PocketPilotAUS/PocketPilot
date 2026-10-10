# PocketPilot Developer Handoff: UI Redesign

**Branch:** `feature/khaled-ui` (from `main` at `dd97173`) · **Author:** Khaled
**Scope:** mobile frontend only. No backend changes.

All five main screens now share one design: dark charcoal surfaces, mint/teal accents, rounded cards, and a matching light mode (the sun/moon toggle on Home).

## 1. Redesigned screens

| Tab | Screen file | What it does |
|---|---|---|
| Home | `App.tsx` (dashboard section) | **Financial Overview**: left to spend, income, spent, % of income; add/edit this month's income in place. **Spending Breakdown**: donut chart of this month's categories. **Budget Tracker**: spent vs budget per category (amber ≥ 80%, red when over) and editing of the budget split. |
| History | `src/screens/TransactionHistoryScreen.tsx` | Summary (total + count for current filters), search, filter chips (date incl. custom range calendar, category, amount, sort), rows grouped by day, detail sheet with confirmed delete, pull to refresh, Karim's Recurring Expenses section (unchanged) at the bottom. |
| AI Chat (centre tab) | `src/screens/AIChatScreen.tsx` | **AI Chat**: welcome screen with four suggested prompts, chat bubbles with formatted replies, typing indicator, honest error states with retry, expense/income confirmation cards, New chat. **My Financial Plans**: "coming soon" empty state (see section 5). |
| Add | `src/screens/AddTransactionScreen.tsx` | Large AED amount, icon category grid (same backend values), description, Repeat monthly with payment-day stepper, Save button pinned above the keyboard and tab bar. |
| Insights | `src/screens/AIInsightsScreen.tsx` | Month selector (no future months), overview tiles, PocketPilot Insight summary, 6-month spending trend, category change cards with AI explanations. |

The bottom navigation (`src/components/BottomNavigation.tsx`) is now **Home, History, AI Chat, Add, Insights**, with AI Chat as a raised mint button. Tab keys and navigation logic in `App.tsx` are unchanged.

## 2. Important files

```text
Mobile/src/
  components/
    dashboard/     FinancialOverview, SpendingBreakdown (donut), BudgetTracker, useDashboardTheme
    transactions/  TransactionRow, TransactionDetail, TransactionFilters, DateRangeCalendar,
                   BottomSheet, CategoryIcon (shared icon + colour per category)
    insights/      MonthSelector, InsightsOverview, InsightSummary, SpendingTrend, CategoryChanges
    ai/            ChatWelcome, FormattedMessage, ProposalCard, TypingIndicator, FinancialPlans
  styles/          DashboardStyles (shared palette), TransactionsStyles, InsightsStyles,
                   AIStyles, AddExpenseStyles
  utils/           dashboard.ts      formatting, budget rows, PocketPilot Insight rules
                   transactions.ts   search, filters, sorting, grouping
                   insights.ts       trend and category-change calculations
                   addExpense.ts     Add form validation and request building
                   messageFormat.ts  safe formatting of AI replies
  services/        budgetService.ts (income and budget split saves)
  types/           chat.ts, plans.ts
```

- **One palette:** `getDashboardPalette()` in `styles/DashboardStyles.ts`, accessed through `useDashboardTheme()`. New screens should use it so they match.
- **Logic is separate from UI:** calculations live in `src/utils/` as plain functions, so they can be tested without a phone.
- **The PocketPilot Insight** (one message chosen from spending vs income and budget, never invented figures) is `buildInsight()` in `utils/dashboard.ts`. It now appears on the Insights tab only.

## 3. How the frontend talks to the backend

- Every protected request uses `apiFetch()` (`src/services/apiClient.ts`). It adds `Authorization: Bearer <token>`, and on 401 clears the token and returns to sign-in.
- Endpoints used by the redesigned screens:

| Screen | Endpoints |
|---|---|
| Home | `GET /budget/monthly`, `PUT /budget/income`, `PUT /budget/plan` |
| History | `GET /transactions/`, `DELETE /transactions/{id}`, `GET /recurring/`, `PUT /recurring/{id}`, `POST /recurring/{id}/stop` |
| Add | `POST /transactions/` (one-off, dated today) or `POST /recurring/` (monthly, with `day` and a `request_key` that prevents duplicates) |
| AI Chat | `POST /ai/chat`, `POST /ai/proposals/{id}/confirm`, `POST /ai/proposals/{id}/dismiss` |
| Insights | `GET /budget/monthly`, `GET /spending/compare`, `GET /recommendations/` (backend ±20% rule), `GET /recommendations/ai` (AI explanations), `GET /transactions/` (trend) |

- Request bodies and validation for adding expenses, the chat and confirmations are **the same as before the redesign**. Search, filtering, the trend and the category comparisons are calculated in the app from these responses. The 20% rule and the AI stay in the backend.

## 4. Running and testing with Expo Go

1. **Backend** (`Backend/`):
   - Python 3.12 venv and `pip install -r requirements.txt`.
   - Create `.env` from `.env.example` with your own `JWT_SECRET_KEY`.
   - Run `python init_db.py` for a new database. It also adds any missing tables to an existing one and never changes existing data. For a database from before user accounts, run `python migrate_add_users.py` first.
   - Start it with `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`.
2. **Mobile** (`Mobile/`):
   - Needs Node.js LTS (tested with Node 24); run `npm install`.
   - Set `API_BASE_URL` in `App.tsx` to your computer's LAN address, e.g. from `ipconfig getifaddr en0` on macOS. **Never commit your local IP** (see section 7).
   - Run `npx expo start` and scan the QR code with Expo Go. The phone must be on the same Wi-Fi.
3. **Checks:** `npx tsc --noEmit` and `npx expo-doctor` in `Mobile`; `python -m pytest tests` in `Backend`.

## 5. What works, and what is UI-only or planned

| Area | Status |
|---|---|
| Login, Home, History, Add, recurring expenses, Insights comparisons and trend | Working against the real backend |
| AI Chat replies and AI explanations on Insights | Working **only when Ollama is running** (below). Otherwise the screens show honest "unavailable" messages with retry. |
| Expense/income confirmations from AI Chat | Working (needs AI replies to create them) |
| **My Financial Plans** | **UI only.** No backend storage exists. It shows a "coming soon" empty state; its only button opens AI Chat with a goal question. `FinancialPlan` (`types/plans.ts`) and a `PlanCard` are ready for real data, but nothing creates plans yet, and no fake plans are ever shown. |
| Income transactions | Not supported by the backend. Income is one monthly total edited on Home, so Add has no Expense/Income switch. |
| Choosing an expense date | Not available. Expenses are saved with today's date, as before. |

**AI Chat needs Ollama** (Karim's backend, `Backend/app/ai/client.py`):
- It uses the model `qwen3:4b` with thinking enabled.
- Install the Ollama app, run `ollama pull qwen3:4b` (about 2.5 GB), and set `OLLAMA_URL=http://localhost:11434` in `Backend/.env`.
- Keep Ollama on localhost: the phone only talks to FastAPI.
- Replies can take a minute on an M1. The backend waits up to 180 s and the app up to 200 s.
- Without `OLLAMA_URL`, `/ai/chat` and `/recommendations/ai` return 503 (when there is something to explain).

## 6. Testing done for this branch

- **TypeScript:** `npx tsc --noEmit` passes with 0 errors.
- **Lint:** the project has no ESLint setup, so it was run on a temporary copy. All new and redesigned files have **0 errors and 0 warnings**.
- **Frontend logic tests:** 137 passed (dashboard and insight rules, History filters and grouping, Insights calculations, Add form and request bodies, AI reply formatting). These were run with a temporary bundler outside the repo, because `Mobile` has no test framework yet.
- **Integration:** 25/25 checks of the real frontend code against a running backend with no Ollama. They cover auth, income and budget saves, one-off and monthly expenses (including duplicate protection), History filters and deletes, Insights comparisons and the 20% flag, AI 503 handling, and session expiry.
- **Backend:** `pytest` 293 passed.
- **Visual checks:** iPhone-width previews of every screen and state, plus Khaled's manual check on an iPhone. **Android has not been tested.**

## 7. Known issues and notes for teammates

1. **`API_BASE_URL` is hard-coded in `App.tsx`.** `main` currently contains Karim's local IP (`192.168.1.185`). Each developer changes it locally and must not commit their own. A shared `.env`-based setting (e.g. `EXPO_PUBLIC_API_BASE_URL`) would remove this problem.
2. **Lint errors that were already there** (not from this branch): `AnimatedWelcome.tsx` (10, react-hooks/refs), `MonthlyIncomeCard.tsx` (1), `RecurringExpenses.tsx` (1); plus a duplicate import warning in `App.tsx`.
3. **Old files now unused** (kept so nobody's work is deleted without agreement): `components/IdealBudgetCard.tsx`, `styles/AIChatStyles.ts`, `styles/AIInsightsStyles.ts`, `styles/AddTransactionStyles.ts`, `styles/TransactionHistoryStyles.ts`. `MonthlyIncomeCard.tsx` is only used for its types. These can be removed in a clean-up PR once the team agrees.
4. **Recurring Expenses (History)** still uses the old metallic style. It was left unchanged to avoid editing Karim's component; restyling it is a good follow-up.
5. **`er.name`** at the repo root on `main` is an accidentally committed `git diff` output and can be deleted.
6. **No mobile test framework or ESLint config** is set up yet; adding Jest and `npx expo lint` is a team decision.
7. **The AI only works with Ollama running**, and real AI replies have not yet been tested on a phone.

**Before integrating your work:**
- Pull this branch and run `npm install` in `Mobile` (no new packages were added).
- Restart the backend after pulling.
- New screens: use `useDashboardTheme()`, `apiFetch()`, and the helpers in `src/utils/` instead of hard-coded colours or raw `fetch`.
- Check the 5-tab order before changing `BottomNavigation.tsx`.
