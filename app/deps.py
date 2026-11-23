"""
Reusable route dependencies — chiefly `get_current_user`.

WHY this file exists:
Every protected route needs the same question answered: "who is making this
request, and are they allowed?" Writing that check in each route would be
repetitive and easy to get wrong in one place. Instead we write it ONCE here
as a dependency, and each protected route adds `Depends(get_current_user)`.
That single line turns a public route into a private one.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token

# Tells FastAPI to look for a token in the "Authorization: Bearer <token>"
# header, and powers the "Authorize" button in the /docs page.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the Bearer token into the actual User, or reject the request."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_token(token)       # None if forged/expired
    if user_id is None:
        raise credentials_error

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:                    # token valid but user was deleted
        raise credentials_error

    return user
