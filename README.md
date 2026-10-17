# PocketPilot

PocketPilot is a personal finance application built with Expo React Native and FastAPI. It combines user-entered monthly budgets, expenses, recurring commitments, debts, savings and financial plans with an Ollama-powered assistant. Financial changes proposed by AI require explicit confirmation.

## Implemented features

- User registration, login, profile/password settings and rotating refresh sessions.
- Monthly income, editable category allocations and custom categories; Budget Tracker and spending comparisons.
- Expense history, CSV statement preview/import and recurring expense schedules.
- Debt estimates, payment history and optional automatic local payment entries.
- Savings goals, recorded contributions and completed-month savings confirmation.
- Guided Financial Plans, AI goal drafts, preview/adjust/accept/reject, debt-aware fingerprints and stale-budget rejection.
- Spending risk monitoring, budget adjustment proposals and recovery recommendations.
- Light/dark appearance, AED/CNY display and language preferences (translation coverage varies).

See [feature status and limitations](docs/requirements.md). This is a development application, not a bank integration or production financial service.

## Stack and architecture

Expo SDK 57, React Native 0.86, React 19 and TypeScript 6 provide the mobile UI. FastAPI, Pydantic and SQLAlchemy provide authenticated JSON APIs backed by SQLite. Ollama runs the configured local AI service; the current model name is hardcoded as `qwen3:4b` in the backend clients.

Phone / Expo Go -> FastAPI -> SQLite; FastAPI -> Ollama. The backend validates AI proposals and owns persistence. A generated draft is not a saved transaction or plan.

```text
Backend/          FastAPI application, models, services, migrations and pytest tests
Mobile/           Expo app, screens, components, themes and Node-based mobile tests
docs/             Current developer guides, API reference and historical handoff logs
```

## Requirements

Use Python 3.11 as the backend development baseline, Node.js compatible with Expo SDK 57 (22.13 or newer), npm, Git and Ollama. Phone testing requires an Expo Go version compatible with this project's SDK and network access to the backend. No cloud AI API key is required.

## Backend setup (Windows PowerShell)

From the repository root:

```powershell
Set-Location Backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Put the generated value in your private `Backend/.env` as `JWT_SECRET_KEY`. Do not commit it. Supported settings are:

```dotenv
JWT_SECRET_KEY=YOUR_GENERATED_SECRET_AT_LEAST_32_CHARACTERS
ACCESS_TOKEN_EXPIRE_MINUTES=30
OLLAMA_URL=http://localhost:11434
OLLAMA_THINK=false
```

`OLLAMA_THINK=false` disables thinking in the main chat client. It does not change the model name. SQLite uses `Backend/pocketpilot.db` when launched from `Backend`; `DATABASE_URL` and `OLLAMA_MODEL` are not implemented configuration variables.

For a new installation only, create missing tables and start the API:

```powershell
if (-not (Test-Path pocketpilot.db)) { .\venv\Scripts\python.exe init_db.py }
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Existing databases require schema inspection and applicable additive migrations; `create_all` does not add missing columns. Read [database maintenance](docs/database.md) before changing an existing database. API schema: `http://localhost:8000/docs`.

## Ollama

In another terminal:

```powershell
ollama pull qwen3:4b
ollama list
```

Run `ollama serve` only if Ollama is not already running. The backend uses native `/api/chat`, not an OpenAI API key. Model availability, memory and speed depend on your computer. See [configuration](docs/development.md).

## Mobile and Expo Go

From a new terminal at the repository root:

```powershell
Set-Location Mobile
npm ci
npm start
```

Set the existing `API_BASE_URL` constant in `Mobile/App.tsx` locally to `http://YOUR_LOCAL_IP:8000`. Do not commit your personal LAN address. Connect your phone to a network that can reach the computer, permit the development server through the firewall, and scan the Expo QR code. Phone `localhost` is the phone, not your computer. An Expo tunnel does not automatically tunnel the FastAPI server. Android emulator networking and remote devices need their own reachable API address.

## Tests

Backend, from `Backend` (isolated test databases; the excluded end-to-end module runs migration scripts):

```powershell
.\venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests --ignore=tests/test_end_to_end.py -k "not migration"
```

Mobile, from `Mobile`:

```powershell
node --test tests/auth-refresh.cjs tests/chat-recording.cjs
node node_modules/typescript/bin/tsc --noEmit
```

See [testing](docs/testing.md) for coverage, migration-test precautions and known failures. Live Ollama/Expo testing complements mocked automated tests.

## Developer documentation

Start with the [documentation index](docs/README.md), [architecture](docs/system-architecture.md), [API reference](docs/api-documentation.md), [AI workflows](docs/budget-goal-chat.md) and [security assessment](docs/security-self-assessment.md).

## Development status

No bank synchronization, real payment execution, transaction editing API, password recovery/email verification or push notification service is implemented. AI extraction remains fallible; unsupported/ambiguous operations require clarification. Some read-like operations synchronize recurring/debt entries, so the app is not a passive bank ledger. Savings figures represent recorded entries, not verified balances. Review the detailed guides before deployment; production hardening and full localization remain work.
