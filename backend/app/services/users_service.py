"""User administration: invite, edit, (de)activate, reset password, bulk student import, role-permission matrix.

Escalation guards:
  * only an administrator may create / edit / (de)activate / reset an administrator account, or grant the admin role;
  * nobody may change their own role or status; the last active administrator is protected;
  * student accounts cannot become staff and back;
  * the student role never receives permissions; admin always keeps roles.manage + users.manage;
    roles.manage cannot be granted to another role.
"""
import logging
import re
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import utcnow
from ..enums import RoleName, UserStatus
from ..errors import Conflict, Forbidden, NotFound, ValidationFailed
from ..models import AcademicRecord, AcademicYear, Department, FacultyProfile, Permission, Role, Student, User
from ..security import unusable_password
from ..serializers import user_dict
from . import audit
from .auth_service import issue_reset_token, reset_link
from .common import like, paginate

log = logging.getLogger("campus")
STAFF = (RoleName.FACULTY, RoleName.ADMIN)
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-/]{0,31}$")


def view(u: User) -> dict:
    out = user_dict(u)
    out["departmentCode"] = u.department.code if u.department else None
    if u.student:
        out["graduationYear"] = u.student.graduation_year
    return out


def _role(db: Session, name: str) -> Role:
    return db.scalar(select(Role).where(Role.name == name))


def _guard_admin(db: Session, actor: User, target_role: str, what: str) -> None:
    if target_role == RoleName.ADMIN and actor.role_name != RoleName.ADMIN:
        audit.deny(db, actor, "access.denied", what, "Only administrators manage administrator accounts")
        raise Forbidden("Only an administrator can manage administrator accounts.")


def _active_admins(db: Session) -> int:
    return db.scalar(select(func.count(User.id)).join(Role).where(Role.name == RoleName.ADMIN, User.status == UserStatus.ACTIVE)) or 0


def _unique(db: Session, email: str, code: str, exclude_id: int | None = None) -> None:
    q = lambda col, v: select(User.id).where(func.lower(col) == v.lower(), User.id != (exclude_id or 0))  # noqa: E731
    if db.scalar(q(User.email, email)):
        raise Conflict("That e-mail is already registered.")
    if db.scalar(q(User.user_code, code)):
        raise Conflict("That user ID is already taken.")


def _graduation_year(db: Session, given: int | None) -> int:
    if given:
        return given
    active = db.scalar(select(AcademicYear).where(AcademicYear.active.is_(True)))
    if not active:
        raise ValidationFailed("Give a graduation year (no academic year is marked current).", field="graduationYear")
    return active.graduation_year


def _invite(db: Session, user: User) -> None:
    raw = issue_reset_token(db, user, get_settings().invite_token_minutes)
    if not get_settings().is_production:
        log.warning("Invitation link for %s: %s", user.email, reset_link(raw))


def list_users(db: Session, q, role, status, dept, page, page_size):
    query = select(User).join(Role)
    if q:
        query = query.where(or_(User.name.ilike(like(q)), User.email.ilike(like(q)), User.user_code.ilike(like(q))))
    if role:
        query = query.where(Role.name == role)
    if status:
        query = query.where(User.status == status)
    if dept:
        query = query.where(User.department_id == dept)
    rows, total = paginate(db, query.order_by(User.name), page, page_size)
    return [view(u) for u in rows], total


def create_user(db: Session, actor: User, body) -> User:
    _guard_admin(db, actor, body.role, "user.create")
    if body.role == RoleName.STUDENT and not body.department_id:
        raise ValidationFailed("Students need a department.", field="departmentId")
    if body.graduation_year and body.role != RoleName.STUDENT:
        raise ValidationFailed("Only students have a graduation year.", field="graduationYear")
    if body.department_id and not db.get(Department, body.department_id):
        raise ValidationFailed("Unknown department.", field="departmentId")
    email = body.email.lower()
    _unique(db, email, body.user_code)
    user = User(user_code=body.user_code, name=body.name, email=email, role=_role(db, body.role), department_id=body.department_id,
                status=UserStatus.INVITED, password_hash=unusable_password(), onboarding_complete=body.role != RoleName.STUDENT)
    db.add(user)
    db.flush()
    if body.role == RoleName.STUDENT:
        s = Student(user_id=user.id, student_code=body.user_code, department_id=body.department_id, degree="", current_year=4,
                    graduation_year=_graduation_year(db, body.graduation_year))
        s.academic = AcademicRecord()
        db.add(s)
    elif body.role == RoleName.FACULTY:
        db.add(FacultyProfile(user_id=user.id, department_id=body.department_id))
    _invite(db, user)
    audit.record(db, "user.create", f"User {user.id} · {user.user_code}", actor=actor, reason=f"Invited {user.user_code} as {body.role}")
    db.commit()
    return user


