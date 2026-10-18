# Local development and configuration

Follow the [root README](../README.md) for PowerShell installation and startup commands. Run the backend from `Backend` so the fixed relative SQLite URL resolves consistently. Install pinned Python requirements and use `npm.cmd ci` with the committed mobile lockfile.

| Setting | Behavior |
| --- | --- |
| `JWT_SECRET_KEY` | Required private HS256 signing secret, at least 32 characters |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Default 30; validated range 1 through 1440 |
| `OLLAMA_URL` | Required for AI: Ollama base URL, for example `http://localhost:11434`; native `/api/chat` |
| `OLLAMA_THINK` | Main client defaults to thinking; false/0/no/off disable it |

The application loads dotenv configuration. Do not commit `.env`, tokens or real financial exports. `.env.example` is a template. There is no implemented `DATABASE_URL` or `OLLAMA_MODEL` setting: inspect [database setup](../Backend/app/database.py) and [AI clients](../Backend/app/ai/) before changing those values in source.

The main model is `qwen3:4b`. Facts/adjustment requests and statement classification disable thinking independently. Main AI calls allow up to 180 seconds per request; mobile chat allows about 200 seconds overall, so multi-call workflows can still exceed the client limit. Statement classification has a shorter timeout. Ollama must have the model available before AI features work.

The mobile API address is currently a source constant in [App.tsx](../Mobile/App.tsx), not an Expo environment variable. Use `http://YOUR_LOCAL_IP:8000` for a reachable development computer, and keep that local change out of commits. Binding Uvicorn to `0.0.0.0` permits LAN access; configure the firewall deliberately. Expo's transport does not proxy the backend. CORS configuration is development-oriented, not a production authorization boundary.

Light/dark and language/currency preferences are stored on-device. Native authentication uses SecureStore; web authentication is in-memory. Selected currency changes display and request interpretation, not canonical AED storage. See [currency display](currency-display.md).

Do not run migration scripts indiscriminately on an existing database. See [database maintenance](database.md). No production deployment automation, TLS termination or operational backup service is supplied by the application.


## Current setup and tooling notes

Python 3.11.9, Node 24.20.0 and npm 11.19.0 were checked locally; these are observed versions, not a guarantee that every newer version works. SDK 57 specifies Node 22.13.x minimum; see the official reference linked in the README. Dependencies pin Expo 57 / React Native 0.86.3 / React 19.2.3. No mobile environment-variable loader or Expo Router is configured.

Fresh setup runs init_db.py and then migrate_plan_reviews.py. Existing schemas need the [migration guide](database.md), including explicit backup before the review script. Migration files remain at Backend/migrate_*.py; no database or folders were reorganized.

Use venv Python directly without shell activation; npm.cmd avoids npm.ps1 restrictions. The README provides separate-terminal commands for Ollama, Uvicorn and Metro, stop/restart and phone reachability. Expo QR/tunnel transport does not proxy FastAPI.

The OpenAI SDK is pinned but unused by the current Ollama clients. No cloud key, external database server or global Expo CLI is needed. Use npm ci with the committed lockfile; do not upgrade the SDK as a network troubleshooting step. Lint remains unconfigured; see [testing](testing.md).

App config is portrait and retains existing launcher icons. The welcome screen alone uses the bundled transparent pocketpilot-logo.png, up to 176 square, scaled down for smaller windows. Its 70% centered button has a 48-point minimum height; the title/subtitle remain and the gray description is removed.
