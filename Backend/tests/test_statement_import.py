import csv
import io
from decimal import Decimal
import jwt
import pytest
from conftest import register_user, login_user, auth_headers
from app.services.statement_import import parse_statement, review_rows


def signed_in(client, email="alice@example.com"):
    register_user(client, email=email)
    return auth_headers(login_user(client, email=email).json()["access_token"])


def labels(rows, categories):
    return [{"row_id": row["row_id"], "kind": "expense" if row["direction"] == "debit" else "income", "category": "Food", "confidence": .95} for row in rows]


def preview(client, headers, text="Date,Description,Amount\n01/10/2026,Lunch,-25.00\n02/10/2026,Salary,5000.00", **options):
    return client.post("/transactions/import/preview", headers=headers, json={"csv_text": text, "currency": "AED", **options})


def confirm(client, headers, result, selections=None):
    return client.post("/transactions/import/confirm", headers=headers, json={"preview_token": result["preview_token"], "selections": selections or [{"row_id": result["rows"][0]["row_id"], "category": "Food", "include_possible_duplicate": result["rows"][0]["possible_duplicate"]}]})


def test_signed_and_split_columns_and_currency_conversion():
    rows, errors = parse_statement('Date,Description,Amount\n01/10/2026,"Shop, City","(1,250.50)"\n2026-10-02,Refund,20', "AED", "DMY", "negative_debits", None)
    assert errors == []
    assert rows[0]["amount_aed"] == "1250.50"
    assert rows[0]["direction"] == "debit"
    assert rows[1]["direction"] == "credit"
    rows, errors = parse_statement('Date;Description;Debit;Credit;Currency\n10/01/2026;Food;50;;CNY\n10/02/2026;Salary;;1000;CNY', "CNY", "MDY", "negative_debits", Decimal(2))
    assert errors == []
    assert rows[0]["date"] == "2026-10-01"
    assert rows[0]["amount_aed"] == "25.00"
    assert rows[1]["direction"] == "credit"


@pytest.mark.parametrize("text", ["Date,Description,Balance\n2026-10-01,Food,50", "Date,Description,Amount\n30/02/2026,Food,-25", "Date,Description,Amount\n2026-10-01,Food,0", "Date,Description,Amount\n2026-10-01,Food,USD 25", "Date,Description,Debit,Credit\n2026-10-01,Food,50,50"])
def test_invalid_csv_rejected(text):
    with pytest.raises(ValueError):
        parse_statement(text, "AED", "DMY", "negative_debits", None)


def test_invalid_rows_are_reported_and_limits_are_not_silently_truncated():
    rows, errors = parse_statement('Date,Description,Amount\n2026-10-01,Food,-25\ninvalid,Shop,-30', "AED", "DMY", "negative_debits", None)
    assert len(rows) == 1
    assert errors[0]["row_id"] == 3
    with pytest.raises(ValueError, match="50 transactions"):
        parse_statement("Date,Description,Amount\n" + "2026-10-01,Food,-25\n" * 51, "AED", "DMY", "negative_debits", None)
    with pytest.raises(ValueError, match="128 KB"):
        parse_statement("x" * (128 * 1024 + 1), "AED", "DMY", "negative_debits", None)


def test_guarded_classification_and_duplicate_flags():
    rows, _ = parse_statement('Date,Description,Amount\n2026-10-01,Credit card payment,-25\n2026-10-02,Refund,10\n2026-10-03,Shop,-30', "AED", "DMY", "negative_debits", None)
    result = review_rows(rows, labels(rows, []), [{"date": "2026-10-03", "amount_aed": 30, "description": "Manual expense"}])
    assert result[0]["kind"] == "transfer"
    assert result[1]["kind"] != "expense"
    assert result[2]["possible_duplicate"] is True


def test_preview_and_confirm_require_auth(api_client):
    assert api_client.post("/transactions/import/preview", json={"csv_text": "x", "currency": "AED"}).status_code == 401
    assert api_client.post("/transactions/import/confirm", json={"preview_token": "x", "selections": [{"row_id": 2, "category": "Food"}]}).status_code == 401


