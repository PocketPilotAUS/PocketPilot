"""Add manual savings without modifying monthly confirmations or other records."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. For a new database, run init_db.py first.")
    with sqlite3.connect(path) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='manual_savings'").fetchone():
            print("Manual savings already up to date.")
            return
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            raise ValueError("Users table not found.")
        backup_path = path.with_name(f"{path.stem}.backup-manual-savings-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup_path) as backup:
            db.backup(backup)
        db.execute("CREATE TABLE manual_savings (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), label VARCHAR(80) NOT NULL, amount_cents INTEGER NOT NULL, request_key VARCHAR(36) NOT NULL, UNIQUE(user_id,request_key))")
        db.execute("CREATE INDEX ix_manual_savings_user_id ON manual_savings(user_id)")
        print(f"Manual savings added. Backup: {backup_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
