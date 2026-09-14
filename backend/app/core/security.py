"""
Authentication and role-based access control primitives.

Covers FR-12 (user access management) and NFR-06 (RBAC + encrypted storage).
Password hashing uses bcrypt; tokens are short-lived JWTs. Role checks are
expressed as FastAPI dependencies so endpoints declare their requirement
declaratively (see api/deps.py for how these compose with DB session
injection).
"""
from datetime import datetime, timedelta, timezone
from enum import Enum

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Role(str, Enum):
    """Roles referenced by FR-12 / NFR-06 role-based access control."""

    ADMIN = "admin"              # full access incl. model retraining, user mgmt
    TRAFFIC_OFFICER = "officer"  # dashboard + alerts, read-only elsewhere
    AUDITOR = "auditor"          # read-only access to logs/analytics


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
