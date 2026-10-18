"""Amount-only turns need a current, grounded workflow and an amount question."""
import re
from app.services.chat_context import _user_text
from app.services.chat_record_drafts import NUMBER
from app.core.currency import display_context
from app.services.chat_savings import grounded


def standalone_amount(text):
    clean = _user_text(text).strip()
    match = re.fullmatch(r"(?:(?:AED|CNY)\s+)?(" + NUMBER + r")(?:\s+(?:AED|CNY))?[.!?]?", clean, re.I)
    return match.group(1).strip() if match else None


def amount_question(messages):
    """Validate the field asked by the assistant, not phrases users must memorize."""
    if len(messages) < 3:
        return None
    text = messages[-2].content.casefold()
    if "?" not in text or not re.search(r"\b(?:how much|amount|payment|contribution)\b", text):
        return None
    if re.search(r"\bextra\b", text):
        return "extra"
    if re.search(r"\b(?:monthly|month)\b", text):
        return "monthly"
    if re.search(r"\b(?:goal|target)\b", text):
        return "target"
    return "amount"


def planning_amount_workflow(body, user_id, today):
    """Client flags and model continuation alone never authorize an amount."""
    field = amount_question(body.messages)
    if body.debt_state:
        from app.services.debt_planning import unseal
        state = unseal(body.debt_state, user_id, "debt_conversation")
        if field in ("monthly", "extra") and state.get("debt_ids") and state.get("phase") in ("discuss", "review"):
            return ("debt", "extra_monthly" if field == "extra" else "monthly_payment")
    if field and body.goal_planning and body.planning_profile:
        raw = body.planning_profile.model_dump(mode="json")
        profile = grounded(display_context(raw, body.aed_to_cny) if body.currency == "CNY" else raw, body.messages, today)
        if profile.get("goal") and profile.get("goal_kind") != "debt":
            if profile.get("target_amount") is None and field in ("target", "amount"):
                return ("savings", "target_amount")
            if profile.get("target_amount") is not None and field in ("monthly", "extra"):
                return ("savings", "monthly_contribution")
    return None


def acknowledgment(text):
    """Recognize a content-free assent; it never authorizes a financial write."""
    return re.fullmatch(r"(?:yes|yep|yeah|okay|ok|sure)(?:[ ,]+please)?[.! ]*", _user_text(text).strip(), re.I) is not None


def has_explicit_question(messages):
    return len(messages) >= 3 and "?" in messages[-2].content
