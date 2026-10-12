"""Add account settings without modifying existing users or financial records."""
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. For a new database, run init_db.py first.")
    with sqlite3.connect(path) as db:
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='account_settings'").fetchone():
            print("Account settings already up to date.")
            return
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'").fetchone():
            raise ValueError("Users table not found. Initialize the database first.")
        backup_path = path.with_name(f"{path.stem}.backup-settings-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup_path) as backup:
            db.backup(backup)
        db.execute("CREATE TABLE account_settings (user_id INTEGER NOT NULL PRIMARY KEY REFERENCES users(id), phone VARCHAR(20), token_version INTEGER NOT NULL DEFAULT 0)")
        print(f"Account settings table added. Backup: {backup_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
