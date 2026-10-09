import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import JWT_ALGORITHM, ConfigurationError
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_and_update_password,
    verify_password
)

PASSWORD = "correct-horse-1"


# Password hashing

def test_hash_is_argon2id_and_not_plaintext():
    hashed = hash_password(PASSWORD)

    assert hashed.startswith("$argon2id$")
    assert PASSWORD not in hashed


def test_same_password_gets_different_hashes():
    # A random salt is used each time
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_verify_correct_password():
    assert verify_password(PASSWORD, hash_password(PASSWORD)) is True


def test_verify_wrong_password():
    hashed = hash_password(PASSWORD)

    assert verify_password("wrong-password", hashed) is False
    assert verify_password(PASSWORD.upper(), hashed) is False
    assert verify_password(PASSWORD + " ", hashed) is False


@pytest.mark.parametrize("bad_hash", [
    "",
    "plaintext-password",
    "$argon2id$garbage",
    "$argon2id$v=19$m=65536,t=3,p=4$abc$def"
])
def test_verify_malformed_hash_returns_false(bad_hash):
    assert verify_password(PASSWORD, bad_hash) is False


def test_current_hash_does_not_need_update():
    valid, updated = verify_and_update_password(PASSWORD, hash_password(PASSWORD))

    assert valid is True
    assert updated is None


# Access tokens

def encode(payload, secret, algorithm=JWT_ALGORITHM):
    return jwt.encode(payload, secret, algorithm=algorithm)


def valid_claims(**overrides):
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "1",
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=5)
    }
    claims.update(overrides)
    return claims


def test_token_round_trip(jwt_secret):
    assert decode_access_token(create_access_token(42)) == 42


def test_token_claims(jwt_secret):
    before = datetime.now(timezone.utc).replace(microsecond=0)
    token = create_access_token(42)

    claims = jwt.decode(token, jwt_secret, algorithms=[JWT_ALGORITHM])

    assert claims["sub"] == "42"
    assert claims["type"] == "access"
    assert set(claims) == {"sub", "type", "iat", "exp"}
    assert claims["exp"] - claims["iat"] == 30 * 60
    assert claims["iat"] >= before.timestamp()
    assert jwt.get_unverified_header(token)["alg"] == "HS256"


def test_token_lifetime_follows_configuration(jwt_secret, monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")

    claims = jwt.decode(create_access_token(1), jwt_secret, algorithms=[JWT_ALGORITHM])

    assert claims["exp"] - claims["iat"] == 5 * 60


def test_token_contains_no_personal_data(jwt_secret):
    token = create_access_token(7)
    payload = token.split(".")[1]
    decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()

    assert "@" not in decoded
    assert jwt_secret not in token


def test_expired_token_rejected(jwt_secret):
    token = create_access_token(1, expires_delta=timedelta(seconds=-1))

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_token_signed_with_other_secret_rejected(jwt_secret):
    token = encode(valid_claims(), "x" * 64)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_tampered_signature_rejected(jwt_secret):
    token = create_access_token(1)
    header, payload, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{payload}.{flipped}")


def test_tampered_payload_rejected(jwt_secret):
    # Change the user ID but keep the original signature
    header, _, signature = create_access_token(1).split(".")
    forged = base64.urlsafe_b64encode(
        json.dumps(valid_claims(sub="2", iat=1, exp=9999999999)).encode()
    ).rstrip(b"=").decode()

    with pytest.raises(InvalidTokenError):
        decode_access_token(f"{header}.{forged}.{signature}")


def test_unsigned_none_algorithm_rejected(jwt_secret):
    token = jwt.encode(valid_claims(), None, algorithm="none")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_other_algorithm_rejected(jwt_secret):
    # Correct secret, but only HS256 is accepted
    token = encode(valid_claims(), jwt_secret, algorithm="HS512")

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("missing", ["sub", "exp", "iat", "type"])
def test_missing_claim_rejected(jwt_secret, missing):
    claims = valid_claims()
    del claims[missing]

    with pytest.raises(InvalidTokenError):
        decode_access_token(encode(claims, jwt_secret))


@pytest.mark.parametrize("subject", ["abc", "", "0", "-1", "1.5", " 1", "²", str(2**63), "9" * 30])
def test_invalid_subject_rejected(jwt_secret, subject):
    with pytest.raises(InvalidTokenError):
        decode_access_token(encode(valid_claims(sub=subject), jwt_secret))


def test_wrong_token_type_rejected(jwt_secret):
    with pytest.raises(InvalidTokenError):
        decode_access_token(encode(valid_claims(type="refresh"), jwt_secret))


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b.c", "a.b"])
def test_malformed_token_rejected(jwt_secret, token):
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


def test_missing_secret_fails_safely(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ConfigurationError):
        create_access_token(1)

    with pytest.raises(ConfigurationError):
        decode_access_token("anything")
