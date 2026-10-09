from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_access_token_expire_minutes
from app.core.security import (
    create_access_token,
    hash_password,
    simulate_password_check,
    verify_and_update_password
)
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

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

    return Token(
        access_token=create_access_token(user.id, expires_delta),
        expires_in=int(expires_delta.total_seconds())
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user
