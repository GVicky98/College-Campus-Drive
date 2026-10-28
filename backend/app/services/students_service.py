"""Staff student directory and CGPA verification."""
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import NotificationKind, RoleName, SkillKind
from ..errors import Forbidden, NotFound, ValidationFailed
from ..models import AcademicRecord, Application, Offer, Student, StudentSkill, User
from ..serializers import offer_view, student_dict
from . import audit
from .applications_service import application_view
from .common import like, paginate
from .notifications import notify


def row(db: Session, s: Student, viewer: User) -> dict:
    out = student_dict(s, mask=viewer.role_name != RoleName.ADMIN)
    out["applicationCount"] = db.scalar(select(func.count(Application.id)).where(Application.student_id == s.id)) or 0
    out["offerCount"] = db.scalar(select(func.count(Offer.id)).where(Offer.student_id == s.id)) or 0
    out["departmentName"] = s.department.name
    return out


def directory_query(q=None, dept=None, year=None, min_cgpa=None, skill=None, placement=None):
    query = select(Student).join(User, User.id == Student.user_id)
    if q:
        query = query.where(or_(User.name.ilike(like(q)), Student.student_code.ilike(like(q)), User.email.ilike(like(q))))
    if dept:
        query = query.where(Student.department_id == dept)
    if year:
        query = query.where(Student.graduation_year == year)
    if min_cgpa is not None:
        query = query.where(Student.id.in_(select(AcademicRecord.student_id).where(AcademicRecord.cgpa >= min_cgpa)))
    if skill:
        query = query.where(Student.id.in_(select(StudentSkill.student_id).where(
            StudentSkill.kind == SkillKind.SKILL, StudentSkill.name.ilike(like(skill)))))
    if placement:
        query = query.where(Student.placement_status == placement)
    return query.order_by(User.name)


def list_students(db: Session, viewer: User, f: dict, page: int, page_size: int):
    rows, total = paginate(db, directory_query(**f), page, page_size)
    return [row(db, s, viewer) for s in rows], total


def detail(db: Session, viewer: User, student_id: int) -> dict:
    s = db.get(Student, student_id)
    if not s:
        raise NotFound("Student not found.")
    mask = viewer.role_name != RoleName.ADMIN
    apps = db.scalars(select(Application).where(Application.student_id == s.id).order_by(Application.applied_at.desc())).unique().all()
    offers = db.scalars(select(Offer).where(Offer.student_id == s.id).order_by(Offer.offered_at.desc())).all()
    audit.record(db, "student.view", f"Student {s.id} · {s.student_code}", actor=viewer)
    db.commit()
    return {"student": row(db, s, viewer), "applications": [application_view(db, a) for a in apps],
            "offers": [offer_view(o) for o in offers], "masked": mask}


def verify_cgpa(db: Session, actor: User, student_id: int, cgpa: float | None) -> dict:
    s = db.get(Student, student_id)
    if not s:
        raise NotFound("Student not found.")
    if s.user_id == actor.id:
        raise Forbidden("You cannot verify your own record.")
    a = s.academic or AcademicRecord()
    s.academic = a
    if cgpa is None and a.cgpa is None:
        raise ValidationFailed("There is no CGPA to verify. Enter the correct value.", field="cgpa")
    reason = None
    if cgpa is not None and (a.cgpa is None or Decimal(str(cgpa)) != a.cgpa):
        reason = f"CGPA corrected {a.cgpa} -> {cgpa}"
        a.cgpa = Decimal(str(cgpa))
    a.cgpa_verified, a.verified_by, a.verified_at = True, actor.id, utcnow()
    notify(db, s.user_id, "Your CGPA has been verified", f"The placement cell verified your CGPA ({a.cgpa}).",
           NotificationKind.SYSTEM, "/student/profile")
    audit.record(db, "student.verify_cgpa", f"Student {s.id} · {s.student_code}", actor=actor, reason=reason)
    db.commit()
    return row(db, s, actor)
