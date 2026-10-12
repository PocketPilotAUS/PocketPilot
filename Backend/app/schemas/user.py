import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NAME_MAX_LENGTH = 100
EMAIL_MAX_LENGTH = 254
PASSWORD_MIN_LENGTH = 8
# Argon2 accepts any length; the cap stops huge inputs being hashed
PASSWORD_MAX_LENGTH = 128

# Same rule as the mobile app: something@something.something, no spaces
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(value: str) -> str:
    # Emails are compared case-insensitively, so they are stored in lowercase
    return value.strip().lower()


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    email: str = Field(max_length=EMAIL_MAX_LENGTH)
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH
    )

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Name cannot be blank.")

        if not value.isprintable():
            raise ValueError("Name contains invalid characters.")

        return value

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        value = normalize_email(value)

        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Enter a valid email address.")

        return value


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # No format or minimum-length rules here: any wrong value simply fails
    # to log in, without revealing the registration rules.
    email: str = Field(min_length=1, max_length=EMAIL_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: str) -> str:
        return normalize_email(value)


class UserResponse(BaseModel):
    # Built from the User model; only these fields are ever returned
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str | None = None
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def mark_as_utc(cls, value: datetime) -> datetime:
        # SQLite drops timezone information; stored times are always UTC
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    email: str = Field(max_length=EMAIL_MAX_LENGTH)
    phone: str | None = Field(default=None, max_length=40)
    current_password: str | None = Field(default=None, min_length=1, max_length=PASSWORD_MAX_LENGTH)

    clean_name = field_validator("name")(UserCreate.clean_name.__func__)
    clean_email = field_validator("email")(UserCreate.clean_email.__func__)

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value):
        if value is None or not value.strip():
            return None
        if not re.fullmatch(r"\+?[0-9 ()-]+", value.strip()):
            raise ValueError("Use a phone number with digits and an optional country code.")
        value = re.sub(r"[ ()-]", "", value.strip())
        if not 7 <= len(value.lstrip("+")) <= 15:
            raise ValueError("Phone numbers must contain 7 to 15 digits.")
        return value


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
