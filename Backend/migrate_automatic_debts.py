"""Add opt-in automatic instalments; preserve existing balances and payment history."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. Initialize new databases first.")
    changes = {"debts": {"total_due_cents": "INTEGER", "fixed_monthly_cents": "INTEGER", "automatic_day": "INTEGER", "next_due": "DATE"},
               "debt_payments": {"applied_cents": "INTEGER NOT NULL DEFAULT 0", "automatic": "BOOLEAN NOT NULL DEFAULT 0"}}
    with sqlite3.connect(path) as db:
        missing = []
        for table, fields in changes.items():
            columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
            if not columns:
                raise ValueError(f"Run the existing {table} migration first.")
            missing += [(table, name, kind) for name, kind in fields.items() if name not in columns]
        if not missing:
            print("Automatic debt payments already up to date.")
            return
        backup = path.with_name(f"{path.stem}.backup-auto-debts-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup) as target:
            db.backup(target)
        for table, name, kind in missing:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")
        print(f"Automatic debt payments added. Backup: {backup.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
