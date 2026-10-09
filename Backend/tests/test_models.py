from datetime import date

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Transaction, User


@pytest.fixture
def db():
    # Separate in-memory database for each test
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    Base.metadata.create_all(bind=test_engine)
    session = sessionmaker(bind=test_engine)()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def make_user(email="alice@example.com", name="Alice"):
    return User(email=email, name=name, hashed_password="not-a-real-hash")


def make_transaction(**overrides):
    values = {"amount": 25.0, "category": "Food", "date": date(2026, 10, 8)}
    values.update(overrides)
    return Transaction(**values)


def test_foreign_keys_are_enforced(db):
    assert db.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_user_created_at_is_set_automatically(db):
    user = make_user()
    db.add(user)
    db.commit()

    assert user.id is not None
    assert user.created_at is not None


def test_transaction_linked_to_user(db):
    user = make_user()
    transaction = make_transaction(owner=user)
    db.add(transaction)
    db.commit()

    assert transaction.user_id == user.id
    assert transaction.owner is user
    assert user.transactions == [transaction]


def test_users_only_see_their_own_transactions(db):
    alice = make_user()
    bob = make_user(email="bob@example.com", name="Bob")
    alice_transaction = make_transaction(owner=alice)
    bob_transaction = make_transaction(owner=bob, category="Transport")
    db.add_all([alice_transaction, bob_transaction])
    db.commit()

    assert alice.transactions == [alice_transaction]
    assert bob.transactions == [bob_transaction]


def test_duplicate_email_rejected(db):
    db.add(make_user())
    db.commit()

    db.add(make_user(name="Another Alice"))

    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("field", ["email", "name", "hashed_password"])
def test_required_user_fields(db, field):
    user = make_user()
    setattr(user, field, None)
    db.add(user)

    with pytest.raises(IntegrityError):
        db.commit()


@pytest.mark.parametrize("field", ["email", "name"])
def test_blank_user_fields_rejected(db, field):
    user = make_user()
    setattr(user, field, "   ")
    db.add(user)

    with pytest.raises(IntegrityError):
        db.commit()


def test_transaction_with_unknown_user_rejected(db):
    db.add(make_transaction(user_id=999))

    with pytest.raises(IntegrityError):
        db.commit()


def test_unowned_legacy_transaction_allowed(db):
    # Rows created before authentication have no owner until resolved
    transaction = make_transaction()
    db.add(transaction)
    db.commit()

    assert transaction.user_id is None
    assert transaction.owner is None


def test_deleting_user_with_transactions_is_blocked(db):
    user = make_user()
    transaction = make_transaction(owner=user)
    db.add(transaction)
    db.commit()
    transaction_id = transaction.id

    db.delete(user)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()

    assert db.get(Transaction, transaction_id).user_id == user.id


def test_existing_transaction_columns_unchanged(db):
    columns = {
        column["name"]: column
        for column in inspect(db.get_bind()).get_columns("transactions")
    }

    assert set(columns) == {
        "id", "amount", "category", "description", "date", "user_id"
    }
    assert columns["amount"]["nullable"] is False
    assert columns["category"]["nullable"] is False
    assert columns["description"]["nullable"] is True
    assert columns["date"]["nullable"] is False
    assert columns["user_id"]["nullable"] is True


def test_transaction_date_default_unchanged(db):
    transaction = Transaction(amount=10.0, category="Food")
    db.add(transaction)
    db.commit()

    assert transaction.date == date.today()
