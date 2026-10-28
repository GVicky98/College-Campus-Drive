"""Administrator services: placement policies, academic configuration, audit log, dashboard, system settings."""
import json
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import AuditResult, JobStatus, OfferStatus, PolicyKind, PolicyScope, ProcessingStatus, RoleName, UserStatus
from ..errors import Conflict, NotFound, ValidationFailed
from ..models import (
    AcademicRecord, AcademicYear, Application, AuditLog, Company, Course, Department, Document, FacultyProfile, Job,
    Offer, PlacementPolicy, Role, Student, SystemSetting, User, job_departments,
)
from ..serializers import iso, policy_dict, sid
from . import audit
from .common import like, paginate

# ---------------------------------------------------------------- policies
PARAM_RULES = {
    PolicyKind.MAX_OFFERS: {"maxAcceptedOffers": (int, 1, 20)},
    PolicyKind.APPLICATION_LIMIT: {"maxActiveApplications": (int, 1, 100)},
    PolicyKind.ACCEPTED_OFFER: {"acceptanceWindowDays": (int, 1, 90)},
    PolicyKind.TIER_RESTRICTION: {"allowOnlyHigherTier": (bool, None, None)},
    PolicyKind.EXCEPTION_APPROVAL: {"requireReason": (bool, None, None), "requireApprover": (bool, None, None)},
}


def _check_params(kind: str, params: dict) -> dict:
    rules = PARAM_RULES[PolicyKind(kind)]
    out = {}
    for key, (typ, lo, hi) in rules.items():
        if key not in params:
            raise ValidationFailed(f"Missing parameter {key}.", field="params")
        v = params[key]
        if typ is bool:
            if not isinstance(v, bool):
                raise ValidationFailed(f"{key} must be true or false.", field="params")
        elif isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
            raise ValidationFailed(f"{key} must be a whole number from {lo} to {hi}.", field="params")
        out[key] = v
    return out


def _check_scope(db: Session, scope: str, value: str | None) -> str | None:
    if scope == PolicyScope.COLLEGE:
        return None
    if not value or not value.isdigit():
        raise ValidationFailed("Choose what this policy applies to.", field="scopeValue")
    if scope == PolicyScope.DEPARTMENT and not db.get(Department, int(value)):
        raise ValidationFailed("Unknown department.", field="scopeValue")
    if scope == PolicyScope.ACADEMIC_YEAR and not db.scalar(select(AcademicYear.id).where(AcademicYear.graduation_year == int(value))):
        raise ValidationFailed("That batch is not configured.", field="scopeValue")
    return value


def list_policies(db: Session) -> list[dict]:
    return [policy_dict(p) for p in db.scalars(select(PlacementPolicy).order_by(PlacementPolicy.kind, PlacementPolicy.id))]


def save_policy(db: Session, actor: User, body, policy_id: int | None = None) -> PlacementPolicy:
    p = db.get(PlacementPolicy, policy_id) if policy_id else PlacementPolicy()
    if policy_id and not p:
        raise NotFound("Policy not found.")
    if policy_id and body.kind != p.kind:
        raise Conflict("The kind of a policy cannot change. Create a new policy instead.")
    clash = db.scalar(select(PlacementPolicy.id).where(func.lower(PlacementPolicy.name) == body.name.lower(), PlacementPolicy.id != (policy_id or 0)))
    if clash:
        raise Conflict("A policy with this name already exists.")
    params = _check_params(body.kind, body.params)
    scope_value = _check_scope(db, body.scope, body.scope_value)
    before = policy_dict(p) if policy_id else None
    p.name, p.description, p.kind, p.scope, p.scope_value = body.name, body.description, body.kind, body.scope, scope_value
    p.params, p.enabled, p.updated_by, p.updated_at = params, body.enabled, actor.name, utcnow()
    db.add(p)
    db.flush()
    if before:
        after = policy_dict(p)
        changes = [f"{k}: {before.get(k)} -> {after.get(k)}" for k in ("name", "scope", "scopeValue", "params", "enabled") if before.get(k) != after.get(k)]
        if before.get("description") != after.get("description"):
            changes.append("description")
        if changes:
            audit.record(db, "policy.update", f"Policy {p.id} · {p.name}", actor=actor, reason="Changed " + "; ".join(changes))
    else:
        audit.record(db, "policy.create", f"Policy {p.id} · {p.name}", actor=actor, reason=f"{p.kind} {json.dumps(params)}")
    db.commit()
    return p


