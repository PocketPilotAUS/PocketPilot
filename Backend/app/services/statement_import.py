"""Small CSV reader: financial facts are parsed, never inferred by the model."""
import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MAX_ROWS = 50
MAX_BYTES = 128 * 1024
CATEGORIES = ["Rent", "Entertainment", "Food", "Transport", "Shopping", "Subscriptions", "Bills", "Other"]
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


def review_rows(rows, labels, existing):
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
        if re.search(r"\b(transfer|credit card payment|card repayment|cash withdrawal|atm withdrawal)\b", row["description"], re.I):
            kind = "transfer"
        if row["direction"] == "credit" and kind == "expense" or row["direction"] == "debit" and kind == "income":
            kind = "review"
        if label.get("confidence", 0) < .8 and kind == "expense":
            kind = "review"
        row.update(kind=kind, category=label.get("category", "Other"))
    return rows
