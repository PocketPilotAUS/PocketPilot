"""Recover unambiguous user-stated goal facts, never assistant monetary claims."""
import re
from datetime import datetime
from decimal import Decimal

NUMBER = r"(\d[\d,]*(?:\.\d{1,2})?\s*[kK]?)"
UNIT = r"\s*(AED|CNY|dhs|dirhams?|yuan)?\s*"


def recover(profile, messages, currency="AED", rate=None):
    result = dict(profile)
    previous_assistant = ""
    def amount(match):
        raw = match.group(1).replace(',', '').replace(' ', '')
        value = Decimal(raw[:-1]) * 1000 if raw.lower().endswith('k') else Decimal(raw)
        unit = (match.group(2) or currency).upper()
        if unit in ("CNY", "YUAN"):
            if rate is None:
                return None
            value = (value / rate).quantize(Decimal('.01'))
        return str(value) if value <= 1_000_000_000 else None
    for message in messages:
        if message.role == 'assistant':
            previous_assistant = message.content
            continue
        content = message.content.split('\n[Currency for untagged')[0].strip()
        # Currency metadata applies to this message, not all prior turns.
        tagged = re.search(r'Currency for untagged amounts in this message: (AED|CNY)', message.content)
        message_currency = tagged.group(1) if tagged else currency
        original_currency = currency
        currency = message_currency
        goal = re.search(r"\b(?:buy|purchase|save for|saving for)\s+(?:(?:a|an|new)\s+)*(.+?)(?=\s+for\s+\d|,|\.|;|\s+i want|$)", content, re.I)
        if goal:
            label = goal.group(1).strip()
            if label and not re.match(r'\d', label) and not re.search(r'\b(?:goal|specific date|budget)\b',label,re.I) and len(label)<=200:
                if result.get('goal') and result['goal'].casefold() != label.casefold():
                    result['current_amount'] = None
                    result['target_amount'] = None
                    result['monthly_contribution'] = None
                    result['deadline'] = None
                result['goal'] = label
                result['goal_kind'] = 'savings'
        target = re.search(r'\b(?:costs?|price(?: is)?|target(?: is)?|want to save|save|for)\s*'+NUMBER+UNIT,content,re.I)
        if target and (goal or re.search(r'\b(?:costs?|price|target|want to save)\b',content,re.I)):
            tail=content[target.end():]
            if not re.match(r'(?:per|a|each)\s+month|monthly',tail,re.I):
                value=amount(target)
                if value is not None: result['target_amount']=value
        monthly=re.search(NUMBER+UNIT+r'(?:per|a|each)\s+month\b',content,re.I)
        if monthly is None and re.search(r'per month|monthly',previous_assistant,re.I):
            monthly=re.search(r"\b(?:let'?s go(?: with)?|lets go(?: with)?|choose|set aside)\s+"+NUMBER+UNIT,content,re.I)
        if monthly:
            value=amount(monthly)
            if value is not None and Decimal(value)>0: result['monthly_contribution']=value
        progress=re.search(r'\b(?:already saved|have saved|saved so far)\s*'+NUMBER+UNIT,content,re.I)
        if progress:
            value=amount(progress)
            if value is not None: result['current_amount']=value
        explicit_date=re.search(r'\b(\d{4}-\d{2}-\d{2})\b',content)
        natural_date=re.search(r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?[,]?\s+\d{4})\b',content,re.I)
        parsed=None
        try:
            if explicit_date: parsed=datetime.strptime(explicit_date.group(1),'%Y-%m-%d').date()
            elif natural_date: parsed=datetime.strptime(re.sub(r'(\d)(st|nd|rd|th)|,',lambda m:m.group(1) or '',natural_date.group(1),flags=re.I),'%B %d %Y').date()
        except ValueError:
            pass
        if parsed:
            result['deadline']=parsed.isoformat()
            if monthly is None: result['monthly_contribution']=None
        currency=original_currency
    return result