def delete_policy(db: Session, actor: User, policy_id: int, reason: str) -> None:
    p = db.get(PlacementPolicy, policy_id)
    if not p:
        raise NotFound("Policy not found.")
    audit.record(db, "policy.delete", f"Policy {p.id} · {p.name}", actor=actor, reason=f"{reason} ({p.kind} {json.dumps(p.params)})")
    db.delete(p)
    db.commit()


# ---------------------------------------------------------------- academic configuration
def academic(db: Session) -> dict:
    depts = db.scalars(select(Department).order_by(Department.code)).all()
    courses = db.scalars(select(Course).order_by(Course.code)).all()
    years = db.scalars(select(AcademicYear).order_by(AcademicYear.graduation_year)).all()
    count = lambda model, d: db.scalar(select(func.count(model.id)).where(model.department_id == d.id)) or 0  # noqa: E731
    return {
        "departments": [{"id": sid(d.id), "code": d.code, "name": d.name, "headName": d.head_name or "",
                         "students": count(Student, d), "courses": count(Course, d)} for d in depts],
        "courses": [{"id": sid(c.id), "code": c.code, "name": c.name, "degree": c.degree, "departmentId": sid(c.department_id),
                     "durationYears": c.duration_years} for c in courses],
        "academicYears": [{"id": sid(y.id), "label": y.label, "graduationYear": y.graduation_year, "active": y.active} for y in years],
    }


def save_department(db: Session, actor: User, body, dept_id: int | None = None) -> None:
    d = db.get(Department, dept_id) if dept_id else Department()
    if dept_id and not d:
        raise NotFound("Department not found.")
    if db.scalar(select(Department.id).where(func.lower(Department.code) == body.code.lower(), Department.id != (dept_id or 0))):
        raise Conflict("That department code is already used.")
    d.code, d.name, d.head_name = body.code.upper(), body.name, body.head_name or None
    db.add(d)
    db.flush()
    audit.record(db, "department.update" if dept_id else "department.create", f"Department {d.code}", actor=actor)
    db.commit()


def delete_department(db: Session, actor: User, dept_id: int) -> None:
    d = db.get(Department, dept_id)
    if not d:
        raise NotFound("Department not found.")
    uses = {
        "students": db.scalar(select(func.count(Student.id)).where(Student.department_id == d.id)),
        "programmes": db.scalar(select(func.count(Course.id)).where(Course.department_id == d.id)),
        "staff accounts": db.scalar(select(func.count(User.id)).where(User.department_id == d.id)),
        "faculty profiles": db.scalar(select(func.count(FacultyProfile.id)).where(FacultyProfile.department_id == d.id)),
        "jobs": db.scalar(select(func.count()).select_from(job_departments).where(job_departments.c.department_id == d.id)),
        "policies": db.scalar(select(func.count(PlacementPolicy.id)).where(PlacementPolicy.scope == PolicyScope.DEPARTMENT,
                                                                           PlacementPolicy.scope_value == str(d.id))),
    }
    in_use = [f"{n} {k}" for k, n in uses.items() if n]
    if in_use:
        raise Conflict(f"{d.code} is still used by " + ", ".join(in_use) + ".")
    audit.record(db, "department.delete", f"Department {d.code}", actor=actor)
    db.delete(d)
    db.commit()


