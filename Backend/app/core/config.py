import os

from dotenv import load_dotenv

load_dotenv()

# Fixed in code rather than read from the environment, so a misconfigured
# server can never be switched to a weaker algorithm (or to "none").
JWT_ALGORITHM = "HS256"

# HS256 secrets should be at least 256 bits (32 bytes) long.
MIN_JWT_SECRET_LENGTH = 32

DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
MAX_ACCESS_TOKEN_EXPIRE_MINUTES = 1440


class ConfigurationError(RuntimeError):
    pass


def get_jwt_secret_key() -> str:
    # Read on every call (not at import time) so the API still starts
    # without a secret, and only authentication fails.
    secret = os.getenv("JWT_SECRET_KEY", "").strip()

    if not secret:
        raise ConfigurationError(
            "JWT_SECRET_KEY is not set. Copy Backend/.env.example to "
            "Backend/.env and generate a secret as described there."
        )

    if len(secret) < MIN_JWT_SECRET_LENGTH:
        raise ConfigurationError(
            f"JWT_SECRET_KEY must be at least {MIN_JWT_SECRET_LENGTH} characters."
        )

    return secret


def get_access_token_expire_minutes() -> int:
    value = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "").strip()

    if not value:
        return DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES

    try:
        minutes = int(value)
    except ValueError:
        raise ConfigurationError(
            "ACCESS_TOKEN_EXPIRE_MINUTES must be a whole number."
        ) from None

    if minutes < 1 or minutes > MAX_ACCESS_TOKEN_EXPIRE_MINUTES:
        raise ConfigurationError(
            "ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and "
            f"{MAX_ACCESS_TOKEN_EXPIRE_MINUTES}."
        )

    return minutes
