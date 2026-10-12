from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import (
    JWT_ALGORITHM,
    get_access_token_expire_minutes,
    get_jwt_secret_key
)
from app.database import MAX_DATABASE_ID

ACCESS_TOKEN_TYPE = "access"

# Argon2id with the library's recommended cost settings
# (64 MiB memory, 3 iterations, 4 lanes)
password_hash = PasswordHash((Argon2Hasher(),))


class InvalidTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    valid, _ = verify_and_update_password(password, hashed_password)
    return valid


def verify_and_update_password(
    password: str,
    hashed_password: str
) -> tuple[bool, str | None]:
    # Returns a new hash when the stored one uses outdated cost settings,
    # so hashes can be upgraded transparently at the next login.
    try:
        return password_hash.verify_and_update(password, hashed_password)
    except UnknownHashError:
        return False, None


# Created once at start-up (not on first use), so even the first login
# attempt for an unknown email takes the same time as any other
_DUMMY_HASH = hash_password("pocketpilot-dummy-password")


def simulate_password_check(password: str) -> None:
    # Spend the same time as a real check when the account does not exist,
    # so response timing does not reveal which emails are registered.
    verify_password(password, _DUMMY_HASH)


def create_access_token(
    user_id: int,
    expires_delta: timedelta | None = None,
    token_version: int = 0
) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=get_access_token_expire_minutes())

    issued_at = datetime.now(timezone.utc)

    payload = {
        # PyJWT requires the subject to be a string
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "version": token_version,
        "iat": issued_at,
        "exp": issued_at + expires_delta
    }

    return jwt.encode(payload, get_jwt_secret_key(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, expected_version: int | None = None) -> int:
    # Read the secret first so a missing secret raises ConfigurationError
    # instead of being reported as an invalid token.
    secret = get_jwt_secret_key()

    try:
        payload = jwt.decode(
            token,
            secret,
            # Only the configured algorithm is accepted, which rejects
            # "none" and algorithm-switching attacks.
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type"]}
        )
    except jwt.PyJWTError as error:
        raise InvalidTokenError("Invalid or expired token") from error

    if payload["type"] != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Wrong token type")

    version = payload.get("version", 0)
    if type(version) is not int or version < 0 or (expected_version is not None and version != expected_version):
        raise InvalidTokenError("Session has been revoked")

    subject = payload["sub"]

    if not isinstance(subject, str) or not subject.isdigit() or not subject.isascii():
        raise InvalidTokenError("Invalid token subject")

    user_id = int(subject)

    if user_id < 1 or user_id > MAX_DATABASE_ID:
        raise InvalidTokenError("Invalid token subject")

    return user_id
