"""Validated semantic routing and user-grounded proposal evidence."""
import re
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.services.chat_context import _user_text, _requested_category


class ChatInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Literal["read", "record", "plan", "clarify", "unsupported", "cancel", "proposal", "financial_plan"]
    topic: Literal["debt", "savings", "budget", "general"]
    proposal_reference: str | None = Field(default=None, max_length=400, description="Exact latest USER text referring to an existing proposed record or its confirmation/status. Null for a fresh recording request, education or cancellation.")
    income_operation: Literal["add", "replace"] | None = Field(default=None, description="Income receipt/additional income: add. Setting a monthly total: replace. Also extract this for read-only hypothetical income scenarios; null for a lookup or non-income task.")
    savings_operation: Literal["affordability", "goal"] | None = Field(default=None, description="affordability: evaluate putting money aside without creating a named total-target goal. goal: create or adjust an explicitly user-stated savings goal. Extract amount_text for affordability too.")
    protected_categories: list[str] = Field(default_factory=list, max_length=40, description="Budget categories the USER explicitly says must not change; preserve their category names. Empty if none.")
    continuation: bool
    kind: Literal["expense", "income"] | None = Field(description="Financial operation discussed, including income in a read-only hypothetical. Null for lookups without a hypothetical amount.")
    amount_text: str | None = Field(max_length=80, description="Exact user money token for the recording request OR read-only hypothetical financial scenario, never a model-computed value.")
    category_text: str | None = Field(max_length=200)
    category: str | None = Field(max_length=40)
    clarification: str | None = Field(max_length=400)

    def supports(self, messages, action):
        if self.intent != "record" or action.kind != self.kind or not self.amount_text:
            return False
        latest = _user_text(messages[-1].content)
        # Explicit non-action language vetoes a mistaken model classification.
        if re.search(r"\b(?:what if|hypothetic\w*|might|would have|how would|do not|don't|dont|never)\b", latest, re.I):
            return False
        if re.fullmatch(r"(?:yes|yep|yeah|ok|okay|sure|sounds good)[.! ]*", latest, re.I):
            return False
        # Only the current task's immediately preceding user turn may supply a
        # missing detail. Older conversation and assistant suggestions aren't evidence.
        text = _user_text(messages[-1].content)
        if self.continuation and len(messages) >= 3:
            text = _user_text(messages[-3].content) + " " + text
        # Dates cannot serve as monetary evidence. Multiple distinct amounts
        # require clarification rather than choosing the model's preferred one.
        money_text = re.sub(r"\b\d{4}-\d{1,2}(?:-\d{1,2})?\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", "", latest)
        if (re.search(r"\b(?:or|and|plus|instead of)\s+(?:(?:AED|CNY)\s+)?\d", money_text, re.I)
                and len(re.findall(r"(?<!\w)\d[\d,]*(?:\.\d+)?\s*[kK]?", without_dates(money_text))) > 1):
            return False
        evidence_without_dates = without_dates(text)
        token = self.amount_text.strip()
        if not re.search(r"(?<![\w.,-])" + re.escape(token) + r"(?!\w|[.,]\d)", evidence_without_dates, re.I):
            return False
        if not re.fullmatch(r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?\s*[kK]?", token):
            return False
        value = Decimal(token.lower().replace(",", "").replace(" ", "").rstrip("k"))
        if token.lower().endswith("k"):
            value *= 1000
        if value != action.amount:
            return False
        # Preserve deterministic rejection of conflicting explicit categories.
        if action.kind == "expense":
            if not self.category_text or self.category_text.casefold() not in text.casefold():
                return False
            from app.schemas.planning import CATEGORIES
            from app.services.planning import ALIASES
            aliases = {name.casefold(): name for name in (*CATEGORIES, "Groceries")}
            aliases.update(ALIASES)
            mentioned = {category for label, category in aliases.items()
                         if re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", text, re.I)}
            if len(mentioned) > 1:
                return False
            known = _requested_category(text)
            canonical_labels = {name.casefold() for name in (*CATEGORIES, "Groceries")}
            proposed = ALIASES.get(action.category.casefold(), action.category)
            explicit_label = bool(re.search(r"\bcategory\b|[\"']", text, re.I))
            if known is not None and (known.casefold() in canonical_labels or explicit_label):
                if known.casefold() != proposed.casefold():
                    return False
            elif not self.category or self.category.casefold() != action.category.casefold():
                return False
        return True


def stated_amounts(messages):
    """Literal monetary candidates only; dates and assistant figures are excluded."""
    text = " ".join(_user_text(message.content) for message in messages if message.role == "user")
    text = without_dates(text)
    return {Decimal(number.replace(",", "")) * (1000 if thousands else 1)
            for number, thousands in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*(k\b)?", text, re.I)}


def without_dates(text):
    from app.services.chat_records import MONTHS
    text = re.sub(r"\b\d{4}-\d{1,2}(?:-\d{1,2})?\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", "", text)
    names = "|".join(sorted(MONTHS, key=len, reverse=True))
    return re.sub(rf"\b(?:{names})\s+\d{{1,2}}(?:st|nd|rd|th)?[,]?\s+\d{{4}}\b|"
                  rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{names})[,]?\s+\d{{4}}\b|"
                  rf"\b(?:{names})\s+\d{{4}}\b", "", text, flags=re.I)
