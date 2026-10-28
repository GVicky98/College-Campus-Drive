"""Proposed actions: awaiting_confirmation -> executing -> confirmed | failed, or cancelled / expired.

Confirming claims the action atomically, re-checks the user's role and permissions, then runs the normal service
function, which re-validates every business rule against current data. Success is reported only after it commits.
"""
from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import utcnow
from ...enums import ActionState, AuditResult, RoleName
from ...errors import ApiError, Conflict, NotFound
from ...models import AssistantAction, User
from .. import audit
from .framework import STAFF

EXPIRED_MESSAGE = "This proposal expired. Ask the assistant to prepare it again."


def _apply(db, user, p):
    from ..applications_service import apply
    apply(db, user, p["jobId"])
    return "Application submitted."


def _reminder(db, user, p):
    from ...routers.student import ReminderIn
    from ..content_service import save_reminder
    save_reminder(db, user, ReminderIn(title=p["title"], at=p["at"], job_id=p.get("jobId")))
    return "Reminder created."


def _stage(db, user, p):
    from ..review_service import update_stage
    r = update_stage(db, user, p["ids"], p["status"], p.get("note"), None)
    if not r["updated"]:
        raise Conflict("No applicant could be moved: " + "; ".join(f["reason"] for f in r["failed"])[:300])
    msg = f"{len(r['updated'])} applicant(s) moved and notified."
    if r["failed"]:
        msg += " Not moved: " + "; ".join(f"#{f['id']} {f['reason']}" for f in r["failed"])
    return msg


def _user_create(db, user, p):
    from ...routers.admin import UserIn
    from ..users_service import create_user
    u = create_user(db, user, UserIn.model_validate(p["user"]))
    return f"Invited {u.name}. They set a password from a one-time link."


def _user_update(db, user, p):
    from ...routers.admin import UserIn
    from ..users_service import update_user
    u = update_user(db, user, p["userId"], UserIn.model_validate(p["user"]))
    return f"Updated {u.name}."


def _user_status(db, user, p):
    from ..users_service import set_status
    u = set_status(db, user, p["userId"], p["status"])
    return f"{u.name} is now {u.status}."


def _import(db, user, p):
    from ...routers.admin import ImportRow
    from ..users_service import import_students
    r = import_students(db, user, [ImportRow.model_validate(x) for x in p["rows"]])
    if not r["imported"]:
        raise Conflict("No rows could be imported: " + "; ".join(f"row {e['row']} {e['field']}: {e['message']}" for e in r["errors"])[:300])
    msg = f"Imported {r['imported']} of {r['total']} student(s)."
    if r["errors"]:
        msg += " Skipped: " + "; ".join(f"row {e['row']} {e['field']} — {e['message']}" for e in r["errors"][:5])
    return msg


def _company_save(db, user, p):
    from ...routers.staff import CompanyIn
    from ..companies_service import save
    c = save(db, user, CompanyIn.model_validate(p["company"]), p.get("companyId"))
    return f"Saved {c.name}."


def _company_archive(db, user, p):
    from ..companies_service import archive
    c = archive(db, user, p["companyId"], p["archived"])
    return f"{c.name} {'archived' if p['archived'] else 'restored'}."


def _policy_save(db, user, p):
    from ...routers.admin import PolicyIn
    from ..admin_service import save_policy
    pol = save_policy(db, user, PolicyIn.model_validate(p["policy"]), p.get("policyId"))
    return f"Policy “{pol.name}” saved."


def _policy_delete(db, user, p):
    from ..admin_service import delete_policy
    delete_policy(db, user, p["policyId"], p["reason"])
    return f"Policy “{p['name']}” deleted."


def _verify(db, user, p):
    from ..students_service import verify_cgpa
    r = verify_cgpa(db, user, p["studentId"], p.get("cgpa"))
    return f"CGPA of {r['name']} verified; the student was notified."


STUDENT = (RoleName.STUDENT,)
# kind -> (roles, permissions (all required), executor)
SPECS = {
    "apply": (STUDENT, (), _apply),
    "create_reminder": (STUDENT, (), _reminder),
    "update_stage": (STAFF, ("applications.review",), _stage),
    "user_create": (STAFF, ("users.manage",), _user_create),
    "user_update": (STAFF, ("users.manage",), _user_update),
    "user_status": (STAFF, ("users.manage",), _user_status),
    "student_import": (STAFF, ("users.manage",), _import),
    "company_save": (STAFF, ("companies.manage",), _company_save),
    "company_archive": (STAFF, ("companies.manage",), _company_archive),
    "policy_save": (STAFF, ("policies.manage",), _policy_save),
    "policy_delete": (STAFF, ("policies.manage",), _policy_delete),
    "verify_cgpa": (STAFF, ("students.edit",), _verify),
}


