# PocketPilot

PocketPilot is a prototype mobile personal-finance assistant built with **Expo / React Native (TypeScript)** and a **FastAPI / SQLite** backend. It records manually entered expenses, summarizes spending by category, compares months, and supports recommendation endpoints, including optional local AI explanations through Ollama.

> **Prototype notice:** The app has real user accounts: Argon2-hashed passwords on the backend, JWT Bearer authentication, tokens stored in the phone's secure storage, and per-user data isolation. The development API runs over plain HTTP. Do **not** enter real passwords, banking credentials, or sensitive financial records.

## Repository

https://github.com/PocketPilotAUS/PocketPilot

```text
PocketPilot/
  Backend/                 FastAPI API, SQLite, algorithms, tests
    app/main.py            Transaction, spending and recommendation endpoints
    app/routers/auth.py    Register, login and current-user endpoints
    app/core/              Configuration and security (hashing, tokens)
    app/dependencies.py    get_current_user (Bearer token check)
    app/database.py
    app/models/            User and Transaction models
    app/schemas/           Request and response validation
    app/services/          Planning, savings goals, goal dates, spending monitor, budget adjustments
    migrate_add_users.py   Safe migration for existing databases
    migrate_*.py           Feature migrations (each makes a backup first)
    .env.example           Template for Backend/.env
  Mobile/                  Expo React Native TypeScript app
    App.tsx
    src/screens/
    src/styles/            External, theme-aware stylesheets
    src/components/
    src/services/          Backend calls, auth and secure token storage
    src/theme/
  docs/                    Technical documentation and handoff guides
```

## Prerequisites

- Git and Visual Studio Code
- Python **3.12** and pip
- Node.js LTS and npm
- Expo Go on an iPhone (or an appropriate emulator)
- Both phone and development PC on the same trusted Wi-Fi for LAN testing
- Optional for AI: Ollama and the model/configuration expected by `Backend/app/ai/client.py` (previously tested with Qwen3 4B)

## Setup — Windows PowerShell

Clone the repository:

```powershell
git clone https://github.com/PocketPilotAUS/PocketPilot.git
cd PocketPilot
```

Set up the backend in **terminal 1**:

```powershell
cd Backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Open `Backend\.env` and paste the printed value after `JWT_SECRET_KEY=` (see [Environment configuration](#environment-configuration)). Then prepare the database ([Database setup and migration](#database-setup-and-migration)) and start the API:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0
```

If PowerShell blocks activation, use `venv\Scripts\python.exe` for commands instead. Check http://127.0.0.1:8000/docs on the PC.

Start mobile in **terminal 2**:

```powershell
cd Mobile
npm install
npx expo start
```

Open Expo Go on the iPhone and scan the QR code. **Before mobile testing**, find the PC's LAN IPv4 address with `ipconfig` and update the `API_BASE_URL` in `Mobile/App.tsx` from the previous developer's local address to `http://YOUR_PC_IP:8000`. Check `http://YOUR_PC_IP:8000/` in iPhone Safari (the financial endpoints now require a login token, so open those through the app or Swagger). Keep the backend running.

Create an account in the app: accounts from the old demo login are not transferred. After pulling new changes, run `npm install` again in `Mobile` (the app uses `expo-secure-store`, which is included in Expo Go).

## Setup — macOS (Terminal)

