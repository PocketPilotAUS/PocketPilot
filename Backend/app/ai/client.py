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


def thinking_enabled():
    # Reasoning stays on by default; OLLAMA_THINK=false turns it off on machines
    # where qwen3 reasoning exceeds the request timeout.
    return os.getenv("OLLAMA_THINK", "true").strip().lower() not in ("0", "false", "no", "off")


def generate_answer(messages, response_format=None, think=None, options=None):
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
            "think": thinking_enabled() if think is None else think, "stream": False,
            "options": {"num_predict": 8192, **(options or {})},
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
    from app.schemas.planning import PlanningInput, CATEGORIES
    profile_schema = PlanningInput.model_json_schema()
    # Retain compatibility with existing saved plans, but restore the earlier
    # conversational extraction protocol instead of requesting a chosen rate.
    profile_schema["properties"].pop("monthly_contribution", None)
    # Constrain category labels at generation time instead of allowing arbitrary keys
    # that the profile validator must reject afterwards.
    profile_schema["properties"]["expenses"] = {
        "type": "object", "properties": {category: {"type": ["number", "null"], "minimum": 0, "maximum": 1000000000} for category in CATEGORIES},
        "additionalProperties": False,
        "description": "Only explicitly supplied monthly baseline costs; omit unknown categories."
    }
    profile_schema["properties"]["protected_categories"] = {
        "type": "array", "items": {"type": "string", "enum": list(CATEGORIES)},
        "description": "Only categories the user explicitly says must not be reduced."
    }
    # Dates are calculated by the server, never by the model: an exact date
    # only when the user states one, otherwise the number of months mentioned.
    profile_schema["properties"]["deadline"]["description"] = (
        "Only an exact calendar date the user explicitly stated, as YYYY-MM-DD. "
        "For a relative timeframe use deadline_in_months instead. Never calculate or guess a date."
    )
    profile_schema["properties"]["deadline_in_months"] = {
        "type": ["integer", "null"], "minimum": 1, "maximum": 600,
        "description": "Only when the user gives a relative timeframe for the goal: the number of months "
                       "(years times 12). The server converts it to a date. Null otherwise."
    }
    return generate_answer(messages, {
        "$defs": profile_schema.pop("$defs", {}),
        "type": "object", "properties": {
            "reply": {"type": "string", "minLength": 1},
            "planning": {"anyOf": [{"type": "null"}, profile_schema]},
            "action": {"anyOf": [{"type": "null"}, {"type": "object", "properties": {
                "kind": {"enum": ["expense", "income"]}, "amount": {"type": "number"},
                "category": {"type": "string"}, "date": {"type": "string"},
                "year": {"type": "integer"}, "month": {"type": "integer"}
            }, "required": ["kind", "amount"], "additionalProperties": False}]}
        }, "required": ["reply", "action", "planning"], "additionalProperties": False
    })


GOAL_FACT_FIELDS = ("goal", "goal_kind", "target_amount", "current_amount", "deadline")


def extract_goal_facts(messages):
    """Read the user's financial goal facts from the conversation as JSON.

    A short, focused extraction without reasoning, so it is fast and runs
    before the conversational reply. It only reports facts; the server
    validates them and calculates every amount and date.
    """
    from app.schemas.planning import PlanningInput
    schema = PlanningInput.model_json_schema()
    properties = {key: schema["properties"][key] for key in GOAL_FACT_FIELDS if key != "deadline"}
    # Debt goals keep their own verified flow; only savings and spending goals here.
    properties["goal_kind"] = {"enum": ["savings", "spending", None]}
    for key in ("target_amount", "current_amount"):
        properties[key] = {"type": ["number", "null"], "minimum": 0, "maximum": 1000000000}
    properties["deadline_in_months"] = {"type": ["integer", "null"], "minimum": 1, "maximum": 600}
    properties["deadline"] = schema["properties"]["deadline"]
    system = (
        "Extract the user's current financial goal from this conversation as JSON. Use only facts the USER stated; "
        "assistant messages are context, never facts. If the user changed a value, use their latest one. "
        "goal: short name of what they are saving for or limiting spending on. goal_kind: savings or spending. "
        "target_amount: the goal amount. current_amount: money already saved toward this goal, only if stated. "
        "deadline: only an exact calendar date the user stated, as YYYY-MM-DD. "
        "deadline_in_months: only a relative timeframe the user stated, as a number of months (years times 12). "
        "Never calculate, guess or default a value: use null for anything not stated. "
        "If the user has not described a financial goal, return every field as null."
    )
    return generate_answer([{"role": "system", "content": system}] + messages, {
        "$defs": schema.get("$defs", {}),
        "type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False,
    }, think=False, options={"temperature": 0})


def generate_budget_adjustment(context, instructions=None, mode="adjust"):
    """Suggest month-end spending limits and tips for the rest of this month as JSON.

    mode: "advice" (level 1, goal still affordable: tips only), "adjust"
    (level 2: reduce projected spending to keep the savings target) or
    "recovery" (level 3: reduce the gap that can't be fully closed).
    Suggestions only: the server validates every amount and computes all totals.
    """
    import json
    names = [row["category"] for row in context["categories"]]
    rules = (
        "Amounts are in AED; never use $ or dollars. Use only the data given; do not invent categories, income or obligations. "
        "A limit is the most the user would spend in a category by month-end, including what is already spent. "
        "It must be between 'lowest_realistic_limit' and 'projected'. Never change categories marked fixed (bills, rent). "
        "Money already spent can't be recovered, and a limit is not money saved: it only avoids future spending if the user keeps to it. "
        "Keep essentials such as food realistic for 'days_left' days; do not suggest stopping them. "
        "Each reason says what the user should do for the rest of the month, under 25 words. "
        "If the user gave instructions, follow them. "
    )
    if mode == "advice":
        task = ("The user's savings goal is still affordable this month: nothing needs to be recovered. Return an empty "
                "'changes' list and do not suggest changing budgets, savings contributions or deadlines. Give up to 3 practical "
                "tips for the rest of the month about the categories in 'over_budget'. ")
    elif mode == "recovery":
        task = ("Recorded spending and bills already leave less than the savings goal needs this month, so it can't be fully met. "
                "Suggest realistic limits that reduce projected spending by up to 'goal_amount'. Up to 2 tips. ")
    else:
        task = ("Projected spending puts the savings goal at risk by 'goal_amount'. Suggest realistic limits that reduce projected "
                "spending by about that amount, no more than needed. If that isn't realistic, suggest what is. Up to 2 tips. ")
    content = json.dumps({**context, **({"user_instructions": instructions} if instructions else {})})
    return generate_answer([{"role": "system", "content": "You are PocketPilot. " + task + rules}, {"role": "user", "content": content}], {
        "type": "object", "properties": {
            "changes": {"type": "array", "maxItems": 0 if mode == "advice" else 12, "items": {
                "type": "object", "properties": {
                    "category": {"enum": names}, "limit": {"type": "number", "minimum": 0},
                    "reason": {"type": "string", "maxLength": 200}},
                "required": ["category", "limit", "reason"], "additionalProperties": False}},
            "tips": {"type": "array", "maxItems": 3, "items": {"type": "string", "maxLength": 200}}},
        "required": ["changes", "tips"], "additionalProperties": False,
    }, think=False, options={"temperature": 0})