def save_course(db: Session, actor: User, body, course_id: int | None = None) -> None:
    c = db.get(Course, course_id) if course_id else Course()
    if course_id and not c:
        raise NotFound("Course not found.")
    if not db.get(Department, body.department_id):
        raise ValidationFailed("Unknown department.", field="departmentId")
    if db.scalar(select(Course.id).where(func.lower(Course.code) == body.code.lower(), Course.id != (course_id or 0))):
        raise Conflict("That course code is already used.")
    c.code, c.name, c.degree, c.department_id, c.duration_years = body.code.upper(), body.name, body.degree, body.department_id, body.duration_years
    db.add(c)
    db.flush()
    audit.record(db, "course.update" if course_id else "course.create", f"Course {c.code}", actor=actor)
    db.commit()


def delete_course(db: Session, actor: User, course_id: int) -> None:
    c = db.get(Course, course_id)
    if not c:
        raise NotFound("Course not found.")
    audit.record(db, "course.delete", f"Course {c.code}", actor=actor)
    db.delete(c)
    db.commit()


def save_year(db: Session, actor: User, body, year_id: int | None = None) -> None:
    a, b = body.label.split("-")
    if int(b) != (int(a) + 1) % 100:
        raise ValidationFailed("Use consecutive years, e.g. 2026-27.", field="label")
    y = db.get(AcademicYear, year_id) if year_id else AcademicYear(active=False)
    if year_id and not y:
        raise NotFound("Academic year not found.")
    if db.scalar(select(AcademicYear.id).where(AcademicYear.label == body.label, AcademicYear.id != (year_id or 0))):
        raise Conflict("That academic year already exists.")
    if db.scalar(select(AcademicYear.id).where(AcademicYear.graduation_year == body.graduation_year, AcademicYear.id != (year_id or 0))):
        raise Conflict("Another academic year already has that graduation batch.")
    if y.active and not body.active:
        raise Conflict("Mark another year as current instead.")
    y.label, y.graduation_year = body.label, body.graduation_year
    db.add(y)
    db.flush()
    if body.active and not y.active:
        for other in db.scalars(select(AcademicYear).where(AcademicYear.id != y.id)):
            other.active = False
        y.active = True
    audit.record(db, "academic_year.update" if year_id else "academic_year.create", f"Academic year {y.label}", actor=actor,
                 reason="Set as active" if body.active else None)
    db.commit()


# ---------------------------------------------------------------- audit log
def audit_logs(db: Session, actor_q, action, resource, result, date_from, date_to, page, page_size):
    q = select(AuditLog)
    if actor_q:
        q = q.where(AuditLog.actor_name.ilike(like(actor_q)))
    if action:
        q = q.where(or_(AuditLog.action == action, AuditLog.action.like(action.replace("%", "") + ".%")))
    if resource:
        q = q.where(AuditLog.resource.ilike(like(resource)))
    if result:
        q = q.where(AuditLog.result == result)
    if date_from and date_to and date_to < date_from:
        raise ValidationFailed("'To' is before 'from'.", field="to")
    if date_from:
        q = q.where(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(AuditLog.created_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1))
    rows, total = paginate(db, q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()), page, page_size)
    actions = sorted({a.split(".")[0] for a in db.scalars(select(AuditLog.action).distinct())})
    return [audit_row(e) for e in rows], total, actions


def audit_row(e: AuditLog) -> dict:
    out = {"id": sid(e.id), "actor": e.actor_name, "actorRole": e.actor_role, "action": e.action, "resource": e.resource,
           "at": iso(e.created_at), "result": e.result}
    if e.reason:
        out["reason"] = e.reason
    return out


