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
| `chat_proposals` | User-owned pending income/expense proposals with confirmation state |

Goal association is a logical identifier rather than a foreign-key guarantee. Legacy transactions with no user are not exposed as another user's data. Monetary representations vary: some ledgers use integer cents, planning uses Decimal/JSON, and legacy transactions use float; do not assume a uniform money column type.

## Safe schema maintenance

For a fresh database, [init_db.py](../Backend/init_db.py) imports registered models and creates missing tables. `create_all` does not upgrade existing columns. Before modifying an existing database: stop writers, back up the database (and any active journal/WAL consistently), inspect its tables/columns, compare the relevant models and read the selected migration script. Test changes on a copy first. Never reset an existing financial database to resolve a missing column.

| Script in Backend | Purpose |
| --- | --- |
| `migrate_add_users.py` | Legacy account ownership migration; inspect its dry-run/assignment options |
| `migrate_account_settings.py` | Account settings schema |
| `migrate_refresh_sessions.py` | Refresh session/token schema |
| `migrate_debts.py` | Debt schema |
| `migrate_debt_payments.py` | Payment ledger |
| `migrate_automatic_debts.py` | Automatic payment fields; requires debt/payment schema |
| `migrate_savings.py` | Monthly savings schema |
| `migrate_manual_savings.py` | Manual contributions |
| `migrate_savings_goals.py` | Optional contribution goal identifier and index; requires manual savings |

These are standalone scripts, not an automatically applied migration chain. Read the actual CLI and safeguards; not every script offers dry-run. Check source filenames before invoking anything. New AI goal drafts do not justify deleting existing records. A missing schema and a stale budget fingerprint are separate failures; stale-budget protection must remain enabled.
