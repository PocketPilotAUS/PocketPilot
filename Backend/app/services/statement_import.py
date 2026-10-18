"""Small CSV reader: financial facts are parsed, never inferred by the model."""
import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MAX_ROWS = 50
MAX_BYTES = 128 * 1024
CATEGORIES = ["Rent", "Entertainment", "Food", "Groceries", "Transport", "Shopping", "Subscriptions", "Bills", "Other"]
ALIASES = {
    "date": {"date", "transactiondate", "postingdate", "posteddate", "valuedate"},
    "description": {"description", "transactiondescription", "details", "narrative", "merchant", "particulars"},
    "amount": {"amount", "transactionamount", "signedamount"},
    "debit": {"debit", "debitamount", "withdrawal", "withdrawals", "moneyout"},
    "credit": {"credit", "creditamount", "deposit", "deposits", "moneyin"},
    "currency": {"currency", "currencycode", "ccy"},
}


def normalize(value):
    return re.sub(r"[^a-z]", "", value.lower())


def read_money(value, currency):
    text = value.strip().upper()
    codes = re.findall(r"\b[A-Z]{3}\b", text)
    if any(code != currency for code in codes):
        raise ValueError("Amount currency does not match the selected statement currency.")
    text = text.replace(currency, "").strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if not re.fullmatch(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?", text):
        raise ValueError("Use amounts such as 25.00 or 1,250.50 with a decimal point.")
    try:
        amount = Decimal(text.replace(",", ""))
        return -abs(amount) if negative else amount
    except InvalidOperation as error:
        raise ValueError("Invalid amount.") from error


def read_date(value, order):
    formats = ["%Y-%m-%d", "%Y/%m/%d"] + (["%d/%m/%Y", "%d-%m-%Y"] if order == "DMY" else ["%m/%d/%Y", "%m-%d-%Y"])
    for fmt in formats:
        try:
            result = datetime.strptime(value.strip(), fmt).date()
            if result > date.today():
                raise ValueError("Future transaction dates are not supported.")
            return result.isoformat()
        except ValueError:
            pass
    raise ValueError("Invalid or future date. Check the statement date format.")


def parse_statement(text, currency, order, amount_style, rate):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Choose a CSV smaller than 128 KB.")
    if "\x00" in text:
        raise ValueError("Choose a UTF-8 CSV, not a PDF or spreadsheet workbook.")
    text = text.lstrip("\ufeff")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect=dialect, strict=True)
    header = next(reader, [])
    columns = {}
    for key, aliases in ALIASES.items():
        matches = [index for index, name in enumerate(header) if normalize(name) in aliases]
        if len(matches) > 1:
            raise ValueError(f"More than one {key} column. Use a simpler CSV export.")
        if matches:
            columns[key] = matches[0]
    if not {"date", "description"}.issubset(columns) or not ("amount" in columns or "debit" in columns and "credit" in columns):
        raise ValueError("CSV needs Date, Description and Amount columns, or Date, Description, Debit and Credit. Headers must be on the first row.")
    rows, errors = [], []
    count = 0
    for line, cells in enumerate(reader, 2):
        if not any(cell.strip() for cell in cells):
            continue
        count += 1
        if count > MAX_ROWS:
            raise ValueError("This first version supports 50 transactions per CSV. Export a smaller date range.")
        try:
            if len(cells) != len(header):
                raise ValueError("Column count does not match the header.")
            get = lambda key: cells[columns[key]].strip()
            if "currency" in columns and get("currency").upper() not in ("", currency):
                raise ValueError("Row currency does not match the selected statement currency.")
            description = " ".join(get("description").split())
            if not description or len(description) > 500:
                raise ValueError("Description must contain 1 to 500 characters.")
            if "debit" in columns and "credit" in columns:
                debit = read_money(get("debit"), currency) if get("debit") else Decimal(0)
                credit = read_money(get("credit"), currency) if get("credit") else Decimal(0)
                if debit < 0 or credit < 0 or bool(debit) == bool(credit):
                    raise ValueError("Use a positive debit or credit, not both.")
                amount, direction = (debit, "debit") if debit else (credit, "credit")
            else:
                signed = read_money(get("amount"), currency)
                direction = "debit" if (signed < 0) == (amount_style == "negative_debits") else "credit"
                amount = abs(signed)
            aed = (amount / rate if currency == "CNY" else amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if aed <= 0 or aed > 1000000000:
                raise ValueError("Amount is zero, too small after conversion, or above the supported limit.")
            rows.append({"row_id": line, "date": read_date(get("date"), order), "description": description,
                         "amount_aed": str(aed), "source_amount": str(amount), "source_currency": currency,
                         "direction": direction})
        except ValueError as error:
            errors.append({"row_id": line, "message": str(error)})
    if not rows:
        raise ValueError("No valid transactions were found. Check the dates, amounts and CSV headers.")
    return rows, errors


def fingerprint(row):
    return (row["date"], Decimal(str(row["amount_aed"])).quantize(Decimal("0.01")), row["description"].strip().casefold())


# Match explicit purchase descriptions, not arbitrary substrings or amounts.
DESCRIPTION_CATEGORIES = {
    "Rent": r"\b(?:(?:apartment|house|flat|monthly)\s+rent|rent\s+(?:payment|for|installment|instalment))\b",
    "Groceries": r"\b(?:groceries|grocery|vegetables|fruit|toiletries|cleaning\s+(?:products|supplies)|household\s+(?:items|supplies|essentials))\b",
    "Food": r"\b(?:restaurant|cafeteria|cafe|coffee|bakery|breakfast|lunch|dinner|takeaway|food\s+delivery)\b",
    "Transport": r"\b(?:petrol|gasoline|fuel|taxi|metro|nol|parking|bus\s+(?:fare|ticket)|car\s+rental)\b",
    "Entertainment": r"\b(?:cinema|movie\s+tickets?|bowling|arcade|escape\s+room|pool\s+table|concert\s+tickets?)\b",
    "Shopping": r"\b(?:clothing|clothes|shoes|accessories|household\s+goods|online\s+shopping|laptop|smartphone|iphone|headphones|electronics)\b",
    "Subscriptions": r"\b(?:(?:music|video|cloud|streaming)\s+(?:streaming\s+|storage\s+)?subscription|netflix|spotify|icloud|youtube\s+premium)\b",
    "Bills": r"\b(?:(?:electricity|water|internet|mobile|phone|utility|utilities)\s+(?:and\s+water\s+)?bill|home\s+internet|broadband\s+bill)\b",
}
TRANSFER_DESCRIPTION = r"\b(?:transfer|credit\s+card\s+payment|card\s+repayment|cash\s+withdrawal|atm\s+withdrawal)\b"
INSTRUCTION_DESCRIPTION = r"\b(?:ignore\s+(?:all|previous|prior)|system\s+(?:prompt|message)|return\s+(?:json|only)|classify\s+(?:this|all)|set\s+(?:the\s+)?category)\b"


def description_category(description, categories=None):
    categories = categories or CATEGORIES
    text = " ".join(description.casefold().replace("-", " ").split())
    if re.search(INSTRUCTION_DESCRIPTION, text, re.I):
        return None
    available = {name.casefold(): name for name in categories}
    matches = {available[name.casefold()] for name, pattern in DESCRIPTION_CATEGORIES.items()
               if name.casefold() in available and re.search(pattern, text, re.I)}
    # Use a dedicated custom category only when the statement names it explicitly.
    custom = {name for name in categories if name not in CATEGORIES and
              re.search(r"(?<!\w)" + re.escape(name.casefold()) + r"(?!\w)", text)}
    if len(custom) == 1 and not matches:
        return next(iter(custom))
    if len(matches) == 1 and not custom:
        return next(iter(matches))
    if not matches and not custom and "groceries" in available and re.search(r"\b(?:supermarket|carrefour|lulu)\b", text):
        return available["groceries"]
    return None


def ambiguous_description(description, categories=None):
    if description_category(description, categories):
        return False
    text = " ".join(description.casefold().replace("-", " ").split())
    matches = [name for name, pattern in DESCRIPTION_CATEGORIES.items() if re.search(pattern, text, re.I)]
    return len(matches) > 1 or bool(re.search(r"\b(?:amazon|carrefour|lulu|apple)\b", text))


def review_rows(rows, labels, existing, categories=None):
    categories = categories or CATEGORIES
    existing_keys = {fingerprint(row) for row in existing}
    date_amount = {(key[0], key[1]) for key in existing_keys}
    seen = set()
    suggestions = {item["row_id"]: item for item in labels}
    for row in rows:
        key = fingerprint(row)
        row["possible_duplicate"] = key in seen or (key[0], key[1]) in date_amount
        seen.add(key)
        label = suggestions.get(row["row_id"], {})
        kind = label.get("kind", "review" if row["direction"] == "debit" else "income")
        category = label.get("category", "Other")
        confidence = label.get("confidence", 0)
        if row["direction"] == "credit":
            # Incoming money is never an importable expense, even if the model says so.
            kind = "income"
        elif re.search(INSTRUCTION_DESCRIPTION, row["description"], re.I):
            kind, category = "review", "Other"
        elif re.search(TRANSFER_DESCRIPTION, row["description"], re.I):
            kind, category = "transfer", "Other"
        elif ambiguous_description(row["description"], categories):
            kind, category = "review", "Other"
        else:
            explicit = description_category(row["description"], categories)
            if explicit:
                kind, category = "expense", explicit
            elif kind not in ("expense", "transfer", "review") or category not in categories or type(confidence) not in (int, float) or not 0.8 <= confidence <= 1:
                kind = "review"
        row.update(kind=kind, category=category if category in categories else "Other")
    return rows
