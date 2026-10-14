"""Add debt storage, backing up existing SQLite data first. Stop the server first."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. For a new database, run init_db.py first.")
    with sqlite3.connect(path) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='debts'").fetchone():
            print("Debt storage already up to date.")
            return
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            raise ValueError("Users table not found.")
        backup_path = path.with_name(f"{path.stem}.backup-debts-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup_path) as backup:
            db.backup(backup)
        db.execute("CREATE TABLE debts (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), name VARCHAR(80) NOT NULL, balance NUMERIC(14,2) NOT NULL, annual_rate NUMERIC(7,4) NOT NULL, remaining_months INTEGER NOT NULL, original_principal NUMERIC(14,2))")
        db.execute("CREATE INDEX ix_debts_user_id ON debts(user_id)")
        print(f"Debt storage added. Backup: {backup_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
