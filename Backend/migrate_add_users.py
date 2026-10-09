"""
Safely add user accounts to an existing PocketPilot SQLite database.

Adds the users table, the transactions.user_id column and its index, but
only the parts that are missing, so it is safe to run more than once.
Existing transactions are never changed or deleted, and are left unowned
(user_id = NULL) until ownership is explicitly assigned.

Stop the API server first, then run from the Backend folder:

    python migrate_add_users.py --dry-run     # show what would change
    python migrate_add_users.py               # back up, then migrate
    python migrate_add_users.py --database path/to/pocketpilot.db
"""

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects import sqlite as sqlite_dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models import Transaction, User

DEFAULT_DATABASE = "pocketpilot.db"

LEGACY_TRANSACTION_COLUMNS = ["id", "amount", "category", "description", "date"]
USER_ID_INDEX = "ix_transactions_user_id"

CREATE_USERS_TABLE = "create users table"
ADD_USER_ID_COLUMN = "add transactions.user_id column"
CREATE_USER_ID_INDEX = f"create index {USER_ID_INDEX}"

DIALECT = sqlite_dialect.dialect()


class MigrationError(Exception):
    pass


@dataclass
class MigrationResult:
    database: Path
    changes: list[str]
    transaction_count: int
    unowned_count: int
    backup: Path | None = None
    dry_run: bool = False


def connect(path):
    # isolation_level=None turns off Python's implicit transaction handling,
    # which would otherwise commit schema changes (DDL) immediately. This
    # script opens and commits its transaction explicitly instead.
    connection = sqlite3.connect(path, isolation_level=None, timeout=5)
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def table_names(connection):
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def column_names(connection, table):
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def index_names(connection, table):
    return {row[1] for row in connection.execute(f"PRAGMA index_list({table})")}


def has_user_id_foreign_key(connection):
    # Row format: (id, seq, table, from, to, on_update, on_delete, match)
    return any(
        row[2] == "users" and row[3] == "user_id" and row[4] in (None, "id")
        for row in connection.execute("PRAGMA foreign_key_list(transactions)")
    )


def check_integrity(connection):
    result = connection.execute("PRAGMA integrity_check").fetchone()[0]

    if result != "ok":
        raise MigrationError(f"Database integrity check failed: {result}")


def plan_changes(connection):
    tables = table_names(connection)

    if "transactions" not in tables:
        raise MigrationError(
            "No transactions table found, so this is not an existing "
            "PocketPilot database. Nothing was changed. Use init_db.py to "
            "create a new database."
        )

    transaction_columns = column_names(connection, "transactions")
    missing = set(LEGACY_TRANSACTION_COLUMNS) - set(transaction_columns)

    if missing:
        raise MigrationError(
            f"The transactions table is missing columns {sorted(missing)}. "
            "Nothing was changed."
        )

    changes = []

    if "users" in tables:
        expected = set(User.__table__.columns.keys())
        missing = expected - set(column_names(connection, "users"))

        if missing:
            raise MigrationError(
                f"An existing users table is missing columns {sorted(missing)}. "
                "It must be reviewed manually. Nothing was changed."
            )
    else:
        changes.append(CREATE_USERS_TABLE)

    if "user_id" not in transaction_columns:
        changes.append(ADD_USER_ID_COLUMN)
    elif not has_user_id_foreign_key(connection):
        # SQLite cannot add a foreign key to an existing column without
        # rebuilding the table, which is too risky to do automatically.
        raise MigrationError(
            "transactions.user_id exists but has no foreign key to users.id. "
            "It must be reviewed manually. Nothing was changed."
        )

    if USER_ID_INDEX not in index_names(connection, "transactions"):
        changes.append(CREATE_USER_ID_INDEX)

    return changes


def count_transactions(connection):
    return connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


def count_unowned(connection):
    if "user_id" not in column_names(connection, "transactions"):
        return count_transactions(connection)

    return connection.execute(
        "SELECT COUNT(*) FROM transactions WHERE user_id IS NULL"
    ).fetchone()[0]


def snapshot_transactions(connection):
    # Every existing value, including user_id if the column already exists
    columns = [
        column for column in LEGACY_TRANSACTION_COLUMNS + ["user_id"]
        if column in column_names(connection, "transactions")
    ]

    rows = connection.execute(
        f"SELECT {', '.join(columns)} FROM transactions ORDER BY id"
    ).fetchall()

    return columns, rows


def backup_path_for(path):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    candidate = path.with_name(f"{path.stem}.backup-{timestamp}{path.suffix}")
    number = 2

    # Never overwrite an existing backup
    while candidate.exists():
        candidate = path.with_name(
            f"{path.stem}.backup-{timestamp}-{number}{path.suffix}"
        )
        number += 1

    return candidate


