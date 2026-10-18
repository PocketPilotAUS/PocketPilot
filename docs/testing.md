# Testing and validation

Use the [README](../README.md) for dependencies and runtime setup. Each command below names its working directory. Mocked tests and live-model checks provide different evidence.

## Automated backend regressions

From Backend:

~~~powershell
.\venv\Scripts\python.exe -m pip check
.\venv\Scripts\python.exe -m pytest tests -q --disable-warnings --tb=short
~~~

Fixtures use in-memory SQLite; migration/concurrency tests use temporary files. test_end_to_end.py migrates its tmp_path database, not Backend/pocketpilot.db. No migration-test exclusion is required for the normal full suite. Do not run standalone migrations against a financial database as a test.

Mocked AI tests check grounding, read-only gates, dates, retained state, ownership, expiry, cancellation, stale snapshots, idempotency and concurrency. They do not prove Ollama recognizes every paraphrase.

Known pre-existing failure: tests/test_planning.py::test_invalid_profiles[patch4] expects an unknown category rejected with 422, but implemented custom-category support accepts it with 200. Report separately; do not change behavior just to make documentation/test reporting look clean.

## Mobile tests and types

From Mobile:

~~~powershell
$mobileTestFiles = @(Get-ChildItem tests -Filter '*.cjs' | ForEach-Object { $_.FullName })
node --test @mobileTestFiles
node node_modules/typescript/bin/tsc --noEmit
~~~

Modules cover auth refresh races, proposal/plan history and controls, debt context/topic switching, savings headroom and responsive welcome logo/button layout. They transpile TypeScript and mock React Native dependencies; this is not a native UI/E2E runner. TypeScript checks types, not phone rendering.

No installed ESLint dependency or lint script exists. Do not auto-install packages through Expo lint just to claim lint passed.

## Opt-in live Ollama

Start Ollama, pull qwen3:4b and configure OLLAMA_URL. Scripts require --live explicitly. --no-think sets OLLAMA_THINK=false for the process; report this mode with results. API harnesses use isolated synthetic accounts/databases, including any explicit confirmation writes.

From Backend, run selected harnesses:

~~~powershell
.\venv\Scripts\python.exe tests/live_expense_cases.py --live --no-think
.\venv\Scripts\python.exe tests/live_income_cases.py --live --no-think
.\venv\Scripts\python.exe tests/live_savings_cases.py --live --no-think
.\venv\Scripts\python.exe tests/live_debt_cases.py --live --no-think
.\venv\Scripts\python.exe tests/live_topic_switches.py --live --no-think
.\venv\Scripts\python.exe tests/live_record_cancellation.py --live --no-think
.\venv\Scripts\python.exe tests/live_chat_acknowledgments.py --live --no-think
.\venv\Scripts\python.exe tests/live_proposal_references.py --live --no-think
.\venv\Scripts\python.exe tests/live_savings_headroom.py --live --no-think
.\venv\Scripts\python.exe tests/live_plan_rejection.py --live --no-think
.\venv\Scripts\python.exe tests/live_multiple_proposals.py --live --no-think
~~~

live_chat_nlu.py is an additional semantic probe, not proof of full API persistence behavior. Run heavy harnesses sequentially on limited hardware. Inspect extracted facts, replies and persisted state, not just HTTP success.

## Device and live checklist

The project owner reports planned physical-device AI functionality and C1?C7 safety tests passed. Separate that evidence from automated results and untested OS/runtime versions.

1. Expenses: Lunch cost me 50 today, transport 75 today, groceries 120 followed by Today. Verify retained facts and a pending proposal only.
2. Income: earned 2k yesterday, income lookup and hypothetical recording 2,000. Verify add versus replacement, date/month, no expense-category question or invented recurrence, and no automatic save.
3. Savings: laptop 5k, 800 a month, then 600 instead. Separately test monthly affordability and protected Rent; no invented goal/Accept card for an informational question.
4. Debt: saved Car Loan, faster payoff, two years, then three. Verify annual APR, 24/36 months, owned saved facts, estimates and no payment recording.
5. Topic switch: debt -> budget -> income lookup -> 800. Expect clarification, no revived action or proposal.
6. C1: Yes with pending expense/income points to Confirm/Dismiss; no save. A legitimate Yes to an explanation question still works.
7. Cancellation/C2: dismiss/cancel, then reference after a topic switch. Check persisted terminal status, no new intake and old confirmation blocked.
8. Rejected Financial Plan: reject vacation goal, ask to accept it conversationally, then attempt the old capability. Verify plan-specific wording, permanent rejection and no saved goal/deposit.
9. Savings math: synthetic 10,000 income, 6,420 non-debt targets, 566.14 separate debt and 600 savings give 3,013.86 before and 2,413.86 after. Verify no double-counted loan and no fake deposit on acceptance.
10. C7: 40 groceries then 25 transport, both today. Verify independent IDs/cards; reference/cancel 40 without changing 25. Only its specific Confirm button saves a record.
11. Backend safety: account isolation, New Chat, expiry, successful retries and concurrent acceptance use isolated tests rather than personal financial accounts.
12. Welcome: transparent logo, centered title/subtitle, no gray description, 70% centered button and correct Get Started navigation. Check small screens/larger text. App configuration is portrait; dimension tests also cover constrained/landscape-sized windows.

## Documentation validation

Check relative Markdown links/fragments, file paths and PowerShell syntax. Compare the API table against app.openapi(); run git diff --check. Review changes for secrets, environment contents, database data, real exports, personal IPs and credentials. Historical handoff counts are not current suite results.

Smoke-test initialization using the real init_db.py and migrate_plan_reviews.py in an isolated temporary working directory. Do not recreate/migrate a developer database to validate instructions. Existing-environment checks are not a clean-Windows installation or universal native-device test.


## Documentation audit validation ? 18 October 2026

| Check | Observed result |
| --- | --- |
| Full backend suite | 1,115 passed; 1 known custom-category expectation failure described above |
| Mobile Node suite | 40 passed |
| TypeScript | Passed |
| Python dependency integrity / exact pins | pip check passed; installed versions match requirements.txt |
| Mobile direct dependencies | Manifest, lockfile and installed versions agree |
| Fresh SQLite setup | init_db.py + migrate_plan_reviews.py created all 17 tables in an isolated temporary database |
| Uvicorn startup / shutdown | Passed with LAN bind and root health request, isolated working directory and temporary port |
| Ollama readiness | Native /api/tags reachable and qwen3:4b installed |
| Documentation consistency | 25 Markdown files checked, 120 relative links valid, all 58 API operations match OpenAPI, 20 PowerShell blocks parse, 15 distinct Python script paths verified |
| Whitespace and secret-pattern review | Passed; signing-key examples are placeholders, no private environment/database contents copied |
| ESLint | Unavailable: not installed/configured |

This was not a clean-Windows reinstallation or new native-device run. No live model inference suite was rerun for documentation-only changes; earlier live/owner-reported device evidence remains separate. Scripts/migrations were exercised only with isolated temporary data, not the developer's financial database.
