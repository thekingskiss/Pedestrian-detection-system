from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import Role, decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user = db.query(User).filter(User.email == payload["sub"]).first()
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*allowed: Role):
    """
    FR-12 / NFR-06: dependency factory for endpoint-level RBAC, e.g.:

        @router.post(..., dependencies=[Depends(require_roles(Role.ADMIN))])
    """

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in {r.value for r in allowed}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {[r.value for r in allowed]}",
            )
        return user

    return checker
