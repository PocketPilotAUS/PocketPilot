import sqlite3
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import migrate_add_users
from app.database import Base
from app.models import Transaction, User
from migrate_add_users import MigrationError, main, migrate

# Schema created by the original Transaction model, before authentication
LEGACY_SCHEMA = """
CREATE TABLE transactions (
    id INTEGER NOT NULL,
    amount FLOAT NOT NULL,
    category VARCHAR NOT NULL,
    description VARCHAR,
    date DATE NOT NULL,
    PRIMARY KEY (id)
);
CREATE INDEX ix_transactions_id ON transactions (id);
"""

# Realistic rows: gaps from deleted ids, missing descriptions, non-ASCII
# text, small and large amounts, and dates across several months
LEGACY_ROWS = [
    (1, 45.5, "Food", "Lunch", "2026-08-03"),
    (2, 25.0, "Transport", "Taxi", "2026-08-14"),
    (5, 0.01, "Shopping", None, "2026-09-01"),
    (7, 12345.67, "Rent", "September rent", "2026-09-30"),
    (8, 18.9, "Café", "Flat white ☕", "2026-10-08"),
    (11, 100.0, "Food", "", "2026-10-08"),
]

USERS_SCHEMA = """
CREATE TABLE users (
    id INTEGER NOT NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id)
);
"""


def make_legacy_db(path, rows=LEGACY_ROWS, extra_sql=""):
    connection = sqlite3.connect(path)
    connection.executescript(LEGACY_SCHEMA + extra_sql)
    connection.executemany(
        "INSERT INTO transactions (id, amount, category, description, date) "
        "VALUES (?, ?, ?, ?, ?)",
        rows
    )
    connection.commit()
    connection.close()
    return path


def query(path, sql):
    connection = sqlite3.connect(path)
    try:
        return connection.execute(sql).fetchall()
    finally:
        connection.close()


def legacy_rows(path):
    return query(
        path,
        "SELECT id, amount, category, description, date "
        "FROM transactions ORDER BY id"
    )


def columns(path, table):
    return [row[1] for row in query(path, f"PRAGMA table_info({table})")]


def tables(path):
    return {row[0] for row in query(path, "SELECT name FROM sqlite_master WHERE type='table'")}


def backups(directory):
    return sorted(directory.glob("*.backup-*.db"))


@pytest.fixture
def legacy_db(tmp_path):
    return make_legacy_db(tmp_path / "pocketpilot.db")


def test_migration_preserves_transactions(legacy_db):
    result = migrate(legacy_db)

    assert legacy_rows(legacy_db) == LEGACY_ROWS
    assert result.transaction_count == len(LEGACY_ROWS)
    assert "users" in tables(legacy_db)
    assert columns(legacy_db, "transactions")[-1] == "user_id"


def test_existing_transactions_left_unowned(legacy_db):
    result = migrate(legacy_db)

    assert query(legacy_db, "SELECT user_id FROM transactions") == [(None,)] * len(LEGACY_ROWS)
    assert query(legacy_db, "SELECT COUNT(*) FROM users") == [(0,)]
    assert result.unowned_count == len(LEGACY_ROWS)


def test_backup_created_before_changes(legacy_db, tmp_path):
    result = migrate(legacy_db)

    assert backups(tmp_path) == [result.backup]
    # The backup is the original, unmigrated database
    assert legacy_rows(result.backup) == LEGACY_ROWS
    assert "user_id" not in columns(result.backup, "transactions")
    assert "users" not in tables(result.backup)


def test_migration_is_repeatable(legacy_db, tmp_path):
    migrate(legacy_db)
    second = migrate(legacy_db)

    assert second.changes == []
    assert second.backup is None
    assert len(backups(tmp_path)) == 1
    assert columns(legacy_db, "transactions").count("user_id") == 1
    assert legacy_rows(legacy_db) == LEGACY_ROWS


def test_empty_legacy_database(tmp_path):
    path = make_legacy_db(tmp_path / "pocketpilot.db", rows=[])

    result = migrate(path)

    assert result.transaction_count == 0
    assert "user_id" in columns(path, "transactions")
    assert "users" in tables(path)