def _get(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if not u:
        raise NotFound("User not found.")
    return u


def update_user(db: Session, actor: User, user_id: int, body) -> User:
    u = _get(db, user_id)
    _guard_admin(db, actor, u.role_name, f"User {u.id}")
    _guard_admin(db, actor, body.role, f"User {u.id}")
    old_role, new_role = u.role_name, body.role
    if new_role != old_role:
        if u.id == actor.id:
            raise Conflict("You cannot change your own role.")
        if RoleName.STUDENT in (old_role, new_role):
            raise Conflict("Student accounts cannot be converted to staff accounts or back.")
        if old_role == RoleName.ADMIN and u.status == UserStatus.ACTIVE and _active_admins(db) <= 1:
            raise Conflict("This is the last active administrator.")
    if new_role == RoleName.STUDENT and not body.department_id:
        raise ValidationFailed("Students need a department.", field="departmentId")
    if body.graduation_year and new_role != RoleName.STUDENT:
        raise ValidationFailed("Only students have a graduation year.", field="graduationYear")
    if body.department_id and not db.get(Department, body.department_id):
        raise ValidationFailed("Unknown department.", field="departmentId")
    email = body.email.lower()
    _unique(db, email, body.user_code, u.id)

    before = view(u)
    old_code = u.user_code
    u.name, u.email, u.user_code, u.department_id = body.name, email, body.user_code, body.department_id
    if new_role != old_role:
        u.role = _role(db, new_role)
        if new_role == RoleName.FACULTY and not u.faculty_profile:
            db.add(FacultyProfile(user_id=u.id, department_id=u.department_id))
    if u.student:
        if u.student.student_code == old_code:  # a code chosen at onboarding is never overwritten
            u.student.student_code = body.user_code
        if body.department_id:
            u.student.department_id = body.department_id
        if body.graduation_year:
            u.student.graduation_year = body.graduation_year
    if u.faculty_profile:
        u.faculty_profile.department_id = u.department_id
    db.flush()
    changed = [k for k, v in view(u).items() if before.get(k) != v and k not in ("createdAt", "lastLoginAt")]
    if changed:
        action = "user.role_change" if new_role != old_role else "user.update"
        audit.record(db, action, f"User {u.id} · {u.user_code}", actor=actor, reason="Changed: " + ", ".join(changed))
    db.commit()
    return u


def set_status(db: Session, actor: User, user_id: int, status: str) -> User:
    u = _get(db, user_id)
    _guard_admin(db, actor, u.role_name, f"User {u.id}")
    if u.id == actor.id:
        raise Conflict("You cannot deactivate your own account.")
    if status == u.status or (status == UserStatus.ACTIVE and u.status == UserStatus.INVITED):
        return u
    if status == UserStatus.INACTIVE and u.role_name == RoleName.ADMIN and u.status == UserStatus.ACTIVE and _active_admins(db) <= 1:
        raise Conflict("This is the last active administrator.")
    u.status = status
    if status == UserStatus.INACTIVE:
        u.password_changed_at = utcnow()  # kills existing refresh tokens
    audit.record(db, "user.deactivate" if status == UserStatus.INACTIVE else "user.activate", f"User {u.id} · {u.user_code}", actor=actor)
    db.commit()
    return u


def reset_password(db: Session, actor: User, user_id: int) -> str:
    u = _get(db, user_id)
    _guard_admin(db, actor, u.role_name, f"User {u.id}")
    if u.status == UserStatus.INACTIVE:
        raise Conflict("Activate the account before resetting its password.")
    s = get_settings()
    raw = issue_reset_token(db, u, s.invite_token_minutes if u.status == UserStatus.INVITED else s.password_reset_minutes)
    if not s.is_production:
        log.warning("Password reset link for %s: %s", u.email, reset_link(raw))
    audit.record(db, "user.reset_password", f"User {u.id} · {u.user_code}", actor=actor)
    db.commit()
    return (f"A reset link was created for {u.email}. E-mail delivery is not configured on this server, "
            "so the link is written to the server log in development.")


def import_students(db: Session, actor: User, rows: list) -> dict:
    errors, valid = [], []
    depts = {d.code.lower(): d for d in db.scalars(select(Department))}
    seen_codes, seen_emails = set(), set()
    for i, r in enumerate(rows, start=2):  # row 1 is the CSV header
        def err(field, message, value):
            errors.append({"row": i, "field": field, "message": message, "value": str(value or "")[:80]})
        code, name, email = (r.student_code or "").strip(), (r.name or "").strip(), (r.email or "").strip().lower()
        dept = depts.get((r.department_code or "").strip().lower())
        year = (r.graduation_year or "").strip()
        bad = False
        if not CODE.match(code):
            err("studentCode", "Use letters, digits, . _ - / (up to 32)", code); bad = True
        elif code.lower() in seen_codes or db.scalar(select(User.id).where(func.lower(User.user_code) == code.lower())):
            err("studentCode", "This student ID already exists", code); bad = True
        if not name or len(name) > 120:
            err("name", "Enter a name (up to 120 characters)", name); bad = True
        if not EMAIL.match(email) or len(email) > 190:
            err("email", "Not a valid e-mail", email); bad = True
        elif email in seen_emails or db.scalar(select(User.id).where(func.lower(User.email) == email)):
            err("email", "This e-mail is already registered", email); bad = True
        if not dept:
            err("departmentCode", "Unknown department code", r.department_code); bad = True
        if not re.fullmatch(r"20\d{2}", year):
            err("graduationYear", "Use a 4-digit year like 2027", year); bad = True
        cgpa = None
        if r.cgpa not in (None, ""):
            try:
                cgpa = float(r.cgpa)
                if not 0 <= cgpa <= 10:
                    raise ValueError
            except ValueError:
                err("cgpa", "CGPA must be between 0 and 10", r.cgpa); bad = True
        seen_codes.add(code.lower())
        seen_emails.add(email)
        if not bad:
            valid.append((code, name, email, dept, int(year), cgpa))
    role = _role(db, RoleName.STUDENT)
    for code, name, email, dept, year, cgpa in valid:
        u = User(user_code=code, name=name, email=email, role=role, department_id=dept.id, status=UserStatus.INVITED,
                 password_hash=unusable_password(), onboarding_complete=False)
        db.add(u)
        db.flush()
        s = Student(user_id=u.id, student_code=code, department_id=dept.id, degree="", current_year=4, graduation_year=year)
        s.academic = AcademicRecord(cgpa=Decimal(str(cgpa)) if cgpa is not None else None, cgpa_verified=False)
        db.add(s)
        _invite(db, u)
    audit.record(db, "user.import", "Student import", actor=actor, reason=f"Student import ({len(valid)}/{len(rows)} rows)")
    db.commit()
    return {"total": len(rows), "imported": len(valid), "errors": errors}


# ---------------------------------------------------------------- roles & permissions
def roles_overview(db: Session) -> dict:
    perms = db.scalars(select(Permission).order_by(Permission.module, Permission.key)).all()
    roles = db.scalars(select(Role)).all()
    counts = dict(db.execute(select(Role.name, func.count(User.id)).join(User, User.role_id == Role.id).group_by(Role.name)).all())
    return {
        "permissions": [{"key": p.key, "module": p.module, "label": p.label, "description": p.description} for p in perms],
        "matrix": {r.name: sorted(p.key for p in r.permissions) for r in roles},
        "userCounts": {r.name: counts.get(r.name, 0) for r in roles},
    }


def set_permission(db: Session, actor: User, role_name: str, perm_key: str, enabled: bool) -> list[str]:
    if actor.role_name != RoleName.ADMIN:
        audit.deny(db, actor, "access.denied", "role.permissions", "Only administrators edit the matrix")
        raise Forbidden("Only an administrator can edit role permissions.")
    role = _role(db, role_name)
    perm = db.scalar(select(Permission).where(Permission.key == perm_key))
    if not role or not perm:
        raise NotFound("Unknown role or permission.")
    has = perm in role.permissions
    if enabled == has:
        return sorted(p.key for p in role.permissions)
    if enabled and role.name == RoleName.STUDENT:
        raise Conflict("The student role cannot receive staff permissions.")
    if not enabled and role.name == RoleName.ADMIN and perm.key in ("roles.manage", "users.manage"):
        raise Conflict("Administrators must keep roles.manage and users.manage.")
    if enabled and perm.key == "roles.manage" and role.name != RoleName.ADMIN:
        raise Conflict("roles.manage can only belong to administrators.")
    if enabled:
        role.permissions.append(perm)
    else:
        role.permissions.remove(perm)
    audit.record(db, "role.permissions.update", f"Role {role.name}", actor=actor,
                 reason=f"{'Granted' if enabled else 'Revoked'} {perm.key}")
    db.commit()
    return sorted(p.key for p in role.permissions)
