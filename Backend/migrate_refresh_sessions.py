"""Add refresh-session tables; back up SQLite first. Safe to rerun."""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from app.models.refresh_session import RefreshSession, RefreshToken


def migrate(database):
    path = Path(database).resolve()
    if not path.is_file():
        raise ValueError("Database not found. Run init_db.py for a new installation.")
    with sqlite3.connect(path) as db:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if {"refresh_sessions", "refresh_tokens"} <= tables:
            print("Refresh sessions already up to date.")
            return
        if "users" not in tables:
            raise ValueError("Users table not found.")
        backup = path.with_name(f"{path.stem}.backup-refresh-{datetime.now():%Y%m%d-%H%M%S-%f}.db")
        with sqlite3.connect(backup) as destination:
            db.backup(destination)
    engine = create_engine("sqlite:///" + path.as_posix())
    try:
        RefreshSession.__table__.create(engine, checkfirst=True)
        RefreshToken.__table__.create(engine, checkfirst=True)
    finally:
        engine.dispose()
    print(f"Refresh sessions added. Backup: {backup.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", default=str(Path(__file__).with_name("pocketpilot.db")))
    migrate(parser.parse_args().database)
