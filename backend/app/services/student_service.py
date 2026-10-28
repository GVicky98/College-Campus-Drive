"""Student self-service: profile, onboarding and the student dashboard."""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import (
    ACTIVE_APPLICATION_STATUSES, ApplicationStatus, EligibilityState, InterviewStatus, JobStatus, SkillKind,
)
from ..errors import Conflict, Forbidden, NotFound
from ..models import (
    AcademicRecord, Application, ApplicationStatusHistory, Department, Interview, Job, Offer, Student, User,
    interview_candidates,
)
from ..serializers import iso, sid, student_dict, user_dict
from . import audit
from .common import student_of
from .jobs_service import student_job_view
from .profile import compute_completion, missing_items, set_tags

# Fields a student may never set on their own record.
CONTROLLED_FIELDS = {
    "id", "userId", "role", "placementStatus", "departmentId", "studentCode", "graduationYear", "profileCompletion",
    "email", "name", "status", "academic",
}


def profile(db: Session, user: User) -> dict:
    s = student_of(db, user)
    out = student_dict(s)
    out["missing"] = missing_items(s)
    out["departmentName"] = s.department.name
    return out


def update_profile(db: Session, user: User, raw: dict, patch) -> dict:
    s = student_of(db, user)
    forbidden = sorted(CONTROLLED_FIELDS & set(raw))
    if forbidden:
        audit.deny(db, user, "student.update", f"Student {s.id}", "Controlled fields: " + ", ".join(forbidden))
        raise Forbidden("These fields are managed by the placement cell: " + ", ".join(forbidden))

    data = patch.model_dump(exclude_unset=True)
    a = s.academic or AcademicRecord(student_id=s.id)
    s.academic = a
    reset_verification = False
    for key in ("phone", "portfolio_url", "resume_file"):  # empty text clears the value
        if key in data:
            setattr(s, key, data[key] or None)
    for key in ("degree", "current_year"):
        if key in data:
            setattr(s, key, data[key])
    if "cgpa" in data:
        new = Decimal(str(data["cgpa"])) if data["cgpa"] is not None else None
        if new != a.cgpa:
            a.cgpa = new
            reset_verification = True
    if "active_arrears" in data and data["active_arrears"] != a.active_arrears:
        a.active_arrears = data["active_arrears"]
        reset_verification = True
    if "arrear_history" in data:
        a.arrear_history = data["arrear_history"]
    if reset_verification:
        a.cgpa_verified, a.verified_by, a.verified_at = False, None, None
    for key, kind in (("skills", SkillKind.SKILL), ("interests", SkillKind.INTEREST), ("preferred_roles", SkillKind.PREFERRED_ROLE)):
        if key in data:
            set_tags(s, kind, data[key])
    db.flush()
    s.profile_completion = compute_completion(s)
    audit.record(db, "student.update", f"Student {s.id}", actor=user,
                 reason="Academic change: verification reset" if reset_verification else None)
    db.commit()
    return profile(db, user)


def onboarding(db: Session, user: User, body) -> dict:
    if user.onboarding_complete:
        raise Conflict("Onboarding is already complete.")
    s = student_of(db, user)
    if not db.get(Department, body.department_id):
        raise NotFound("Department not found.")
    taken = db.scalar(select(Student.id).where(func.lower(Student.student_code) == body.student_code.lower(), Student.id != s.id))
    if taken:
        raise Conflict("That student ID is already registered.")
    s.student_code = body.student_code
    s.department_id = body.department_id
    s.degree = body.degree
    s.current_year = body.current_year
    s.graduation_year = body.graduation_year
    s.phone = body.phone or None
    s.portfolio_url = body.portfolio_url or None
    if body.resume_file:
        s.resume_file = body.resume_file
    a = s.academic or AcademicRecord()
    s.academic = a
    a.cgpa = Decimal(str(body.cgpa))
    a.active_arrears = body.active_arrears
    a.arrear_history = body.arrear_history
    a.cgpa_verified = False
    set_tags(s, SkillKind.SKILL, body.skills)
    set_tags(s, SkillKind.INTEREST, body.interests)
    set_tags(s, SkillKind.PREFERRED_ROLE, body.preferred_roles)
    user.department_id = body.department_id
    user.onboarding_complete = True
    db.flush()
    s.profile_completion = compute_completion(s)
    audit.record(db, "student.onboarding", f"Student {s.id}", actor=user)
    db.commit()
    return user_dict(user)


def dashboard(db: Session, user: User) -> dict:
    s = student_of(db, user)
    now = utcnow()
    open_jobs = db.scalars(select(Job).where(Job.status == JobStatus.PUBLISHED, Job.deadline > now, Job.archived_at.is_(None))).unique().all()
    views = [student_job_view(db, s, j) for j in open_jobs]
    eligible = [v for v in views if v["eligibility"]["state"] == EligibilityState.ELIGIBLE]
    apps = db.scalars(select(Application).where(Application.student_id == s.id)).unique().all()
    active_apps = [a for a in apps if a.status in ACTIVE_APPLICATION_STATUSES]

    events = []
    interviews = db.scalars(
        select(Interview).join(interview_candidates).join(Application, Application.id == interview_candidates.c.application_id)
        .where(Application.student_id == s.id, Interview.status == InterviewStatus.SCHEDULED, Interview.scheduled_at > now)
    ).unique().all()
    for i in interviews:
        events.append({"id": sid(i.id), "title": f"{i.round_name} — {i.job.title}", "sub": i.job.company.name,
                       "at": iso(i.scheduled_at), "kind": "interview", "location": i.location})
    for a in apps:
        drive = a.job.drive
        if a.status not in (ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN) and drive and drive.drive_date and drive.drive_date > now:
            events.append({"id": f"d_{a.job_id}", "title": f"{a.job.title} drive", "sub": a.job.company.name,
                           "at": iso(drive.drive_date), "kind": "drive"})
    events.sort(key=lambda e: e["at"])
    events = events[:5]

    deadlines = sorted(
        [v for v in views if not v.get("applicationId") and v["eligibility"]["state"] != EligibilityState.NOT_ELIGIBLE],
        key=lambda v: v["job"]["deadline"])[:4]
    recommended = sorted([v for v in eligible if not v.get("applicationId")], key=lambda v: -v["relevance"])[:3]

    history = db.scalars(
        select(ApplicationStatusHistory).join(Application).where(Application.student_id == s.id)
        .order_by(ApplicationStatusHistory.at.desc()).limit(6)
    ).all()
    app_by_id = {a.id: a for a in apps}
    activity = [{
        "at": iso(h.at), "status": h.status, "note": h.note, "applicationId": sid(h.application_id),
        "text": f"{app_by_id[h.application_id].job.company.name} — {app_by_id[h.application_id].job.title}",
    } for h in history]

    out = student_dict(s)
    out["departmentName"] = s.department.name
    return {
        "student": out,
        "metrics": {
            "eligibleJobs": len(eligible),
            "activeApplications": len(active_apps),
            "offers": db.scalar(select(func.count(Offer.id)).where(Offer.student_id == s.id)) or 0,
            "upcoming": len(events),
        },
        "events": events,
        "deadlines": deadlines,
        "recommended": recommended,
        "activity": activity,
    }