def test_dry_run_changes_nothing(legacy_db, tmp_path):
    original = legacy_db.read_bytes()

    result = migrate(legacy_db, dry_run=True)

    assert result.changes == [
        migrate_add_users.CREATE_USERS_TABLE,
        migrate_add_users.ADD_USER_ID_COLUMN,
        migrate_add_users.CREATE_USER_ID_INDEX
    ]
    assert legacy_db.read_bytes() == original
    assert backups(tmp_path) == []


def test_partial_users_table_already_exists(tmp_path):
    path = make_legacy_db(tmp_path / "pocketpilot.db", extra_sql=USERS_SCHEMA)

    result = migrate(path)

    assert result.changes == [
        migrate_add_users.ADD_USER_ID_COLUMN,
        migrate_add_users.CREATE_USER_ID_INDEX
    ]
    assert legacy_rows(path) == LEGACY_ROWS


def test_partial_user_id_column_without_index(tmp_path):
    path = make_legacy_db(
        tmp_path / "pocketpilot.db",
        extra_sql=USERS_SCHEMA + "ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users (id);"
    )

    result = migrate(path)

    assert result.changes == [migrate_add_users.CREATE_USER_ID_INDEX]
    assert columns(path, "transactions").count("user_id") == 1
    assert legacy_rows(path) == LEGACY_ROWS


def test_partial_user_id_column_without_users_table(tmp_path):
    path = make_legacy_db(
        tmp_path / "pocketpilot.db",
        extra_sql="ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users (id);"
    )

    result = migrate(path)

    assert result.changes == [
        migrate_add_users.CREATE_USERS_TABLE,
        migrate_add_users.CREATE_USER_ID_INDEX
    ]
    assert legacy_rows(path) == LEGACY_ROWS


def test_existing_owner_values_are_preserved(tmp_path):
    path = make_legacy_db(
        tmp_path / "pocketpilot.db",
        extra_sql=USERS_SCHEMA + """
            ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users (id);
            INSERT INTO users VALUES (1, 'a@example.com', 'A', 'hash', '2026-10-01');
        """
    )
    query_connection = sqlite3.connect(path)
    query_connection.execute("UPDATE transactions SET user_id = 1 WHERE id = 1")
    query_connection.commit()
    query_connection.close()

    migrate(path)

    assert query(path, "SELECT id, user_id FROM transactions WHERE user_id IS NOT NULL") == [(1, 1)]


def test_dangling_owner_rolls_back(tmp_path):
    # user_id points at a user that does not exist: needs a human decision
    path = make_legacy_db(
        tmp_path / "pocketpilot.db",
        extra_sql="ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users (id);"
    )
    connection = sqlite3.connect(path)
    connection.execute("UPDATE transactions SET user_id = 99 WHERE id = 2")
    connection.commit()
    connection.close()

    with pytest.raises(MigrationError, match="reference users that do not exist"):
        migrate(path)

    assert "users" not in tables(path)
    assert legacy_rows(path) == LEGACY_ROWS
    assert query(path, "SELECT user_id FROM transactions WHERE id = 2") == [(99,)]


def test_user_id_without_foreign_key_refused(tmp_path):
    # Added by hand without REFERENCES: SQLite could not enforce ownership
    path = make_legacy_db(
        tmp_path / "pocketpilot.db",
        extra_sql=USERS_SCHEMA + "ALTER TABLE transactions ADD COLUMN user_id INTEGER;"
    )
    original = path.read_bytes()

    with pytest.raises(MigrationError, match="no foreign key"):
        migrate(path)

    assert path.read_bytes() == original
    assert backups(tmp_path) == []


def test_failure_mid_migration_rolls_back(legacy_db, tmp_path, monkeypatch):
    def fail_verification(*args):
        raise MigrationError("Simulated failure after schema changes")

    monkeypatch.setattr(migrate_add_users, "verify_migration", fail_verification)

    with pytest.raises(MigrationError, match="Simulated failure"):
        migrate(legacy_db)

    # Schema changes were rolled back; the backup is still there
    assert "users" not in tables(legacy_db)
    assert "user_id" not in columns(legacy_db, "transactions")
    assert legacy_rows(legacy_db) == LEGACY_ROWS
    assert len(backups(tmp_path)) == 1


