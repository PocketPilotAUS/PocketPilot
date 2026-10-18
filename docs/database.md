# SQLite data model and maintenance

[database.py](../Backend/app/database.py) uses `sqlite:///./pocketpilot.db`; launch from `Backend`. SQLAlchemy enables SQLite foreign keys. [Models](../Backend/app/models/) define these tables:

| Tables | Ownership and relationships |
| --- | --- |
| `users`, `account_settings` | Account identity and user settings |
| `refresh_sessions`, `refresh_tokens` | Session family and hashed rotating tokens linked to a user |
| `transactions`, `monthly_income`, `budget_plans` | User expense ledger and year/month income and budget records |
| `recurring_expenses`, `recurring_occurrences` | User schedules and unique occurrence claims |
| `debts`, `debt_payments` | User obligations and payment history; deletion preserves historical payment information |
| `monthly_savings`, `manual_savings` | User month snapshots and contributions; optional manual `goal_id` associates a saved plan |
| `planning_profiles`, `financial_plans` | User planning inputs and saved JSON plan snapshots |
| `chat_proposals` | User-owned transaction proposals, expiry and cancellation tombstones |
| `financial_plan_reviews` | Durable owner-bound Financial Plan capabilities: pending, accepting, rejected, saved, expired |

Goal association is a logical identifier rather than a foreign-key guarantee. Legacy transactions with no user are not exposed as another user's data. Monetary representations vary: some ledgers use integer cents, planning uses Decimal/JSON, and legacy transactions use float; do not assume a uniform money column type.

## Safe schema maintenance

For a fresh database, [init_db.py](../Backend/init_db.py) imports registered models and creates missing tables. Run [migrate_plan_reviews.py](../Backend/migrate_plan_reviews.py) immediately afterward: PlanReview is not imported by app.models in the standalone initializer. The API imports it later, but does not create tables automatically. `create_all` does not upgrade existing columns. Before modifying an existing database: stop writers, back up the database (and any active journal/WAL consistently), inspect its tables/columns, compare the relevant models and read the selected migration script. Test changes on a copy first. Never reset an existing financial database to resolve a missing column.

| Script in Backend | Purpose |
| --- | --- |
| `migrate_add_users.py` | Legacy ownership schema; --database and --dry-run; unowned transactions stay hidden |
| `migrate_account_settings.py` | Account settings schema |
| `migrate_refresh_sessions.py` | Refresh session/token schema |
| `migrate_debts.py` | Debt schema |
| `migrate_debt_payments.py` | Payment ledger |
| `migrate_automatic_debts.py` | Automatic payment fields; requires debt/payment schema |
| `migrate_savings.py` | Monthly savings schema |
| `migrate_manual_savings.py` | Manual contributions |
| `migrate_savings_goals.py` | Optional contribution goal identifier and index; requires manual savings |

| `migrate_plan_reviews.py` | Financial Plan review registry; current-directory database, no --database switch or built-in backup |

These are standalone scripts, not an automatically applied migration chain. Read the actual CLI and safeguards; not every script offers dry-run. Check source filenames before invoking anything. New AI goal drafts do not justify deleting existing records. A missing schema and a stale budget fingerprint are separate failures; stale-budget protection must remain enabled.


## Commands and migration order

Run from Backend, using the scripts in place. For a fresh database, use the guarded two-command setup in the [README](../README.md). For an existing database, inspect first:

~~~powershell
.\venv\Scripts\python.exe -c "import sqlite3; c=sqlite3.connect('file:pocketpilot.db?mode=ro',uri=True); print(c.execute('SELECT name FROM sqlite_master WHERE type=? ORDER BY name',('table',)).fetchall()); c.close()"
~~~

Stop API writers before taking a consistent backup. From Backend:

~~~powershell
.\venv\Scripts\python.exe -c "import sqlite3,datetime; p='pocketpilot.backup-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.db'; s=sqlite3.connect('file:pocketpilot.db?mode=ro',uri=True); d=sqlite3.connect(p); s.backup(d); d.close(); s.close(); print(p)"
~~~

Keep backups private and outside version control. Test upgrades on a copy. Scripts with --database can target that copy; migrate_plan_reviews.py uses the engine's current-directory path, so use an isolated working directory when testing it.

Apply only required migrations, in dependency order:

1. Legacy pre-authentication database: migrate_add_users.py --database pocketpilot.db --dry-run; inspect, then repeat without --dry-run. No owner-assignment CLI exists. Unowned legacy rows remain hidden.
2. Account/session tables: migrate_account_settings.py, then migrate_refresh_sessions.py as needed.
3. Debt/payment tables: migrate_debts.py, migrate_debt_payments.py, then migrate_automatic_debts.py. The last adds automatic-payment/fixed-baseline columns to old tables.
4. Savings: migrate_savings.py, migrate_manual_savings.py, then migrate_savings_goals.py. The last adds manual_savings.goal_id and its index.
5. Financial Plan reviews: migrate_plan_reviews.py after users exist. Back up explicitly: this script does not make its own backup.

Invoke selected scripts with the venv interpreter, for example:

~~~powershell
.\venv\Scripts\python.exe migrate_automatic_debts.py --database pocketpilot.db
.\venv\Scripts\python.exe migrate_plan_reviews.py
~~~

All listed scripts except migrate_plan_reviews.py accept --database; migrate_add_users.py also supports --dry-run. Do not pass unsupported switches. Table-creation migrations do not retrofit missing columns. There is no Alembic runner or complete versioned upgrade chain. After required column upgrades, init_db.py can create still-missing registered tables; it is not a substitute for schema inspection. Restart the API and request fresh reviews; old unregistered cards are invalid.

Review/proposal rows are safety metadata, not financial ledger entries. New Chat clears references without deleting that metadata. Do not delete rejected/dismissed/consumed rows to make an old capability reusable.
