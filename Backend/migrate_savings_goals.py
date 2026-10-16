"""Let manual savings entries count toward a financial plan.

Adds a nullable goal_id column to manual_savings. Existing entries stay
general savings (goal_id NULL); no other table or record is changed.
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. For a new database, run init_db.py first.")
    with sqlite3.connect(path) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='manual_savings'").fetchone():
            raise ValueError("Manual savings table not found. Run migrate_manual_savings.py first.")
        columns = {row[1] for row in db.execute("PRAGMA table_info(manual_savings)")}
        if "goal_id" in columns:
            print("Savings goals already up to date.")
            return
        backup_path = path.with_name(f"{path.stem}.backup-savings-goals-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup_path) as backup:
            db.backup(backup)
        db.execute("ALTER TABLE manual_savings ADD COLUMN goal_id VARCHAR(36)")
        db.execute("CREATE INDEX ix_manual_savings_goal_id ON manual_savings(goal_id)")
        print(f"Savings goals added. Backup: {backup_path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
