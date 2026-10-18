# PocketPilot

PocketPilot is a personal finance app for monthly budgets, expense and income tracking, debts, savings goals and financial planning. An Ollama-powered assistant understands financial questions and prepares reviewable proposals. The backend validates financial facts and calculations; conversational agreement alone does not save financial changes.

## Features

- Accounts: registration/login, profile and password settings, rotating refresh sessions and logout.
- Month-specific income, named/custom category allocations, Budget Tracker and spending comparisons.
- Expense add/list/delete, recurring schedules and reviewed CSV expense import.
- Savings goals, manual contributions, goal progress and completed-month savings confirmation.
- Saved loans, annual-rate installment estimates, payment history, opt-in automatic local ledger entries and accelerated-repayment advice.
- Guided and budget-backed Financial Plans, previews, acceptance/rejection, stale-snapshot checks and spending-risk monitoring.
- AI Chat: natural recording requests, follow-ups, budget/income lookups, savings affordability, saved-debt advice and topic switching.
- Confirmation safety: independently actionable transaction proposals, explicit Confirm/Dismiss controls, durable plan rejection, ownership checks, expiry and retry/concurrency protection.
- Dark/light appearance, AED/CNY display, partial localization and a locally bundled transparent welcome logo.

A plan allocation is not an actual expense, savings deposit or bank transfer. See [feature scope](docs/requirements.md).

## Technology and architecture

~~~text
Phone (Expo / React Native)
  -> FastAPI -> validated financial services -> SQLite
             -> Ollama native /api/chat -> qwen3:4b
Phone -> public AED/CNY reference-rate feed (no financial ledger sent)
~~~

| Layer | Implementation |
| --- | --- |
| Mobile | Expo ~57.0.27, React Native 0.86.3, React 19.2.3, TypeScript ~6.0.3 |
| Modules | SecureStore, AsyncStorage, DocumentPicker, FileSystem, Blur, LinearGradient, SVG, Lucide |
| Navigation | Screen state in Mobile/App.tsx; no Expo Router |
| API | FastAPI, Pydantic, Uvicorn, SQLAlchemy; pins in Backend/requirements.txt |
| Authentication | Argon2id passwords, HS256 access JWTs, hashed rotating refresh tokens |
| Database | SQLite, foreign keys enabled; canonical financial currency AED |
| AI | Ollama / qwen3:4b through HTTPX structured requests |
| Testing | pytest / FastAPI TestClient, Node test runner, TypeScript |

The OpenAI Python package is present in requirements, but current AI clients call Ollama directly. No OpenAI account or API key is required.

## Repository structure

~~~text
PocketPilot/
  README.md
  Backend/
    app/
      main.py          API application and core transaction/spending routes
      routers/         Auth, budgets, chat, plans, debts, savings, CSV import
      services/        Financial rules, context, drafts and confirmation lifecycles
      algorithms/      Budget/spending/debt calculations
      ai/              Ollama clients and prompts
      core/            Security, configuration, currency and language helpers
      models/          SQLAlchemy models
      schemas/         Validation
    init_db.py
    migrate_*.py       Existing standalone migrations; keep here
    requirements.txt
    .env.example
    tests/             Automated tests and opt-in live Ollama harnesses
    docs/              Feature cross-reference
  Mobile/
    App.tsx            Screen navigation and API address
    app.json           Expo configuration (portrait orientation)
    assets/            Bundled images
    src/               Screens, components, hooks, services, types, styles, preferences
    tests/             Node regression tests
    package.json
    package-lock.json
  docs/                Maintained guides and historical handoff logs
~~~

Virtual environments, node_modules, private environment files and databases are not distributed source. Keep the existing database and migration layout unchanged.

## Prerequisites for Windows

Install these tools and reopen PowerShell so PATH changes take effect:

