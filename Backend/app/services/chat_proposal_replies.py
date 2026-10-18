"""Acknowledgments report persisted proposal state; confirmation stays on its endpoint."""
import json
import re
from decimal import Decimal
from app.routers.proposals import ProposedAction, expire_proposal

REFERENCE_WORD = re.compile(r"\b(?:that|this|it|previous|earlier|last)\b", re.I)


def proposal_acknowledgment(db, user_id, proposal, currency, rate):
    proposal = expire_proposal(db, user_id, proposal)
    status = proposal.status
    update = [{"id": proposal.id, "status": status}]
    payload = json.loads(proposal.payload)
    payload.pop("_expires_at", None)
    action = ProposedAction.model_validate(payload) if payload.get("kind") else None
    if action:
        amount = action.amount * (rate if currency == "CNY" else Decimal(1))
        label = f"{currency} {amount:,.2f} {action.category} expense" if action.kind == "expense" else f"{currency} {amount:,.2f} income proposal"
    else:
        label = "proposal"
    if status == "dismissed":
        return {"reply": f"That {label} was dismissed and can no longer be confirmed. Nothing was saved. If you want to record it, please create a new proposal.", "proposal_updates": update}
    if status == "expired":
        return {"reply": f"That {label} has expired and can no longer be confirmed. Nothing was saved. Please create a new proposal if you still want to record it.", "proposal_updates": update}
    if status == "saved":
        return {"reply": "That record was already saved. Nothing else has been recorded.", "proposal_updates": update}
    payload = json.loads(proposal.payload)
    payload.pop("_expires_at", None)
    action = ProposedAction.model_validate(payload)
    amount = action.amount * (rate if currency == "CNY" else Decimal(1))
    if action.kind == "expense":
        details = f"{currency} {amount:,.2f} {action.category} expense dated {action.date.isoformat()}"
    elif action.income_operation == "add":
        details = f"one-time {currency} {amount:,.2f} income receipt dated {action.date.isoformat()}"
    else:
        details = f"monthly income update to {currency} {amount:,.2f} for {action.year}-{action.month:02d}"
    return {"reply": f"Your {details} is still pending. Please use Confirm to save it or Dismiss to cancel. Nothing has been saved.",
            "proposal_updates": update}



def reference_candidates(history, semantic, latest, currency, rate):
    """Filter chat-owned rows using only selectors grounded in this user turn."""
    candidates = list(history)
    kinds = {kind for kind in ("expense", "income") if re.search(r"\b" + kind + r"\b", latest, re.I)}
    if len(kinds) == 1:
        kind = next(iter(kinds))
        candidates = [row for row in candidates if json.loads(row.payload).get("kind") == kind]
    # Resolve literal selectors even when the model recognizes cancellation but
    # omits its fields. Persisted facts supply labels, never new transaction data.
    from types import SimpleNamespace
    from app.services.chat_interpretation import stated_amounts
    amounts = stated_amounts([SimpleNamespace(role="user", content=latest)])
    if len(amounts) == 1:
        value = next(iter(amounts))
        factor = rate if currency == "CNY" else Decimal(1)
        candidates = [row for row in candidates if Decimal(str(json.loads(row.payload).get("amount", -1))) * factor == value]
    labels = []
    for row in candidates:
        payload = json.loads(row.payload)
        if any(label and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", latest, re.I)
               for label in (payload.get("category"), payload.get("description"))):
            labels.append(row)
    if labels:
        candidates = labels
    if semantic.category_text and semantic.category_text.casefold() in latest.casefold() and semantic.category:
        # A guessed category for a pronoun must not choose among multiple records.
        if re.search(r"\b" + re.escape(semantic.category) + r"\b", latest, re.I):
            candidates = [row for row in candidates if json.loads(row.payload).get("category") == semantic.category]
        else:
            described = [row for row in candidates if (json.loads(row.payload).get("description") or "").casefold() == semantic.category_text.casefold()]
            if described:
                candidates = described
    return candidates


def resolve_reference(db, user_id, history, semantic, latest, currency, rate):
    """Only IDs supplied by this chat and verified against account ownership qualify."""
    reference = semantic.proposal_reference
    if not (reference and reference.casefold() in latest.casefold()) and not REFERENCE_WORD.search(latest):
        return {"reply": "Which proposal do you mean? Nothing has been saved."}
    candidates = reference_candidates(history, semantic, latest, currency, rate)
    if not candidates:
        return {"reply": "I can't find that proposal in this chat. Please create a new proposal if you want to record a transaction. Nothing has been saved."}
    if len(candidates) != 1:
        return {"reply": "Which proposal do you mean? Please specify its amount and whether it is an expense or income. Nothing has been saved."}
    return proposal_acknowledgment(db, user_id, candidates[0], currency, rate)



def reference_turn(semantic, latest):
    """A mislabeled recording intent cannot turn an existing-record reference into intake."""
    if semantic.intent == "proposal":
        return True
    if semantic.intent != "record" or not semantic.proposal_reference:
        return False
    from app.services.chat_record_drafts import amount_value
    # Demonstratives/pronouns ground a backward reference. A fresh, user-stated
    # monetary amount remains a recording request, not an implicit reuse of history.
    return bool(REFERENCE_WORD.search(latest)) and amount_value(semantic.amount_text, latest) is None
