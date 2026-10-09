from datetime import date, timedelta

import jwt
import pytest

from app.core.config import JWT_ALGORITHM
from app.core.security import create_access_token
from app.main import compare_spending, get_recommendations
from app.models.transaction import Transaction
from conftest import auth_headers, login_user, register_user

NOT_AUTHENTICATED = {"detail": "Could not validate credentials."}
NOT_FOUND = {"detail": "Transaction not found"}

# Each user's data is chosen so that mixing them would change every result:
# Alice's Food rises 50% (a recommendation); Bob's Food is flat (none);
# combined, Food would rise only about 20%.
ALICE_TRANSACTIONS = [
    {"amount": 100, "category": "Food", "description": "Groceries", "date": "2026-09-15"},
    {"amount": 150, "category": "Food", "description": "Groceries", "date": "2026-10-08"},
    {"amount": 40, "category": "Transport", "date": "2026-10-09"},
]
BOB_TRANSACTIONS = [
    {"amount": 400, "category": "Food", "date": "2026-09-10"},
    {"amount": 400, "category": "Food", "date": "2026-10-10"},
    {"amount": 900, "category": "Rent", "description": "Bob's rent", "date": "2026-10-01"},
]

PROTECTED_ENDPOINTS = [
    ("post", "/transactions/"),
    ("get", "/transactions/"),
    ("delete", "/transactions/1"),
    ("get", "/spending/summary"),
    ("get", "/spending/compare?year=2026&month=10"),
    ("get", "/recommendations/?year=2026&month=10"),
    ("get", "/recommendations/ai?year=2026&month=10"),
]

VALID_TRANSACTION = {"amount": 10, "category": "Food", "date": "2026-10-08"}


class User:
    def __init__(self, client, name, email):
        password = f"{name.lower()}-password-1"
        response = register_user(client, name=name, email=email, password=password)
        assert response.status_code == 201

        self.id = response.json()["id"]
        self.client = client
        self.headers = auth_headers(
            login_user(client, email=email, password=password).json()["access_token"]
        )

    def request(self, method, path, headers=None, **kwargs):
        return self.client.request(
            method, path, headers={**self.headers, **(headers or {})}, **kwargs
        )

    def add(self, transaction):
        response = self.request("post", "/transactions/", json=transaction)
        assert response.status_code == 201
        return response.json()

    def get(self, path):
        response = self.request("get", path)
        assert response.status_code == 200
        return response.json()


@pytest.fixture
def alice(api_client):
    return User(api_client, "Alice", "alice@example.com")


@pytest.fixture
def bob(api_client):
    return User(api_client, "Bob", "bob@example.com")


@pytest.fixture
def carol(api_client):
    # A third user with no transactions at all
    return User(api_client, "Carol", "carol@example.com")


@pytest.fixture
def populated(alice, bob):
    for transaction in ALICE_TRANSACTIONS:
        alice.add(transaction)

    for transaction in BOB_TRANSACTIONS:
        bob.add(transaction)

    return alice, bob


@pytest.fixture
def legacy_transaction(db_session):
    # A row created before authentication existed: it has no owner
    transaction = Transaction(
        amount=5000,
        category="Legacy",
        description="Created before accounts existed",
        date=date(2026, 10, 5)
    )
    db_session.add(transaction)
    db_session.commit()
    return transaction.id


def request(client, method, path, headers=None):
    kwargs = {"json": VALID_TRANSACTION} if method == "post" else {}
    return client.request(method, path, headers=headers or {}, **kwargs)


# Authentication is required

