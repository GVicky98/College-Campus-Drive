"""FastAPI dependencies: the signed-in user and permission / role checks.

Authorisation is decided from the database on every request (active flag, role, permission matrix);
the claims inside the JWT are never trusted for this.
"""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .database import get_db
from .enums import RoleName, UserStatus
from .errors import Forbidden, Unauthenticated
from .models import User
from .security import decode_token
from .services import audit

Db = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: Db) -> User:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthenticated("Please sign in.")
    payload = decode_token(header[7:].strip(), "access")
    if not payload:
        raise Unauthenticated("Your session has expired. Please sign in again.")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != UserStatus.ACTIVE:
        raise Unauthenticated("Your session has expired. Please sign in again.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def ensure_permission(db: Session, user: User, *perms: str, mode: str = "any") -> None:
    """Raise 403 (and audit it) unless the user holds any/all of `perms`."""
    held = [user.can(p) for p in perms]
    if (any(held) if mode == "any" else all(held)):
        return
    audit.deny(db, user, "access.denied", ", ".join(perms), "Missing permission")
    raise Forbidden()


def ensure_role(db: Session, user: User, *roles: str) -> None:
    if user.role_name in roles:
        return
    audit.deny(db, user, "access.denied", f"role:{'/'.join(roles)}", "Role not allowed")
    raise Forbidden()


def require_perm(*perms: str, mode: str = "any"):
    """Dependency: the signed-in user must hold any (default) or all of the permissions."""
    def dependency(user: CurrentUser, db: Db) -> User:
        ensure_permission(db, user, *perms, mode=mode)
        return user
    return Depends(dependency)


def require_role(*roles: str):
    def dependency(user: CurrentUser, db: Db) -> User:
        ensure_role(db, user, *roles)
        return user
    return Depends(dependency)


def is_staff(user: User) -> bool:
    return user.role_name in (RoleName.FACULTY, RoleName.ADMIN)


StudentUser = Annotated[User, require_role(RoleName.STUDENT)]
AdminUser = Annotated[User, require_role(RoleName.ADMIN)]