| Requirement | Version / guidance |
| --- | --- |
| Windows | Ollama installer requires Windows 10 22H2 or newer; Windows 11 is suitable |
| Python | 3.11 baseline, locally checked with 3.11.9; include the Python launcher |
| Node.js / npm | Node 24 is the verified local baseline: 24.20.0 / npm 11.19.0; Expo SDK 57 specifies Node 22.13.x minimum |
| Git | Git for Windows; no project-specific minimum declared |
| Ollama | Native Windows app; local CLI checked with 0.40.6 |
| Mobile runtime | Expo Go compatible with SDK 57, or a matching development build |
| Network | Reachable private Wi-Fi; internet for initial downloads and uncached exchange rates |

Official references: [Python on Windows](https://docs.python.org/3.11/using/windows.html), [Node.js](https://nodejs.org/en/download), [Git for Windows](https://git-scm.com/install/windows), [Ollama for Windows](https://docs.ollama.com/windows), [Expo setup](https://docs.expo.dev/get-started/set-up-your-environment/). [Expo SDK 57](https://docs.expo.dev/versions/v57.0.0/) specifies Android 7+, iOS 16.4+ and React Native 0.86; the installed runtime may have additional requirements.

Ollama speed depends on available CPU/GPU and memory. No verified minimum RAM/VRAM is specified by this project. The Windows + compatible Expo Go path does not require a separate database server, paid AI service, global Expo CLI, Android Studio or Xcode. Development builds require their own build setup; no eas.json is supplied.

~~~powershell
py -3.11 --version
node --version
npm.cmd --version
git --version
ollama --version
~~~

Use npm.cmd in PowerShell to avoid npm.ps1 execution-policy issues. The virtual environment is invoked directly below; activation and execution-policy changes are unnecessary.

## 1. Obtain the source

Use your team's repository URL; no public URL is assumed:

~~~powershell
New-Item -ItemType Directory -Force C:\dev | Out-Null
Set-Location C:\dev
$repositoryUrl = Read-Host "Paste the PocketPilot clone URL"
git clone $repositoryUrl PocketPilot
Set-Location PocketPilot
git switch fix/ai-natural-language
~~~

The branch must be available in the clone. Alternatively, extract the team's source archive and open PowerShell in its PocketPilot root. These instructions require the current implementation, including migrate_plan_reviews.py. Uncommitted changes are not available in a remote clone until separately shared.

## 2. Backend installation and environment

From the repository root:

~~~powershell
Set-Location Backend
py -3.11 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
notepad .env
~~~

Paste your generated secret into your private .env. Example values:

~~~dotenv
JWT_SECRET_KEY=REPLACE_WITH_YOUR_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
ACCESS_TOKEN_EXPIRE_MINUTES=30
OLLAMA_URL=http://localhost:11434
OLLAMA_THINK=false
~~~

| Variable | Meaning |
| --- | --- |
| JWT_SECRET_KEY | Required for auth and signed drafts; private random secret, at least 32 characters |
| ACCESS_TOKEN_EXPIRE_MINUTES | Integer 1?1440, default 30 |
| OLLAMA_URL | Required for AI calls; base URL of your trusted Ollama host |
| OLLAMA_THINK | Main client defaults to true; false/0/no/off disable thinking. False is practical on slower hardware |

Clients normalize an optional /v1 suffix and call native /api/chat. The model name qwen3:4b is fixed in source: OLLAMA_MODEL is not implemented. DATABASE_URL is not an environment setting either: database.py uses sqlite:///./pocketpilot.db. Start from Backend so the file resolves consistently. Refresh sessions last a fixed seven days, independently of access-token lifetime.

## 3. Initialize a new database

Only for a fresh installation with no existing financial database, from Backend:

~~~powershell
if (Test-Path pocketpilot.db) { throw "Existing database: follow docs/database.md first." }
.\venv\Scripts\python.exe init_db.py
.\venv\Scripts\python.exe migrate_plan_reviews.py
~~~

Both commands are required. The initializer creates models registered by app.models; the second script explicitly registers and creates financial_plan_reviews, which the standalone initializer does not import. Importing the API alone does not initialize SQLite.

For an existing database, stop writers, back up consistently, inspect schema and follow [database maintenance](docs/database.md). create_all does not add missing columns. Do not reset financial data or move migration files to fix a schema error.

## 4. Ollama setup

Install and open Ollama for Windows. In another PowerShell terminal:

~~~powershell
ollama pull qwen3:4b
ollama list
Invoke-RestMethod http://localhost:11434/api/tags
~~~

The Windows app normally runs its server in the background. If it is not running, use a dedicated terminal:

~~~powershell
ollama serve
~~~

Do not start a second server if Ollama already owns port 11434. Optionally run ollama run qwen3:4b to test interactively; type /bye to exit. The backend needs the server and downloaded model, not a permanently open interactive chat.

## 5. Start the backend

From Backend:

~~~powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
~~~

Leave it running. In another terminal:

~~~powershell
Invoke-RestMethod http://127.0.0.1:8000/
~~~

Expected message: PocketPilot API is running. Browse [localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation; /openapi.json is the machine-readable schema. Financial/account routes require Bearer authentication. Root health does not verify model readiness or migrations.

## 6. Install mobile dependencies and connect a phone

In a new terminal at the repository root:

~~~powershell
Set-Location Mobile
npm.cmd ci
ipconfig
~~~

Find the active Wi-Fi IPv4 address, not the gateway or a VPN/virtual adapter. Edit the existing API_BASE_URL constant in Mobile/App.tsx locally:

~~~typescript
const API_BASE_URL = "http://YOUR_PC_WIFI_IPV4:8000";
~~~

Replace the placeholder with the actual address. Phone localhost means the phone; 0.0.0.0 is a server bind address, not a client destination. This setting is a source constant, not EXPO_PUBLIC_API_URL or a mobile .env variable. Do not copy personal LAN addresses into shared documentation.

Connect both devices to the same private Wi-Fi, without guest/client isolation. Allow Python/Uvicorn and Node/Expo through Windows Firewall on that private network; do not disable the firewall. First open http://YOUR_PC_WIFI_IPV4:8000/ in the phone browser. Fix reachability before debugging the app.

From Mobile:

~~~powershell
npm.cmd start -- --lan
~~~

Scan the QR code with a matching Expo Go runtime (Android: Expo Go scanner; iOS: Camera/Expo Go). For SDK mismatch, use a compatible runtime or matching development build following Expo's guidance; do not blindly change SDK versions. Expo tunnel only tunnels Metro, not FastAPI.

Get Started opens login. Register an account, sign in, enter monthly income/category targets, and add debts before asking for saved-loan estimates. No demo credentials or prefilled financial records are required.

## Stop and restart

| Service | Stop | Restart |
| --- | --- | --- |
| FastAPI | Ctrl+C in its terminal | Repeat Uvicorn command from Backend |
| Expo / Metro | Ctrl+C in its terminal | npm.cmd start -- --lan from Mobile |
| Terminal Ollama server | Ctrl+C | ollama serve |
| Background Ollama app | Quit from tray menu | Open Ollama from Start |

Restart the backend after changing .env. Reload the phone after API_BASE_URL changes. If assets/code appear stale, restart Metro with npm.cmd start -- --clear --lan. Restarting does not require reinitializing SQLite, reinstalling dependencies or redownloading the model.

## Tests and validation

From Backend:

~~~powershell
.\venv\Scripts\python.exe -m pip check
.\venv\Scripts\python.exe -m pytest tests -q --disable-warnings --tb=short
~~~

Tests use in-memory or temporary SQLite, including migration tests, rather than the local financial database. A known category-validation test conflicts with custom-category support; see [testing](docs/testing.md). Do not report a wholly passing suite while that failure remains.

From Mobile:

~~~powershell
$mobileTestFiles = @(Get-ChildItem tests -Filter '*.cjs' | ForEach-Object { $_.FullName })
node --test @mobileTestFiles
node node_modules/typescript/bin/tsc --noEmit
~~~

Mocked AI tests verify contracts and safeguards, not real-model language quality. Opt-in Ollama checks use isolated accounts/databases:

~~~powershell
# From Backend, with Ollama running:
.\venv\Scripts\python.exe tests/live_multiple_proposals.py --live --no-think
.\venv\Scripts\python.exe tests/live_plan_rejection.py --live --no-think
~~~

See [testing and live checklists](docs/testing.md) for other harnesses. The project owner reports physical-device C1?C7 functionality/safety tests passed; this is not coverage of every iOS/Android version. No installed ESLint dependency or lint script exists. Do not install packages merely to claim lint passed.

## Troubleshooting

| Symptom | Check / remedy |
| --- | --- |
| Phone cannot connect | Uvicorn bind, phone-browser PC:8000 test, private firewall rules, same Wi-Fi, no guest isolation/VPN interference |
| Connection stopped working | DHCP may have changed PC IPv4. Recheck ipconfig, update API_BASE_URL and reload |
| Browser works, app fails | Check exact base URL, current JS bundle/runtime and matching backend revision. Web CORS is separate from native reachability |
| AI unavailable / timeout | Check Ollama, /api/tags, qwen3:4b and OLLAMA_URL. Try OLLAMA_THINK=false and restart API. Multi-call workflows can exceed the roughly 200-second chat timeout |
| Port in use | Stop the server in its owning terminal; avoid duplicate Ollama/Uvicorn processes |
| Authentication 503 | Configure JWT_SECRET_KEY and a valid token lifetime, then restart |
| Missing Python module | Use venv Python and install requirements.txt from Backend |
| Missing JS module | npm.cmd ci from Mobile, then restart Metro |
| Missing table/column | Check working directory, stop writers, back up, inspect schema and apply required migrations from docs/database.md |
| Review not found | Create a fresh review. Unregistered old cards, rejected/expired reviews and foreign account IDs cannot be accepted |
| Stale plan / HTTP 409 | Review again against current budget/debts/month; never bypass the fingerprint |
| Yes does not save | Intended: use Confirm or Accept on the specific card. Dismiss/Reject invalidates its capability |
| Stale logo | Reload current bundle; clear Metro cache if needed. Welcome uses bundled assets/pocketpilot-logo.png |

## Security, privacy and limitations

Use a trusted private LAN for development HTTP. Do not expose Uvicorn or Ollama publicly. Production needs HTTPS, deployment configuration, rate limiting, backups and operational hardening not supplied here.

Never publish .env, keys/tokens, SQLite files/journals/backups, real exports or account details. SQLite is not application-encrypted. Native tokens use SecureStore; web credentials are in memory. Scoped financial context goes to the configured Ollama host; remote hosting changes the privacy boundary. Public exchange-rate requests send no ledger or credentials.

No bank synchronization, real payments, password recovery/email verification, push notifications, PDF/OCR import or generic transaction-edit API is implemented. Confirmed income receipts update the selected month's saved income total; there is no separate income-transaction ledger or automatic recurring salary schedule. Some summaries synchronize opted-in recurring/debt entries on requests; there is no background bank scheduler.

Model interpretation is fallible and English-oriented validation remains conservative. Generated informational prose is not independently verified sentence by sentence. Savings are user-recorded values and repayment figures are estimates. Backend financial operations require network access even though the logo is bundled offline.

## Further documentation

Start with the [documentation index](docs/README.md), [architecture](docs/system-architecture.md), [database guide](docs/database.md), [API reference](docs/api-documentation.md), [AI workflows](docs/budget-goal-chat.md), [Financial Plans](docs/financial-planning.md) and [security assessment](docs/security-self-assessment.md). Historical handoff logs record earlier milestones, not current setup instructions.
