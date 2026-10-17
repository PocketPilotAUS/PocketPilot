# Testing and validation

Install dependencies from the [README](../README.md). Backend fixtures use isolated SQLite databases and mocked Ollama responses, never the real financial database.

From Backend:

```powershell
.\venv\Scripts\python.exe -B -m pytest -q --tb=short -p no:cacheprovider tests --ignore=tests/test_end_to_end.py -k "not migration"
```

The excluded end-to-end module runs migrations in a fixture. Migration-named tests and test_migration.py are excluded even though they normally use temporary files. Run migration coverage only when authorized. The AI proposal fix requires no migration.

AI regression modules cover read-only suppression, account isolation, pending wording, relative dates/income periods, recording after a pending goal, null actions, confirmation/rejection and debt-aware stale-plan acceptance. Expense evidence cases include date/year confusion, wrong amounts/categories, aliases, multiple numbers and ambiguity.

From Mobile:

```powershell
node --test tests/auth-refresh.cjs tests/chat-recording.cjs
node node_modules/typescript/bin/tsc --noEmit
```

Node tests exercise transformed logic/rendering with mocks, not a real-device end-to-end harness. Coverage includes refresh races, proposal/plan exclusivity, calendar dates and plan saving-state isolation. TypeScript checks types. No lint script or installed ESLint dependency is configured; do not auto-install packages during verification.

Known pre-existing failure: `tests/test_planning.py::test_invalid_profiles[patch4]` expects an unknown category rejected, but current custom-category support accepts it. Report separately from regressions rather than changing unrelated behavior.

Before merge: run `git diff --check`, validate Markdown paths and routes against app.openapi(), and inspect all proposed staging content for secrets/environment artifacts. Live Expo Go/Ollama QA remains necessary for model behavior, network and layout beyond mocked tests.
