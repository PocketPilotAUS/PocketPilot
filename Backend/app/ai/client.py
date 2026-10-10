import os
import re
from urllib.parse import urlsplit, urlunsplit

class IncompleteAnswerError(ValueError):
    pass

import httpx
from dotenv import load_dotenv

load_dotenv()


def final_answer(data):
    if data.get("done") is not True or data.get("done_reason") == "length":
        raise IncompleteAnswerError("Model did not finish its answer")
    # Ollama returns reasoning in message.thinking; never forward that field.
    content = data.get("message", {}).get("content")
    if not isinstance(content, str):
        raise ValueError("Missing final answer")
    # Guard against tagged reasoning from model/template variants.
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    if re.search(r"</?think\b", content, re.IGNORECASE) or not content:
        raise ValueError("No complete final answer")
    return content


def generate_answer(messages, response_format=None):
    url = os.getenv("OLLAMA_URL")
    if not url:
        raise ValueError("OLLAMA_URL is not configured.")
    parts = urlsplit(url)
    base_path = parts.path.rstrip("/")
    if base_path.endswith("/v1"):
        base_path = base_path[:-3]
    endpoint = urlunsplit((parts.scheme, parts.netloc, base_path + "/api/chat", "", ""))
    with httpx.Client(timeout=180.0) as client:
        response = client.post(endpoint, json={
            "model": "qwen3:4b", "messages": messages,
            "think": True, "stream": False,
            "options": {"num_predict": 8192},
            **({"format": response_format} if response_format else {}),
        })
        response.raise_for_status()
        return final_answer(response.json())


def generate_ai_explanation(prompt):
    return generate_answer([
        {"role": "system", "content": (
            "You are PocketPilot, a personal finance assistant. Explain verified financial information clearly. "
            "Do not invent amounts, percentages, or balances. Do not assume why spending changed. "
            "Keep the final answer short, practical, and addressed directly to the user."
        )},
        {"role": "user", "content": prompt},
    ])


def generate_chat_reply(messages):
    return generate_answer(messages, {
        "type": "object", "properties": {
            "reply": {"type": "string", "minLength": 1},
            "action": {"anyOf": [{"type": "null"}, {"type": "object", "properties": {
                "kind": {"enum": ["expense", "income"]}, "amount": {"type": "number"},
                "category": {"type": "string"}, "date": {"type": "string"},
                "year": {"type": "integer"}, "month": {"type": "integer"}
            }, "required": ["kind", "amount"], "additionalProperties": False}]}
        }, "required": ["reply", "action"], "additionalProperties": False
    })
