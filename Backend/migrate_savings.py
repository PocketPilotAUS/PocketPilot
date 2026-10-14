"""Add monthly savings confirmations without rewriting existing financial data."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. For a new database, run init_db.py first.")
    with sqlite3.connect(path) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='monthly_savings'").fetchone():
            print("Savings storage already up to date.")
            return
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            raise ValueError("Users table not found.")
        backup_path = path.with_name(f"{path.stem}.backup-savings-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup_path) as backup:
            db.backup(backup)
        db.execute("CREATE TABLE monthly_savings (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), year INTEGER NOT NULL, month INTEGER NOT NULL, income_cents INTEGER NOT NULL, spent_cents INTEGER NOT NULL, extra_debt_cents INTEGER NOT NULL, saved_cents INTEGER NOT NULL, UNIQUE(user_id,year,month))")
        db.execute("CREATE INDEX ix_monthly_savings_user_id ON monthly_savings(user_id)")
        print(f"Savings storage added. Backup: {backup_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
