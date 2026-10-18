"""Opt-in E2/E5/E6 against real Ollama through /ai/chat and an isolated in-memory DB.
From Backend: venv/Scripts/python.exe tests/live_expense_cases.py --live [--no-think]
No mocks; no confirmation calls and no production account/database writes.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--no-think", action="store_true")
    args = parser.parse_args()
    if args.no_think:
        os.environ["OLLAMA_THINK"] = "false"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import Base, get_db
    from app.models.transaction import Transaction
    from app.models.chat_proposal import ChatProposal
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    def isolated():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = isolated
    failures = 0
    try:
        with TestClient(app) as client:
            client.post("/auth/register", json={"name": "Expense live", "email": "expense-live@example.com", "password": "expense-live-test-2026"})
            token = client.post("/auth/login", json={"email": "expense-live@example.com", "password": "expense-live-test-2026"}).json()["access_token"]
            headers = {"Authorization": "Bearer " + token}
            today = datetime.now(timezone(timedelta(hours=4))).date().isoformat()
            for name, turns, amount, category in [
                ("E2", ["Lunch cost me 50 today."], 50, "Food"),
                ("E5", ["I just bought groceries for 120.", "Today."], 120, "Groceries"),
                ("E6", ["Spent 75 on transport today."], 75, "Transport"),
            ]:
                history, state, passed = [], None, True
                for index, text in enumerate(turns):
                    history.append({"role": "user", "content": text})
                    response = client.post("/ai/chat", headers=headers, json={"messages": history, "record_state": state, "require_budget": True})
                    data = response.json()
                    print(json.dumps({"case": name, "text": text, "status": response.status_code,
                        "reply": data.get("reply", data.get("detail")), "proposal": data.get("proposal"), "has_draft": bool(data.get("record_state"))}), flush=True)
                    if response.status_code != 200:
                        passed = False
                        break
                    history.append({"role": "assistant", "content": data["reply"]})
                    state = data.get("record_state")
                    if index < len(turns) - 1:
                        passed &= data.get("proposal") is None and bool(state)
                    else:
                        proposal = data.get("proposal") or {}
                        passed &= (proposal.get("status") == "pending" and Decimal(str(proposal.get("amount", -1))) == amount
                                   and proposal.get("category") == category and proposal.get("date") == today)
                failures += not passed
                print(f"{name}: {'PASS' if passed else 'FAIL'}", flush=True)
            with factory() as db:
                count = db.query(Transaction).count()
                print(json.dumps({"pending_proposals": db.query(ChatProposal).count(), "saved_transactions": count}), flush=True)
                failures += count != 0
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