@pytest.mark.parametrize("method, path", PROTECTED_ENDPOINTS)
def test_requires_authentication(api_client, method, path):
    response = request(api_client, method, path)

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("method, path", PROTECTED_ENDPOINTS)
@pytest.mark.parametrize("token_kind", ["garbage", "expired", "tampered", "wrong_secret", "unknown_user"])
def test_rejects_invalid_tokens(api_client, alice, method, path, token_kind):
    valid = alice.headers["Authorization"].removeprefix("Bearer ")
    header, payload, signature = valid.split(".")

    token = {
        "garbage": "not-a-token",
        "expired": create_access_token(alice.id, expires_delta=timedelta(seconds=-1)),
        "tampered": f"{header}.{payload}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}",
        "wrong_secret": jwt.encode(
            {"sub": str(alice.id), "type": "access", "iat": 1, "exp": 9999999999},
            "w" * 64,
            algorithm=JWT_ALGORITHM
        ),
        "unknown_user": create_access_token(999)
    }[token_kind]

    response = request(api_client, method, path, headers=auth_headers(token))

    assert response.status_code == 401
    assert response.json() == NOT_AUTHENTICATED


def test_unauthenticated_create_saves_nothing(api_client, db_session):
    request(api_client, "post", "/transactions/")

    assert db_session.query(Transaction).count() == 0


def test_authentication_checked_before_input_validation(api_client):
    # An invalid month still gets 401, so nothing is processed for anonymous users
    response = api_client.get("/spending/compare?year=2026&month=13")

    assert response.status_code == 401


def test_health_check_is_public(api_client):
    assert api_client.get("/").status_code == 200


# Creating transactions

def test_new_transaction_owned_by_token_user(alice, db_session):
    created = alice.add(VALID_TRANSACTION)

    assert db_session.get(Transaction, created["id"]).user_id == alice.id


def test_response_format_unchanged(alice):
    created = alice.add({**VALID_TRANSACTION, "description": "Lunch"})

    assert set(created) == {"id", "amount", "category", "description", "date"}


@pytest.mark.parametrize("field", ["user_id", "owner", "owner_id"])
def test_client_supplied_owner_is_rejected(alice, bob, db_session, field):
    response = alice.request("post", "/transactions/", json={**VALID_TRANSACTION, field: bob.id})

    assert response.status_code == 422
    assert db_session.query(Transaction).count() == 0
    assert bob.get("/transactions/") == []


def test_client_supplied_id_is_rejected(alice, bob, db_session):
    bob_transaction = bob.add(VALID_TRANSACTION)

    response = alice.request(
        "post", "/transactions/", json={**VALID_TRANSACTION, "id": bob_transaction["id"]}
    )

    assert response.status_code == 422
    assert db_session.query(Transaction).count() == 1
    assert db_session.get(Transaction, bob_transaction["id"]).user_id == bob.id


def test_mobile_app_request_format_accepted(alice):
    # Exactly what Mobile/src/screens/AddTransactionScreen.tsx sends
    for description in ("Coffee", None):
        response = alice.request("post", "/transactions/", json={
            "amount": 4.5,
            "category": "Food",
            "description": description,
            "date": "2026-10-09"
        })

        assert response.status_code == 201


# Listing transactions

def test_each_user_lists_only_own_transactions(populated):
    alice, bob = populated

    alice_list = alice.get("/transactions/")
    bob_list = bob.get("/transactions/")

    assert [t["amount"] for t in alice_list] == [100, 150, 40]
    assert [t["amount"] for t in bob_list] == [400, 400, 900]
    assert not {t["id"] for t in alice_list} & {t["id"] for t in bob_list}


def test_new_user_sees_no_transactions(populated, carol):
    assert carol.get("/transactions/") == []


# Deleting transactions

def test_cannot_delete_other_users_transaction(populated, db_session):
    alice, bob = populated
    bob_transaction_id = bob.get("/transactions/")[0]["id"]

    response = alice.request("delete", f"/transactions/{bob_transaction_id}")

    assert response.status_code == 404
    assert response.json() == NOT_FOUND
    assert db_session.get(Transaction, bob_transaction_id) is not None
    assert len(bob.get("/transactions/")) == len(BOB_TRANSACTIONS)


