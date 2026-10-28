"""Sign-in, session refresh, password change and password reset."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import utcnow
from ..enums import AuditResult, UserStatus
from ..errors import Forbidden, Unauthenticated, ValidationFailed
from ..models import PasswordResetToken, RevokedToken, User
from ..security import (
    DUMMY_HASH, check_password_policy, create_access_token, create_refresh_token, hash_password, hash_token, is_locked,
    new_one_time_token, verify_password,
)
from ..serializers import user_dict
from . import audit

log = logging.getLogger("campus")

BAD_LOGIN = "The e-mail / user ID or password is incorrect, or the account is temporarily locked."
FORGOT_MESSAGE = "If an account exists for that e-mail, a password reset link has been sent."


def session_payload(user: User) -> dict:
    token, expires_in = create_access_token(user.id, user.role_name)
    return {"user": user_dict(user), "permissions": user.permission_keys, "accessToken": token, "expiresIn": expires_in}


def find_by_identifier(db: Session, identifier: str) -> User | None:
    ident = identifier.strip().lower()
    return db.scalar(select(User).where((func.lower(User.email) == ident) | (func.lower(User.user_code) == ident)))


def login(db: Session, identifier: str, password: str) -> User:
    s = get_settings()
    user = find_by_identifier(db, identifier)
    password_ok = verify_password(password, user.password_hash if user else DUMMY_HASH)

    if not user or is_locked(user.locked_until) or not password_ok:
        if user and not is_locked(user.locked_until):
            user.failed_login_count += 1
            if user.failed_login_count >= s.max_failed_logins:
                user.locked_until = utcnow() + timedelta(minutes=s.lockout_minutes)
                user.failed_login_count = 0
                audit.record(db, "auth.lockout", f"User {user.id}", actor=user, result=AuditResult.DENIED,
                             reason=f"{s.max_failed_logins} failed sign-ins")
        audit.record(db, "auth.login", "", actor=None, actor_label=identifier[:60], result=AuditResult.DENIED,
                     reason="Bad credentials or locked")
        db.commit()
        raise Unauthenticated(BAD_LOGIN)

    if user.status != UserStatus.ACTIVE:
        audit.deny(db, user, "auth.login", f"User {user.id}", "Account not active")
        raise Forbidden("This account is not active. Contact the placement cell.")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    audit.record(db, "auth.login", f"User {user.id}", actor=user)
    db.commit()
    return user


def refresh(db: Session, payload: dict) -> User:
    """Validate a decoded refresh token, revoke it (rotation) and return its user."""
    jti = payload.get("jti")
    if not jti or db.scalar(select(RevokedToken).where(RevokedToken.jti == jti)):
        raise Unauthenticated("Your session has ended. Please sign in again.")
    user = db.get(User, int(payload["sub"]))
    if not user or user.status != UserStatus.ACTIVE:
        raise Unauthenticated("Your session has ended. Please sign in again.")
    # Tokens issued before the last password change / deactivation are dead (iat has whole-second precision).
    issued = datetime.fromtimestamp(payload.get("iat", 0), tz=timezone.utc).replace(tzinfo=None)
    if user.password_changed_at and issued < user.password_changed_at.replace(microsecond=0):
        raise Unauthenticated("Your session has ended. Please sign in again.")
    revoke(db, payload)
    return user


def revoke(db: Session, payload: dict) -> None:
    jti = payload.get("jti")
    if not jti or db.scalar(select(RevokedToken).where(RevokedToken.jti == jti)):
        return
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc).replace(tzinfo=None)
    db.add(RevokedToken(jti=jti, user_id=int(payload["sub"]), expires_at=exp))


def new_refresh(user: User, remember: bool):
    return create_refresh_token(user.id, remember)


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        audit.deny(db, user, "auth.password_change", f"User {user.id}", "Wrong current password")
        raise Unauthenticated("Your current password is incorrect.")
    if current == new:
        raise ValidationFailed("Choose a password you have not used just now.", field="newPassword")
    check_password_policy(new, user.email, user.user_code)
    user.password_hash = hash_password(new)
    user.password_changed_at = utcnow()
    audit.record(db, "auth.password_change", f"User {user.id}", actor=user)
    db.commit()


def issue_reset_token(db: Session, user: User, minutes: int) -> str:
    raw, hashed = new_one_time_token()
    db.add(PasswordResetToken(user_id=user.id, token_hash=hashed, expires_at=utcnow() + timedelta(minutes=minutes)))
    return raw


def reset_link(raw: str) -> str:
    return f"{get_settings().frontend_url.rstrip('/')}/reset-password?token={raw}"


def forgot_password(db: Session, email: str) -> str:
    s = get_settings()
    user = db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))
    if user and user.status == UserStatus.ACTIVE:
        raw = issue_reset_token(db, user, s.password_reset_minutes)
        audit.record(db, "auth.password_reset_requested", f"User {user.id}", actor=user)
        db.commit()
        if not s.is_production:
            # E-mail delivery is not implemented: in development the link is printed to the server log.
            log.warning("Password reset link for %s: %s", user.email, reset_link(raw))
    return FORGOT_MESSAGE


def reset_password(db: Session, raw: str, password: str) -> None:
    row = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(raw)))
    if not row or row.used_at or row.expires_at < utcnow():
        raise ValidationFailed("This reset link is invalid or has expired. Request a new one.", field="token")
    user = db.get(User, row.user_id)
    check_password_policy(password, user.email, user.user_code)
    user.password_hash = hash_password(password)
    user.password_changed_at = utcnow()
    user.failed_login_count = 0
    user.locked_until = None
    row.used_at = utcnow()
    if user.status == UserStatus.INVITED:
        user.status = UserStatus.ACTIVE
        audit.record(db, "user.activate", f"User {user.id}", actor=user, reason="Accepted invitation")
    audit.record(db, "auth.password_reset", f"User {user.id}", actor=user)
    db.commit()