Install Python 3.12 if needed (for example with [Homebrew](https://brew.sh): `brew install python@3.12`), then:

```bash
git clone https://github.com/PocketPilotAUS/PocketPilot.git
cd PocketPilot/Backend
python3.12 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Paste the printed value after `JWT_SECRET_KEY=` in `Backend/.env`, prepare the database (next sections), then start the API:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0
```

Start mobile in a second terminal with `cd Mobile`, `npm install`, `npx expo start` (Node.js LTS required, e.g. `brew install node@24`). On macOS, find the LAN address with `ipconfig getifaddr en0`.

## Environment configuration

The backend reads settings from `Backend/.env` (copied from `Backend/.env.example`) or from real environment variables.

| Variable | Required | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | Yes, for login | Signs login tokens. At least 32 characters; generate it as shown above. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token lifetime, 1–1440 minutes. Default 30. |
| `OLLAMA_URL` | Only for AI | Ollama URL, e.g. `http://localhost:11434` (a trailing `/v1` is also accepted). The app uses the model `qwen3:4b`. |
| `OLLAMA_THINK` | No | `true` (default) lets the model reason before answering. Set `false` on slower machines: with reasoning on, a chat reply can take minutes and exceed the 180-second request timeout. |

Secret management:

- **Never commit `Backend/.env`** (it is in `.gitignore`) and never share the secret in chat, screenshots or documents.
- Each developer generates their own secret. Each deployment needs its own, different secret.
- There is no default secret. If it is missing or too short, the API still starts, but logging in and checking tokens fail with HTTP 503 (no one can access protected data), and the reason is written to the server log.
- Changing the secret immediately logs out every user (all existing tokens stop working). Do this if a secret may have leaked.

## Database setup and migration

The database is `Backend/pocketpilot.db` (run commands from the `Backend` folder). It is not committed to Git.

**New database** (no `pocketpilot.db` yet):

```bash
python init_db.py
```

**Existing database** created before user accounts were added: run the migration once, otherwise transaction endpoints fail with `no such column: transactions.user_id`.

1. **Stop the API server.**
2. Preview the changes (modifies nothing):

   ```bash
   python migrate_add_users.py --dry-run
   ```

3. Run the migration:

   ```bash
   python migrate_add_users.py
   ```

What the migration does:

- Creates a timestamped backup first, e.g. `pocketpilot.backup-20261009-153826.db`, and checks it before changing anything. Existing backups are never overwritten.
- Adds only what is missing: the `users` table, the `transactions.user_id` column and its index. Running it again is safe; it reports "Already up to date".
- Makes all changes in one database transaction. If any check fails (for example, transaction data would change), everything is rolled back.
- Never deletes or changes existing transactions.
- Stops without changing anything if the database looks unexpected (missing tables, an old-format `users` table, or a `user_id` column without a foreign key), so a person can review it.

Use `--database path/to/file.db` to migrate a different file.

**Existing transactions become unowned.** They were created before accounts existed, so the migration does not guess who they belong to. They stay in the database but are **hidden from every user** until ownership is assigned on purpose. There is no tool for assigning them yet.

**Existing database from before savings goals:** run `python migrate_savings_goals.py` once (stop the API first). It backs up the database, then adds the optional `manual_savings.goal_id` column; existing savings stay general savings. Other feature migrations (`migrate_debts.py`, `migrate_savings.py`, `migrate_manual_savings.py`, …) work the same way and report "already up to date" when nothing is needed. A new database created with `init_db.py` already has every table and column.

**Restoring a backup:** stop the server, then copy the backup over the database (for example `cp pocketpilot.backup-20261009-153826.db pocketpilot.db`, or `Copy-Item` on Windows). Backups contain the same financial data as the database: keep them private. They end in `.db`, so Git ignores them.

## What works in the current prototype

- Animated welcome screen, metallic/glass UI, dark/light theme toggle
- Registration, login, session restore and logout connected to the backend, with Argon2-hashed passwords and JWT Bearer tokens
- Login tokens stored with `expo-secure-store` (iOS Keychain / Android Keystore); expired sessions return to sign-in
- Per-user data isolation: each user only sees, analyses and deletes their own transactions
- Manual expense entry, including custom category, description and date
- Expense history and deletion with confirmation
- Dashboard total expenses and category breakdown from SQLite-backed API
- Backend monthly spending comparison and deterministic recommendations
- Optional backend AI recommendation explanations via Ollama/Qwen3 (API tested; **not displayed in mobile UI yet**)
- Safe, repeatable migration for existing SQLite databases
- AI Chat recognises a financial goal in normal conversation, builds a verified plan from the saved budget and offers **Accept / Adjust / Reject**; only Accept saves it to My Financial Plans. Deadlines come from the user's own words ("by February 2027", "in six months"), never from model arithmetic
- Savings: extra savings, contributions to a specific savings goal (goal progress updates without double counting), month-end confirmation of a month's savings (only after the month ends), and monthly history
- Spending: planned budget versus recorded expenses, kept separate from savings
- Spending monitoring for the current month with three levels (over budget, savings goal at risk, savings goal unaffordable), shown on Home and in Plans, with Planned versus Projected figures on the Plans Overview
- Optional AI adjustment and recovery plans: validated month-end spending limits, plan options (later deadline), applied only after the user accepts
- Recurring expenses shown as compact rows with an edit sheet
## API quick checks

Full details: [docs/api-documentation.md](docs/api-documentation.md).

- `GET /` — health message (public)
- `POST /auth/register` — create an account (public)
- `POST /auth/login` — log in and receive a token (public)
- `GET /auth/me` — current user's profile
- `POST /transactions/` — create expense
- `GET /transactions/` — list expenses
- `DELETE /transactions/{id}` — remove expense
- `GET /spending/summary` — total and category breakdown
- `GET /spending/compare?year=2026&month=10` — compare months
- `GET /recommendations/?year=2026&month=10` — rules-based advice
- `GET /recommendations/ai?year=2026&month=10` — optional AI explanation
- `POST /ai/chat` — AI Chat; may return a verified, unsaved plan draft
- `GET /planning/plans`, `POST /planning/budget-plans`, `PUT /planning/budget-plans/{id}`, `DELETE /planning/plans/{id}` — saved financial plans (progress includes savings assigned to the goal)
- `GET /planning/status` — this month's spending status and risk level
- `POST /planning/adjustments/proposal`, `POST /planning/adjustments/accept` — AI spending limits (draft, then explicit accept)
- `GET /savings`, `POST/PUT/DELETE /savings/manual`, `PUT /savings/confirm` — savings, goal contributions, month confirmation

All endpoints except the first three require `Authorization: Bearer <token>`.

Use FastAPI Swagger at http://127.0.0.1:8000/docs to test endpoint schemas and responses: register, log in, then click **Authorize** and paste the `access_token`. AI responses require the configured Ollama server, and may be empty when there are no qualifying month-over-month changes.

## Tests

From `Backend` with the environment activated (Windows and macOS):

```bash
python -m pytest tests
```

Use `pytest tests`, not plain `pytest`: plain `pytest` also collects `test_ai_manual.py`, a manual script that needs a running Ollama server. The tests use temporary in-memory databases and a random test secret; they never touch `pocketpilot.db` or need a `.env` file.

The backend suite covers authentication, token validation, password storage, cross-user data isolation, the migration (including repeated runs and rollback) and the original transaction, spending and recommendation behaviour. It also covers AI goal plans and deadlines (`test_proactive_goal_plans.py`, `test_goal_deadlines.py`), savings goals and month confirmation (`test_goal_savings.py`, `test_savings_confirmation.py`), and spending monitoring and AI adjustments (`test_spending_monitor.py`, `test_spending_forecast.py`, `test_plan_recommendations.py`, `test_buffer_warnings.py`). AI calls are mocked in tests; no Ollama server is needed.

`tests/test_planning.py::test_invalid_profiles[patch4]` currently fails: it expects an expense category named "Unknown" to be rejected, but custom budget categories were intentionally allowed in commit c6c6566. The test needs updating by the planning feature's owner.

From `Mobile`:

```powershell
npx tsc --noEmit
npx expo-doctor
```

The Mobile project has no automated test framework or ESLint setup yet; `npx expo lint` sets ESLint up on first run (a team decision). The checks already run and the manual device test checklist are in the mobile authentication handoff document shared with the team.

These are commands to run locally; test results are **not** asserted by this document. Also manually verify register → dashboard → add transaction → history → delete → logout → login → app restart.

## Security notes and deployment considerations

The backend is built for local development on a trusted network. Before any real deployment:

- **Use HTTPS.** Over plain HTTP, passwords and tokens can be read by anyone on the same network.
- **Add rate limiting** to `/auth/login` and `/auth/register` (for example at a reverse proxy). There is currently no limit on login attempts, and each password check uses about 64 MiB of memory (Argon2), so heavy traffic could also exhaust server memory.
- **Use a strong, private `JWT_SECRET_KEY`** from a secrets manager or environment variable, never from a committed file.
- Keep `OLLAMA_URL` on a local or trusted server: AI recommendations send the user's spending categories and percentage changes to it.

Known limitations:

- Tokens cannot be revoked individually; a stolen token works until it expires (30 minutes by default). Changing the secret logs out everyone.
- No refresh tokens, logout endpoint, password change, password reset or email verification.
- Registration reveals whether an email is already registered (HTTP 409). Login does not.
- Pre-migration transactions stay unowned and hidden until a tool to assign them is built.
- SQLite is suitable for development and small deployments only.

## Known limitations / next work

1. Finish device testing of mobile authentication: session expiry, offline start-up and Android (tested on iPhone so far; see the checklist in the mobile authentication handoff document shared with the team).
2. Add income tracking, editing/search/filtering transactions, budgets and savings goals.
3. Implement recurring bills, subscriptions, debt payoff planner.
4. Add charts, AI recommendation cards and a data-grounded AI chat.
5. Build Profile/Settings, notification preferences, reminder system and persistent theme choice.
6. Add rate limiting, HTTPS deployment, token refresh/logout, and password reset.

## Financial planning and spending monitoring

Monitoring runs on the server and is deterministic; AI is only used, on request, to suggest spending limits and wording.

- **Levels** (current month): Level 3 when income minus recorded spending, debt payments, upcoming recurring bills and unpaid debt instalments is less than the monthly contributions of active savings goals. Level 2 when a credible spending forecast leaves less than those contributions, or when the money left after protecting the goal savings is smaller than what the saved budget still needs this month. Level 1 when a category is over budget but the goal remains affordable.
- **Forecast:** fixed bills are not extrapolated; everyday categories use the current spending pace and up to three tracked past months. With too little history, the remaining planned budget is used and no Level 2 is raised from the projection.
- **AI limits:** the server checks every amount (never below what is already spent or due, never above the projection, at most half of the spending still expected in a category) and calculates all totals. Accepting stores the limits for the month and only lowers category budgets; transactions are never changed.

## Git hygiene

`Mobile/App.tsx` contains each developer's local `API_BASE_URL`: do not commit your own IP address.

Never commit `Backend/venv/`, `Mobile/node_modules/`, `*.db` (including migration backups), `.env`, secrets, local credentials or Expo cache. Check `git status` and `git diff --cached` before committing. Documentation and source code can be committed after review.
