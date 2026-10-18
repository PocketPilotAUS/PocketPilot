"""Opt-in live Ollama routing check. No account/database changes or mocked model.
Run from Backend: venv/Scripts/python.exe tests/live_chat_nlu.py --live
This checks interpretation only; it does not certify full conversation behavior.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ai.client import interpret_chat_turn
from app.services.chat_interpretation import ChatInterpretation

CASES = [
    ("Spent 50 on lunch.", "record", "budget"),
    ("Lunch was 50.", "record", "budget"),
    ("Can you add the 50 I paid for lunch?", "record", "budget"),
    ("I just bought groceries for 120.", "record", "budget"),
    ("How much have I spent on food?", "read", "budget"),
    ("What can I afford to save?", "plan", "savings"),
    ("I wanna save 5k for a laptop.", "plan", "savings"),
    ("I need to clear my car loan sooner.", "plan", "debt"),
    ("Forget the loan for now, how's my budget?", "read", "budget"),
    ("I earned 2k yesterday.", "record", "budget"),
    ("What's my income?", "read", "budget"),
    ("Can I save more without changing my rent budget?", "plan", "savings"),
    ("What if I spent 500 on groceries?", "read", "budget"),
    ("How would recording 2,000 income affect my budget?", "read", "budget"),
    ("I might buy a laptop.", "read", "general"),
    ("Explain how debt payments work.", "read", "debt"),
    ("I don't want to record this expense.", "read", "general"),
    ("800", "clarify", "general"),
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    args = parser.parse_args()
    failures = 0
    for text, expected, topic in CASES:
        try:
            value = ChatInterpretation.model_validate_json(interpret_chat_turn(
                [{"role": "user", "content": text}], {"currency": "AED"}))
            # Record/read topics don't select a calculator. Only planning topics matter.
            passed = value.intent == expected and (expected != "plan" or value.topic == topic)
            failures += not passed
            print(json.dumps({"text": text, "passed": passed, "expected": expected,
                              "interpretation": value.model_dump()}), flush=True)
        except Exception as error:
            failures += 1
            print(json.dumps({"text": text, "passed": False, "error": type(error).__name__}), flush=True)
    print(f"Live routing: {len(CASES) - failures}/{len(CASES)} passed")
    raise SystemExit(bool(failures))
