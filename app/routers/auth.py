"""Authentication routes: /auth/signup, /auth/login, /auth/me (same design as the Expense Tracker API)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if user is None or not verify_password(form.password, user.password_hash):
        # Same message for unknown email and wrong password, so emails can't be enumerated.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    return Token(access_token=create_access_token(subject=str(user.id)))


@router.get("/me", response_model=UserOut)
def who_am_i(current_user: User = Depends(get_current_user)):
    return current_user
