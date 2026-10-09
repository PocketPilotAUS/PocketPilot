from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.database import get_db
from app.models.user import User

# auto_error=False lets get_current_user return the same 401 response for
# every failure (missing header, wrong scheme, bad token, unknown user).
bearer_scheme = HTTPBearer(auto_error=False)


def credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    if credentials is None:
        raise credentials_error()

    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise credentials_error() from None

    # A valid token for a user that no longer exists is still rejected
    user = db.get(User, user_id)

    if user is None:
        raise credentials_error()

    return user


# Declared with Annotated and no default value, so calling an endpoint
# function directly without passing the user raises a TypeError instead of
# silently passing FastAPI's Depends placeholder into a query.
CurrentUser = Annotated[User, Depends(get_current_user)]
