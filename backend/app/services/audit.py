"""Append-only audit trail."""
from contextvars import ContextVar

from sqlalchemy.orm import Session

from ..enums import AuditResult
from ..models import AuditLog, User

# Set by middleware for every request, so services don't need the Request object.
current_ip: ContextVar[str | None] = ContextVar("current_ip", default=None)


def record(
    db: Session,
    action: str,
    resource: str = "",
    *,
    actor: User | None = None,
    result: AuditResult = AuditResult.SUCCESS,
    reason: str | None = None,
    actor_label: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        actor_name=(actor.name if actor else actor_label or "anonymous")[:120],
        actor_role=actor.role_name if actor else "system",
        action=action[:64],
        resource=(resource or "")[:255],
        result=result,
        reason=reason[:400] if reason else None,
        ip_address=current_ip.get(),
    )
    db.add(entry)
    return entry


def deny(db: Session, actor: User | None, action: str, resource: str = "", reason: str = "") -> None:
    """Record a refused attempt and commit at once, so it survives the error response's rollback."""
    record(db, action, resource, actor=actor, result=AuditResult.DENIED, reason=reason)
    db.commit()
