from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.core.config import get_access_token_expire_minutes
from app.core.security import (
    create_access_token,
    hash_password,
    simulate_password_check,
    verify_and_update_password,
    verify_password
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.account_settings import AccountSettings, get_account_settings
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse, ProfileUpdate, PasswordChange

router = APIRouter(prefix="/auth", tags=["Authentication"])

EMAIL_TAKEN_MESSAGE = "An account with this email already exists."
LOGIN_FAILED_MESSAGE = "Incorrect email or password."


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_email(db, user_in.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=EMAIL_TAKEN_MESSAGE
        )

    user = User(
        name=user_in.name,
        email=user_in.email,
        hashed_password=hash_password(user_in.password)
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        # Another request registered the same email in the meantime;
        # the database unique constraint is the final safeguard.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=EMAIL_TAKEN_MESSAGE
        ) from None

    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = get_user_by_email(db, credentials.email)

    if user is None:
        simulate_password_check(credentials.password)
        valid, updated_hash = False, None
    else:
        valid, updated_hash = verify_and_update_password(
            credentials.password,
            user.hashed_password
        )

    # Same response whether the email or the password was wrong
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=LOGIN_FAILED_MESSAGE,
            headers={"WWW-Authenticate": "Bearer"}
        )

    if updated_hash is not None:
        user.hashed_password = updated_hash
        db.commit()

    expires_delta = timedelta(minutes=get_access_token_expire_minutes())

    settings = get_account_settings(db, user.id)
    return Token(
        access_token=create_access_token(user.id, expires_delta, token_version=settings.token_version if settings else 0),
        expires_in=int(expires_delta.total_seconds())
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = UserResponse.model_validate(current_user)
    settings = get_account_settings(db, current_user.id)
    result.phone = settings.phone if settings else None
    return result


@router.patch("/me", response_model=UserResponse)
def update_profile(body: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not inspect(db.get_bind()).has_table("account_settings"):
        raise HTTPException(503, "Account settings need a database update. Run migrate_account_settings.py on the backend.")
    if body.email != current_user.email:
        if not body.current_password or not verify_password(body.current_password, current_user.hashed_password):
            raise HTTPException(403, "Enter your correct current password to change your email.")
        other = get_user_by_email(db, body.email)
        if other is not None and other.id != current_user.id:
            raise HTTPException(409, EMAIL_TAKEN_MESSAGE)
    settings = db.get(AccountSettings, current_user.id)
    if settings is None:
        settings = AccountSettings(user_id=current_user.id)
        db.add(settings)
    current_user.name = body.name
    current_user.email = body.email
    settings.phone = body.phone
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, EMAIL_TAKEN_MESSAGE) from None
    db.refresh(current_user)
    return read_current_user(current_user, db)


@router.post("/password", status_code=204)
def change_password(body: PasswordChange, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not inspect(db.get_bind()).has_table("account_settings"):
        raise HTTPException(503, "Account settings need a database update. Run migrate_account_settings.py on the backend.")
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(403, "Your current password is incorrect.")
    if body.current_password == body.new_password:
        raise HTTPException(422, "Choose a different new password.")
    # Increment and replace together. Old JWTs no longer match this account's version.
    settings = db.get(AccountSettings, current_user.id)
    if settings is None:
        settings = AccountSettings(user_id=current_user.id, token_version=0)
        db.add(settings)
        db.flush()
    current_user.hashed_password = hash_password(body.new_password)
    db.query(AccountSettings).filter_by(user_id=current_user.id).update({AccountSettings.token_version: AccountSettings.token_version + 1})
    db.commit()