def test_other_users_transaction_looks_like_missing_one(populated):
    alice, bob = populated
    bob_transaction_id = bob.get("/transactions/")[0]["id"]

    others = alice.request("delete", f"/transactions/{bob_transaction_id}")
    missing = alice.request("delete", "/transactions/99999")

    assert (others.status_code, others.json()) == (missing.status_code, missing.json())


def test_owner_can_delete_own_transaction(populated):
    alice, bob = populated
    alice_transaction_id = alice.get("/transactions/")[0]["id"]

    assert alice.request("delete", f"/transactions/{alice_transaction_id}").status_code == 200
    assert len(alice.get("/transactions/")) == len(ALICE_TRANSACTIONS) - 1
    assert len(bob.get("/transactions/")) == len(BOB_TRANSACTIONS)


# Unowned legacy transactions

def test_legacy_transaction_hidden_from_everyone(populated, legacy_transaction):
    alice, bob = populated

    for user in (alice, bob):
        assert legacy_transaction not in [t["id"] for t in user.get("/transactions/")]
        assert "Legacy" not in user.get("/spending/summary")["category_spending"]
        assert "Legacy" not in user.get("/spending/compare?year=2026&month=10")["current_spending"]


def test_legacy_transaction_cannot_be_deleted(alice, legacy_transaction, db_session):
    response = alice.request("delete", f"/transactions/{legacy_transaction}")

    assert response.status_code == 404
    assert db_session.get(Transaction, legacy_transaction) is not None


def test_new_user_sees_no_legacy_data(carol, legacy_transaction):
    assert carol.get("/transactions/") == []
    assert carol.get("/spending/summary")["total_spending"] == 0


# Spending summary

def test_summary_is_per_user(populated):
    alice, bob = populated

    assert alice.get("/spending/summary") == {
        "total_spending": 290,
        "category_spending": {"Food": 250, "Transport": 40},
        "category_percentages": {"Food": 86.21, "Transport": 13.79}
    }
    assert bob.get("/spending/summary") == {
        "total_spending": 1700,
        "category_spending": {"Food": 800, "Rent": 900},
        "category_percentages": {"Food": 47.06, "Rent": 52.94}
    }


def test_summary_empty_for_user_without_transactions(populated, carol):
    assert carol.get("/spending/summary") == {
        "total_spending": 0,
        "category_spending": {},
        "category_percentages": {}
    }


def test_summary_unaffected_by_other_users_changes(populated):
    alice, bob = populated
    before = alice.get("/spending/summary")

    bob.add({"amount": 999, "category": "Food", "date": "2026-10-08"})
    bob.request("delete", f"/transactions/{bob.get('/transactions/')[0]['id']}")

    assert alice.get("/spending/summary") == before


# Monthly comparison

def test_comparison_is_per_user(populated):
    alice, bob = populated

    alice_comparison = alice.get("/spending/compare?year=2026&month=10")
    bob_comparison = bob.get("/spending/compare?year=2026&month=10")

    assert alice_comparison["current_spending"] == {"Food": 150, "Transport": 40}
    assert alice_comparison["previous_spending"] == {"Food": 100}
    assert alice_comparison["percentage_changes"]["Food"] == 50.0

    assert bob_comparison["current_spending"] == {"Food": 400, "Rent": 900}
    assert bob_comparison["previous_spending"] == {"Food": 400}
    assert bob_comparison["percentage_changes"]["Food"] == 0.0


def test_comparison_empty_for_user_without_transactions(populated, carol):
    comparison = carol.get("/spending/compare?year=2026&month=10")

    assert comparison["current_spending"] == {}
    assert comparison["previous_spending"] == {}
    assert comparison["percentage_changes"] == {}


# Recommendations