def create(db: Session, user: User, conversation_id: int, message_id: int, proposal: dict) -> AssistantAction:
    a = AssistantAction(user_id=user.id, conversation_id=conversation_id, message_id=message_id, kind=proposal["kind"],
                        title=proposal["title"][:200], description=proposal["description"][:500], details=proposal["details"],
                        payload={**proposal["payload"], "_destructive": proposal["destructive"]},
                        expires_at=utcnow() + timedelta(minutes=get_settings().assistant_action_ttl_minutes))
    db.add(a)
    return a


def effective_state(a: AssistantAction) -> str:
    if a.state == ActionState.AWAITING and a.expires_at < utcnow():
        return ActionState.EXPIRED
    if a.state == ActionState.EXECUTING:
        return ActionState.AWAITING
    return a.state


def action_dict(a: AssistantAction) -> dict:
    state = effective_state(a)
    out = {"id": str(a.id), "kind": a.kind, "title": a.title, "description": a.description, "details": a.details or [], "state": state}
    if (a.payload or {}).get("_destructive"):
        out["destructive"] = True
    message = a.result_message or (EXPIRED_MESSAGE if state == ActionState.EXPIRED else None)
    if message:
        out["resultMessage"] = message
    return out


def _owned(db: Session, user: User, action_id: int) -> AssistantAction:
    a = db.get(AssistantAction, action_id)
    if not a or a.user_id != user.id:
        if a:
            audit.deny(db, user, "assistant.action", f"Action {action_id}", "Not the owner")
        raise NotFound("Action not found.")
    return a


def _claim(db: Session, a: AssistantAction, to_state: str) -> None:
    if a.state == ActionState.AWAITING and a.expires_at < utcnow():
        a.state, a.result_message, a.resolved_at = ActionState.EXPIRED, EXPIRED_MESSAGE, utcnow()
        db.commit()
        raise Conflict(EXPIRED_MESSAGE)
    done = db.execute(update(AssistantAction).where(AssistantAction.id == a.id, AssistantAction.state == ActionState.AWAITING)
                      .values(state=to_state).execution_options(synchronize_session=False)).rowcount
    db.commit()
    if not done:
        raise Conflict("This action was already handled.")
    db.refresh(a)


def _finish(db: Session, user: User, a: AssistantAction, state: str, message: str) -> None:
    a.state, a.result_message, a.resolved_at = state, message[:500], utcnow()
    audit.record(db, f"assistant.action.{state}", f"Action {a.id} · {a.kind} · {a.title}"[:255], actor=user,
                 result=AuditResult.FAILED if state == ActionState.FAILED else AuditResult.SUCCESS, reason=message)
    db.commit()


def confirm(db: Session, user: User, action_id: int) -> AssistantAction:
    a = _owned(db, user, action_id)
    _claim(db, a, ActionState.EXECUTING)
    roles, perms, run = SPECS[a.kind]
    if user.role_name not in roles or not all(user.can(p) for p in perms):
        audit.record(db, "access.denied", f"Action {a.id} · {a.kind}", actor=user, result=AuditResult.DENIED, reason="Permission lost")
        _finish(db, user, a, ActionState.FAILED, "You no longer have permission to do this. Nothing was changed.")
        return a
    payload = {k: v for k, v in (a.payload or {}).items() if not k.startswith("_")}
    try:
        message = run(db, user, payload)
    except ApiError as e:
        db.rollback()
        db.refresh(a)
        _finish(db, user, a, ActionState.FAILED, f"The server did not allow this: {e.message}")
        return a
    except Exception:
        db.rollback()
        db.refresh(a)
        _finish(db, user, a, ActionState.FAILED, "Something went wrong and nothing was changed. Please try again.")
        return a
    db.refresh(a)
    _finish(db, user, a, ActionState.CONFIRMED, message)
    return a


def reject(db: Session, user: User, action_id: int) -> AssistantAction:
    a = _owned(db, user, action_id)
    _claim(db, a, ActionState.CANCELLED)
    _finish(db, user, a, ActionState.CANCELLED, "Cancelled. Nothing was changed.")
    return a