def test_preview_is_read_only_and_confirm_is_retry_safe(api_client, monkeypatch):
    auth = signed_in(api_client)
    monkeypatch.setattr("app.routers.statement_import.classify_statement", labels)
    response = preview(api_client, auth)
    assert response.status_code == 200
    result = response.json()
    assert result["rows"][0]["kind"] == "expense"
    assert result["rows"][1]["kind"] == "income"
    assert api_client.get("/transactions/", headers=auth).json() == []
    assert confirm(api_client, auth, result).json() == {"added": 1, "skipped_duplicates": 0}
    assert confirm(api_client, auth, result).json() == {"added": 0, "skipped_duplicates": 1}
    transactions = api_client.get("/transactions/", headers=auth).json()
    assert len(transactions) == 1 and transactions[0]["amount"] == 25


def test_ai_failure_still_allows_manual_review(api_client, monkeypatch):
    auth = signed_in(api_client)
    monkeypatch.setattr("app.routers.statement_import.classify_statement", lambda *args: (_ for _ in ()).throw(ValueError("offline")))
    result = preview(api_client, auth).json()
    assert result["ai_available"] is False
    assert result["rows"][0]["kind"] == "review"
    assert confirm(api_client, auth, result).json()["added"] == 1


def test_credits_wrong_owner_and_tampered_tokens_rejected(api_client, monkeypatch):
    alice = signed_in(api_client)
    bob = signed_in(api_client, "bob@example.com")
    monkeypatch.setattr("app.routers.statement_import.classify_statement", labels)
    result = preview(api_client, alice).json()
    assert confirm(api_client, bob, result).status_code == 422
    credit = [{"row_id": result["rows"][1]["row_id"], "category": "Food"}]
    assert confirm(api_client, alice, result, credit).status_code == 422
    result["preview_token"] = result["preview_token"][:-8] + "aaaaaaaa"
    assert confirm(api_client, alice, result).status_code == 422
    assert api_client.get("/transactions/", headers=alice).json() == []


def test_duplicates_are_scoped_to_current_user_and_require_review(api_client, monkeypatch):
    alice = signed_in(api_client)
    bob = signed_in(api_client, "bob@example.com")
    monkeypatch.setattr("app.routers.statement_import.classify_statement", labels)
    api_client.post("/transactions/", headers=bob, json={"amount": 25, "date": "2026-10-01", "category": "Food", "description": "Lunch"})
    result = preview(api_client, alice).json()
    assert result["rows"][0]["possible_duplicate"] is False
    api_client.post("/transactions/", headers=alice, json={"amount": 25, "date": "2026-10-01", "category": "Food", "description": "Another shop"})
    result = preview(api_client, alice).json()
    assert result["rows"][0]["possible_duplicate"] is True
    selection = [{"row_id": 2, "category": "Food"}]
    assert confirm(api_client, alice, result, selection).status_code == 422
    selection[0]["include_possible_duplicate"] = True
    assert confirm(api_client, alice, result, selection).json()["added"] == 1


def test_confirmation_is_atomic_with_invalid_selection(api_client, monkeypatch):
    auth = signed_in(api_client)
    monkeypatch.setattr("app.routers.statement_import.classify_statement", labels)
    result = preview(api_client, auth).json()
    assert confirm(api_client, auth, result, [{"row_id": 2, "category": "Food"}, {"row_id": 999, "category": "Other"}]).status_code == 422
    assert api_client.get("/transactions/", headers=auth).json() == []


def test_yuan_import_pins_original_aed_amount(api_client, monkeypatch):
    auth = signed_in(api_client)
    monkeypatch.setattr("app.routers.statement_import.classify_statement", labels)
    result = preview(api_client, auth, "Date,Description,Amount\n2026-10-01,Lunch,-50", currency="CNY", aed_to_cny=2).json()
    assert result["rows"][0]["amount_aed"] == "25.00"
    assert confirm(api_client, auth, result).json()["added"] == 1
    assert api_client.get("/transactions/", headers=auth).json()[0]["amount"] == 25
