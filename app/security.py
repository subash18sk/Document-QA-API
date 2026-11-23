"""
All security primitives live here: password hashing + JWT tokens.

WHY one file:
Cryptography is the easiest thing to get subtly wrong. Concentrating it in
one small, reviewed place means the rest of the app just calls these helpers
and never touches raw crypto.

TWO JOBS:
1. Passwords  -> hash_password / verify_password  (using bcrypt)
2. Identity   -> create_access_token / decode_token (using JWT)
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.config import settings

# bcrypt is a deliberately SLOW hashing algorithm. Slowness is a feature:
# it makes brute-forcing stolen hashes impractical. We use the `bcrypt`
# library directly (simpler and current) rather than a wrapper.
#
# bcrypt has a hard 72-byte input limit, so we encode to bytes and trim to 72
# before hashing. We do the identical trim on verify so the two always match.
def _to_bcrypt_bytes(plain: str) -> bytes:
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    """Turn a real password into a one-way hash (stored as a string)."""
    hashed = bcrypt.hashpw(_to_bcrypt_bytes(plain), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a login attempt against the stored hash. One-way: it re-hashes
    the attempt with the stored salt and compares."""
    return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("utf-8"))


def create_access_token(subject: str) -> str:
    """
    Build a JWT. A JWT is a signed note that says "this is user X, valid
    until time T". Because it's signed with our secret, the server can trust
    it later WITHOUT a database lookup (that's 'stateless' auth).
    `subject` is the user id we put in the standard 'sub' claim.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> str | None:
    """
    Verify a JWT's signature + expiry and return the user id inside it.
    Returns None if the token is forged, tampered with, or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except InvalidTokenError:
        return None