def create_backup(connection, path):
    backup = backup_path_for(path)

    # SQLite's online backup API copies a consistent snapshot of the database
    target = sqlite3.connect(backup)
    try:
        connection.backup(target)
    finally:
        target.close()

    verify_backup(backup, count_transactions(connection))

    return backup


def verify_backup(backup, expected_count):
    target = sqlite3.connect(f"{backup.as_uri()}?mode=ro", uri=True)
    try:
        check_integrity(target)

        if count_transactions(target) != expected_count:
            raise MigrationError(
                f"Backup {backup} does not contain every transaction. "
                "Nothing was changed."
            )
    finally:
        target.close()


def apply_changes(connection):
    # BEGIN IMMEDIATE takes the write lock now, so nothing else can modify
    # the database between checking the schema and changing it.
    connection.execute("BEGIN IMMEDIATE")

    try:
        changes = plan_changes(connection)
        before = snapshot_transactions(connection)

        if CREATE_USERS_TABLE in changes:
            create_table(connection, User.__table__)

        if ADD_USER_ID_COLUMN in changes:
            # NULL is the default, so every existing transaction stays unowned
            connection.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN user_id INTEGER REFERENCES users (id)"
            )

        if CREATE_USER_ID_INDEX in changes:
            index = next(
                index for index in Transaction.__table__.indexes
                if index.name == USER_ID_INDEX
            )
            connection.execute(str(CreateIndex(index).compile(dialect=DIALECT)))

        verify_migration(connection, before, changes)
        connection.execute("COMMIT")

    except BaseException:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise

    return changes


def create_table(connection, table):
    connection.execute(str(CreateTable(table).compile(dialect=DIALECT)))

    for index in table.indexes:
        connection.execute(str(CreateIndex(index).compile(dialect=DIALECT)))


def verify_migration(connection, before, changes):
    columns, rows_before = before

    # Compare the same columns as before, so a newly added user_id is ignored
    rows_after = connection.execute(
        f"SELECT {', '.join(columns)} FROM transactions ORDER BY id"
    ).fetchall()

    if rows_after != rows_before:
        raise MigrationError(
            "Transaction data changed during migration. Rolled back."
        )

    if ADD_USER_ID_COLUMN in changes:
        owned = connection.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id IS NOT NULL"
        ).fetchone()[0]

        if owned:
            raise MigrationError(
                "Existing transactions were given an owner. Rolled back."
            )

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()

    if violations:
        raise MigrationError(
            f"{len(violations)} transaction(s) reference users that do not "
            "exist. This needs a manual decision. Rolled back."
        )

    result = connection.execute("PRAGMA quick_check").fetchone()[0]

    if result != "ok":
        raise MigrationError(f"Database check failed: {result}. Rolled back.")


def migrate(database, dry_run=False):
    path = Path(database).resolve()

    # Refuse rather than let sqlite3 silently create a new, empty file
    if not path.is_file():
        raise MigrationError(f"Database not found: {path}. Nothing was created.")

    connection = connect(path)

    try:
        check_integrity(connection)
        changes = plan_changes(connection)
        transaction_count = count_transactions(connection)

        if dry_run or not changes:
            return MigrationResult(
                database=path,
                changes=changes,
                transaction_count=transaction_count,
                unowned_count=count_unowned(connection),
                dry_run=dry_run
            )

        backup = create_backup(connection, path)
        changes = apply_changes(connection)
    finally:
        connection.close()

    # Re-open and confirm the committed result
    connection = connect(path)

    try:
        if plan_changes(connection):
            raise MigrationError("Migration did not complete. Restore from backup.")

        if count_transactions(connection) != transaction_count:
            raise MigrationError("Transaction count changed. Restore from backup.")

        return MigrationResult(
            database=path,
            changes=changes,
            transaction_count=transaction_count,
            unowned_count=count_unowned(connection),
            backup=backup
        )
    finally:
        connection.close()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Add user accounts to an existing PocketPilot database."
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help=f"Path to the SQLite database (default: {DEFAULT_DATABASE})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying anything"
    )
    args = parser.parse_args(argv)

    try:
        result = migrate(args.database, dry_run=args.dry_run)
    except (MigrationError, sqlite3.Error) as error:
        print(f"Migration failed: {error}", file=sys.stderr)
        return 1

    print(f"Database: {result.database}")

    if not result.changes:
        print("Already up to date. Nothing was changed.")
    elif result.dry_run:
        print("Dry run. These changes would be made:")
        for change in result.changes:
            print(f"  - {change}")
    else:
        print(f"Backup created: {result.backup}")
        print("Changes made:")
        for change in result.changes:
            print(f"  - {change}")

    print(f"Transactions: {result.transaction_count}")
    print(f"Unowned transactions (hidden from all users): {result.unowned_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