def test_incompatible_users_table_refused(tmp_path):
    # The first draft of the User model had no name or created_at
    path = make_legacy_db(
        tmp_path / "pocketpilot.db",
        extra_sql="CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR, hashed_password VARCHAR);"
    )
    original = path.read_bytes()

    with pytest.raises(MigrationError, match="missing columns"):
        migrate(path)

    assert path.read_bytes() == original
    assert backups(tmp_path) == []


def test_database_without_transactions_table_refused(tmp_path):
    path = tmp_path / "pocketpilot.db"
    sqlite3.connect(path).close()
    original = path.read_bytes()

    with pytest.raises(MigrationError, match="No transactions table"):
        migrate(path)

    assert path.read_bytes() == original
    assert backups(tmp_path) == []


def test_missing_database_not_created(tmp_path):
    path = tmp_path / "missing.db"

    with pytest.raises(MigrationError, match="Database not found"):
        migrate(path)

    assert not path.exists()


def test_backup_never_overwrites_existing_backup(legacy_db, monkeypatch):
    taken = migrate_add_users.backup_path_for(legacy_db)
    taken.write_bytes(b"older backup")
    monkeypatch.setattr(migrate_add_users, "backup_path_for", lambda path: taken)

    with pytest.raises(sqlite3.DatabaseError):
        migrate(legacy_db)

    assert taken.read_bytes() == b"older backup"


def test_backup_path_gets_unique_name(legacy_db):
    first = migrate_add_users.backup_path_for(legacy_db)
    first.write_bytes(b"")

    assert migrate_add_users.backup_path_for(legacy_db) != first


def test_migrated_schema_matches_models(legacy_db, tmp_path):
    migrate(legacy_db)

    fresh = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{fresh}")
    Base.metadata.create_all(bind=engine)
    engine.dispose()

    for table in ["users", "transactions"]:
        assert query(legacy_db, f"PRAGMA table_info({table})") == query(fresh, f"PRAGMA table_info({table})")
        # Skip the first field (seq), which only reflects creation order
        assert sorted(row[1:] for row in query(legacy_db, f"PRAGMA index_list({table})")) == sorted(
            row[1:] for row in query(fresh, f"PRAGMA index_list({table})")
        )

    assert [row[2:5] for row in query(legacy_db, "PRAGMA foreign_key_list(transactions)")] == [
        ("users", "user_id", "id")
    ]


def test_models_work_on_migrated_database(legacy_db):
    migrate(legacy_db)

    engine = create_engine(f"sqlite:///{legacy_db}")
    session = sessionmaker(bind=engine)()

    try:
        user = User(email="alice@example.com", name="Alice", hashed_password="not-a-real-hash")
        session.add(Transaction(amount=9.5, category="Food", date=date(2026, 10, 9), owner=user))
        session.commit()

        # Filtering by owner never includes unowned legacy rows
        owned = session.query(Transaction).filter(Transaction.user_id == user.id).all()
        assert [t.amount for t in owned] == [9.5]
        assert session.query(Transaction).filter(Transaction.user_id.is_(None)).count() == len(LEGACY_ROWS)

        # The foreign key added by ALTER TABLE is enforced
        session.add(Transaction(amount=1.0, category="Food", date=date(2026, 10, 9), user_id=999))
        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()
        engine.dispose()


def test_command_line(legacy_db, capsys):
    assert main(["--database", str(legacy_db), "--dry-run"]) == 0
    assert "Dry run" in capsys.readouterr().out

    assert main(["--database", str(legacy_db)]) == 0
    output = capsys.readouterr().out
    assert "Backup created" in output
    assert f"Unowned transactions (hidden from all users): {len(LEGACY_ROWS)}" in output

    assert main(["--database", str(legacy_db)]) == 0
    assert "Already up to date" in capsys.readouterr().out


def test_command_line_reports_failure(tmp_path, capsys):
    assert main(["--database", str(tmp_path / "missing.db")]) == 1
    assert "Migration failed" in capsys.readouterr().err