# ---------------------------------------------------------------- dashboard
def dashboard(db: Session, viewer: User) -> dict:
    count = lambda q: db.scalar(q) or 0  # noqa: E731
    students = count(select(func.count(Student.id)))
    placed = count(select(func.count(func.distinct(Offer.student_id))).where(Offer.status == OfferStatus.ACCEPTED))
    alerts = []
    failed_docs = count(select(func.count(Document.id)).where(Document.processing == ProcessingStatus.FAILED))
    if failed_docs:
        alerts.append({"level": "error", "text": f"{failed_docs} document(s) could not be read for the AI assistant", "link": "/admin/documents"})
    inactive_faculty = count(select(func.count(User.id)).join(Role).where(Role.name == RoleName.FACULTY, User.status != UserStatus.ACTIVE))
    if inactive_faculty:
        alerts.append({"level": "warning", "text": f"{inactive_faculty} faculty account(s) are invited or inactive", "link": "/admin/users?role=faculty"})
    unverified = count(select(func.count(AcademicRecord.id)).where(AcademicRecord.cgpa.is_not(None), AcademicRecord.cgpa_verified.is_(False)))
    if unverified:
        alerts.append({"level": "warning", "text": f"{unverified} student(s) have an unverified CGPA", "link": "/admin/students"})
    out = {
        "metrics": {
            "totalUsers": count(select(func.count(User.id))),
            "activeStudents": count(select(func.count(User.id)).join(Role).where(Role.name == RoleName.STUDENT, User.status == UserStatus.ACTIVE)),
            "facultyAccounts": count(select(func.count(User.id)).join(Role).where(Role.name == RoleName.FACULTY)),
            "companies": count(select(func.count(Company.id)).where(Company.archived_at.is_(None))),
            "activeJobs": count(select(func.count(Job.id)).where(Job.status == JobStatus.PUBLISHED)),
            "applications": count(select(func.count(Application.id))),
            "offers": count(select(func.count(Offer.id))),
        },
        "placement": {"totalStudents": students, "placed": placed, "pct": round(100 * placed / students, 1) if students else 0,
                      "accepted": count(select(func.count(Offer.id)).where(Offer.status == OfferStatus.ACCEPTED)),
                      "offers": count(select(func.count(Offer.id)))},
        "alerts": alerts,
    }
    if viewer.can("audit.view"):
        denied = count(select(func.count(AuditLog.id)).where(AuditLog.result == AuditResult.DENIED,
                                                             AuditLog.created_at >= utcnow() - timedelta(days=7)))
        if denied:
            alerts.append({"level": "info", "text": f"{denied} denied access attempt(s) in the last 7 days", "link": "/admin/audit-logs?result=denied"})
        out["activity"] = [audit_row(e) for e in db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(7))]
    return out


# ---------------------------------------------------------------- system settings
DEFAULT_SETTINGS = {
    "collegeName": "Campus Assistant College",
    "placementEmail": "placements@college.edu",
    "placementSeason": "2026-27",
    "sessionTimeoutMinutes": 60,
    "maintenanceBanner": False,
    "maintenanceMessage": "",
}
PUBLIC_KEYS = ("collegeName", "maintenanceBanner", "maintenanceMessage", "sessionTimeoutMinutes")


def get_settings_values(db: Session) -> dict:
    stored = {s.key: json.loads(s.value) for s in db.scalars(select(SystemSetting))}
    return {k: stored.get(k, v) for k, v in DEFAULT_SETTINGS.items()}


def public_settings(db: Session) -> dict:
    values = get_settings_values(db)
    return {k: values[k] for k in PUBLIC_KEYS}


def save_settings(db: Session, actor: User, body) -> dict:
    before = get_settings_values(db)
    new = body.model_dump(by_alias=True)
    changed = [k for k in DEFAULT_SETTINGS if new[k] != before[k]]
    for k in DEFAULT_SETTINGS:
        row = db.get(SystemSetting, k)
        if row:
            row.value = json.dumps(new[k])
        else:
            db.add(SystemSetting(key=k, value=json.dumps(new[k])))
    if changed:
        audit.record(db, "settings.update", "System settings", actor=actor, reason="Changed: " + ", ".join(changed))
    db.commit()
    return get_settings_values(db)


def system_status(db: Session) -> dict:
    from .assistant.llm import provider_status
    return {
        "assistant": provider_status(),
        "documents": {
            "indexed": db.scalar(select(func.count(Document.id)).where(Document.processing == ProcessingStatus.INDEXED)) or 0,
            "failed": db.scalar(select(func.count(Document.id)).where(Document.processing == ProcessingStatus.FAILED)) or 0,
        },
        "activeYear": db.scalar(select(AcademicYear.label).where(AcademicYear.active.is_(True))),
    }
