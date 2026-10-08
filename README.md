# PocketPilot

PocketPilot is a prototype mobile personal-finance assistant built with **Expo / React Native (TypeScript)** and a **FastAPI / SQLite** backend. It records manually entered expenses, summarizes spending by category, compares months, and supports recommendation endpoints, including optional local AI explanations through Ollama.

> **Prototype notice:** Mobile registration/login uses fictional accounts stored locally for demonstration. The backend has no user authentication or per-user data isolation. Do **not** enter real passwords, banking credentials, or sensitive financial records.

## Repository

https://github.com/PocketPilotAUS/PocketPilot

```text
PocketPilot/
  Backend/                 FastAPI API, SQLite, algorithms, tests
    app/main.py
    app/database.py
    app/models/transaction.py
  Mobile/                  Expo React Native TypeScript app
    App.tsx
    src/screens/
    src/styles/            External, theme-aware stylesheets
    src/components/
    src/services/
    src/theme/
  docs/                    Technical documentation and handoff guide
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

Start backend in **terminal 1**:

```powershell
cd Backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0
```

If PowerShell blocks activation, use `venv\Scripts\python.exe` for commands instead. Check http://127.0.0.1:8000/docs on the PC.

Start mobile in **terminal 2**:

```powershell
cd Mobile
npm install
npx expo start
```

Open Expo Go on the iPhone and scan the QR code. **Before mobile testing**, find the PC's LAN IPv4 address with `ipconfig` and update the `API_BASE_URL` in `Mobile/App.tsx` from the previous developer's local address to `http://YOUR_PC_IP:8000`. Test `http://YOUR_PC_IP:8000/spending/summary` in iPhone Safari. Keep the backend running.

The development HTTP API is for a trusted local network only; production requires HTTPS and authentication.

## What works in the current prototype

- Animated welcome screen, metallic/glass UI, dark/light theme toggle
- Demo registration, login, session restore, and logout using AsyncStorage
- Manual expense entry, including custom category, description and date
- Expense history and deletion with confirmation
- Dashboard total expenses and category breakdown from SQLite-backed API
- Backend monthly spending comparison and deterministic recommendations
- Optional backend AI recommendation explanations via Ollama/Qwen3 (API tested; **not displayed in mobile UI yet**)

## API quick checks

- `GET /` — health message
- `POST /transactions/` — create expense
- `GET /transactions/` — list expenses
- `DELETE /transactions/{id}` — remove expense
- `GET /spending/summary` — total and category breakdown
- `GET /spending/compare?year=2026&month=10` — compare months
- `GET /recommendations/?year=2026&month=10` — rules-based advice
- `GET /recommendations/ai?year=2026&month=10` — optional AI explanation

Use FastAPI Swagger at http://127.0.0.1:8000/docs to test endpoint schemas and responses. AI responses require the configured Ollama server, and may be empty when there are no qualifying month-over-month changes.

## Tests

From `Backend` with the environment activated:

```powershell
python -m pytest
```

From `Mobile`:

```powershell
npx tsc --noEmit
```

These are commands to run locally; test results are **not** asserted by this document. Also manually verify register → dashboard → add transaction → history → delete → logout → login → app restart.

## Known limitations / next work

1. Replace demo authentication with hashed-password backend auth and token/session handling; link all data to user IDs.
2. Preserve existing SQLite data carefully while migrating transaction schema.
3. Add income tracking, editing/search/filtering transactions, budgets and savings goals.
4. Implement recurring bills, subscriptions, debt payoff planner.
5. Add charts, AI recommendation cards and a data-grounded AI chat.
6. Build Profile/Settings, notification preferences, reminder system and persistent theme choice.
7. Add security tests, error handling, environment-based configuration and deployment instructions.

See `docs/DEVELOPER_HANDOFF.md` for an ordered development plan and troubleshooting.

## Git hygiene

Never commit `Backend/venv/`, `Mobile/node_modules/`, `*.db`, `.env`, secrets, local credentials or Expo cache. Check `git status` and `git diff --cached` before committing. Documentation and source code can be committed after review.