def test_recommendations_are_per_user(populated):
    alice, bob = populated

    alice_recommendations = alice.get("/recommendations/?year=2026&month=10")["recommendations"]
    bob_recommendations = bob.get("/recommendations/?year=2026&month=10")["recommendations"]

    food = next(r for r in alice_recommendations if r["category"] == "Food")
    assert food["percentage_change"] == 50.0
    assert food["type"] == "spending_increase"

    assert all(r["category"] != "Rent" for r in alice_recommendations)
    assert all(r["category"] != "Food" for r in bob_recommendations)


def test_recommendations_empty_for_user_without_transactions(populated, carol):
    assert carol.get("/recommendations/?year=2026&month=10")["recommendations"] == []


def test_ai_recommendations_use_only_own_data(populated, carol, monkeypatch):
    alice, bob = populated
    prompts = []

    def fake_ai_explanation(prompt):
        prompts.append(prompt)
        return "Explanation"

    monkeypatch.setattr("app.main.generate_ai_explanation", fake_ai_explanation)

    alice_result = alice.get("/recommendations/ai?year=2026&month=10")["ai_recommendations"]

    assert [r["category"] for r in alice_result if r["category"] == "Food"] == ["Food"]
    assert any("Food" in prompt and "50.0%" in prompt for prompt in prompts)
    assert not any("Rent" in prompt for prompt in prompts)

    # Bob and Carol trigger no explanation about Alice's spending
    prompts.clear()
    bob.get("/recommendations/ai?year=2026&month=10")
    carol.get("/recommendations/ai?year=2026&month=10")

    assert not any("Food" in prompt for prompt in prompts)


# Out-of-range input fails safely instead of causing server errors

@pytest.mark.parametrize("transaction_id", ["0", "-1", str(2**63), "9" * 30])
def test_delete_out_of_range_id_returns_404(alice, transaction_id):
    response = alice.request("delete", f"/transactions/{transaction_id}")

    assert response.status_code == 404
    assert response.json() == NOT_FOUND


@pytest.mark.parametrize("amount", ["1e309", "-1e309", "Infinity", "NaN"])
def test_non_finite_amount_rejected(alice, db_session, amount):
    response = alice.request(
        "post",
        "/transactions/",
        content=f'{{"amount": {amount}, "category": "Food", "date": "2026-10-08"}}',
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "amount"]
    assert db_session.query(Transaction).count() == 0
    assert alice.get("/spending/summary")["total_spending"] == 0


def test_huge_amount_rejected(alice, db_session):
    # Two of these would add up to infinity and break the summary
    response = alice.request("post", "/transactions/", json={**VALID_TRANSACTION, "amount": 1e308})

    assert response.status_code == 422
    assert db_session.query(Transaction).count() == 0


def test_maximum_amounts_still_summarise(alice):
    for _ in range(3):
        alice.add({**VALID_TRANSACTION, "amount": 1_000_000_000})

    assert alice.get("/spending/summary")["total_spending"] == 3_000_000_000
    assert alice.request("get", "/spending/compare?year=2026&month=10").status_code == 200


def test_validation_error_echoing_infinity_is_json_safe(alice):
    # Missing field: the whole body (with infinity in it) is echoed back
    response = alice.request(
        "post",
        "/transactions/",
        content='{"amount": Infinity, "date": "2026-10-08"}',
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
    assert {"body", "amount"} <= {part for e in response.json()["detail"] for part in e["loc"]}


@pytest.mark.parametrize("path", ["/spending/compare", "/recommendations/", "/recommendations/ai"])
@pytest.mark.parametrize("year", ["10000", "9" * 30])
def test_out_of_range_year_rejected(alice, path, year):
    response = alice.request("get", f"{path}?year={year}&month=5")

    assert response.status_code == 422


def test_largest_valid_year_accepted(alice):
    assert alice.request("get", "/spending/compare?year=9999&month=12").status_code == 200


# Internal calls cannot skip the user

@pytest.mark.parametrize("function", [compare_spending, get_recommendations])
def test_internal_calls_must_pass_user(function, db_session):
    with pytest.raises(TypeError):
        function(2026, 10, db=db_session)
