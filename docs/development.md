# Local development and configuration

Follow the [root README](../README.md) for PowerShell installation and startup commands. Run the backend from `Backend` so the fixed relative SQLite URL resolves consistently. Install pinned Python requirements and use `npm ci` with the committed mobile lockfile.

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
