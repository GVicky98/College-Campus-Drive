"""Staff applicant review: list, bulk stage changes (with eligibility exceptions) and CSV export.

Stage order: applied < shortlisted < interview < selected. Moves must go forward (skipping is fine);
`rejected` is allowed from any active stage. offer_received / rejected / withdrawn are final for review.
An applicant whose eligibility snapshot was not "eligible" can only be advanced with a recorded exception.
"""
import csv
import io

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import ApplicationStatus, EligibilityState, JobStatus, NotificationKind, PolicyKind, RoleName
from ..models import AcademicRecord, Application, Company, EligibilitySnapshot, Job, Student, User
from . import audit
from .applications_service import add_history, application_view
from .common import like, paginate
from .eligibility import enabled_policies
from .notifications import notify
from .profile import set_placement_status

ORDER = [ApplicationStatus.APPLIED, ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW, ApplicationStatus.SELECTED]
FINAL = (ApplicationStatus.OFFER_RECEIVED, ApplicationStatus.REJECTED, ApplicationStatus.WITHDRAWN)
MESSAGE = {
    ApplicationStatus.SHORTLISTED: "was shortlisted",
    ApplicationStatus.INTERVIEW: "moved to the interview stage",
    ApplicationStatus.SELECTED: "was selected",
    ApplicationStatus.REJECTED: "was not taken forward",
}


def review_query(q=None, status=None, company_id=None, job_id=None, dept=None, eligibility=None, sort=None):
    query = (select(Application).join(Job, Job.id == Application.job_id).join(Company, Company.id == Job.company_id)
             .join(Student, Student.id == Application.student_id).join(User, User.id == Student.user_id))
    if q:
        p = like(q)
        query = query.where(or_(User.name.ilike(p), Student.student_code.ilike(p), Company.name.ilike(p), Job.title.ilike(p)))
    if status:
        query = query.where(Application.status == status)
    if company_id:
        query = query.where(Job.company_id == company_id)
    if job_id:
        query = query.where(Application.job_id == job_id)
    if dept:
        query = query.where(Student.department_id == dept)
    if eligibility:
        query = query.where(Application.id.in_(select(EligibilitySnapshot.application_id).where(EligibilitySnapshot.state == eligibility)))
    if sort == "cgpa":
        query = query.outerjoin(AcademicRecord, AcademicRecord.student_id == Student.id).order_by(AcademicRecord.cgpa.desc(), Application.id.desc())
    elif sort == "name":
        query = query.order_by(User.name, Application.id)
    else:
        query = query.order_by(Application.applied_at.desc(), Application.id.desc())
    return query


def list_applications(db: Session, viewer: User, f: dict, page: int, page_size: int):
    rows, total = paginate(db, review_query(**f), page, page_size)
    mask = viewer.role_name != RoleName.ADMIN
    return [application_view(db, a, with_student=True, mask=mask) for a in rows], total


def update_stage(db: Session, actor: User, ids: list[int], status: str, note: str | None, exception) -> dict:
    target = ApplicationStatus(status)
    policy = (enabled_policies(db, PolicyKind.EXCEPTION_APPROVAL) or [None])[0]
    updated, failed = [], []
    for app_id in dict.fromkeys(ids):  # de-duplicated, order kept
        app = db.scalar(select(Application).where(Application.id == app_id).with_for_update())
        if not app:
            failed.append({"id": str(app_id), "reason": "Application not found."})
            continue
        current = ApplicationStatus(app.status)
        reason = None
        if current in FINAL:
            reason = f"Already {current.replace('_', ' ')}."
        elif target == ApplicationStatus.REJECTED:
            if app.offer:
                reason = "An offer exists. Withdraw the offer first."
        else:
            if ORDER.index(target) <= ORDER.index(current):
                reason = f"Already at {current} — stages only move forward."
            elif app.job.status == JobStatus.CANCELLED:
                reason = "The job was cancelled."
            elif app.snapshot and app.snapshot.state != EligibilityState.ELIGIBLE and not app.snapshot.exception_reason:
                if not exception:
                    reason = f"Not eligible when applied ({app.snapshot.state.replace('_', ' ')}): an exception is required."
                elif policy and policy.params.get("requireApprover") and not exception.approved_by:
                    reason = "The exception needs an approver."
                else:
                    app.snapshot.exception_reason = exception.reason
                    app.snapshot.exception_approved_by = exception.approved_by
                    audit.record(db, "eligibility.exception", f"Application {app.id}", actor=actor,
                                 reason=f"{exception.reason} (approved by {exception.approved_by})")
        if reason:
            failed.append({"id": str(app.id), "reason": reason})
            continue
        app.status = target
        app.updated_at = utcnow()
        add_history(app, target, note or f"Moved to {target.replace('_', ' ')}", actor)
        audit.record(db, f"application.{target}", f"Application {app.id}", actor=actor, reason=f"{current} -> {target}")
        notify(db, app.student.user_id, f"Application update — {app.job.company.name}",
               f"Your application for {app.job.title} {MESSAGE[target]}.", NotificationKind.APPLICATION,
               f"/student/applications/{app.id}")
        if target == ApplicationStatus.REJECTED:
            set_placement_status(db, app.student)
        updated.append(str(app.id))
    db.commit()
    return {"updated": updated, "failed": failed}


def to_csv(header: list[str], rows: list[list]) -> str:
    """CSV text; cells that a spreadsheet would run as a formula are prefixed with a quote."""
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["'" + str(c) if isinstance(c, str) and c[:1] in ("=", "+", "-", "@", "\t", "\r") else c for c in r])
    return buf.getvalue()


def export_csv(db: Session, actor: User, f: dict) -> str:
    rows = db.scalars(review_query(**f).limit(5000)).unique().all()
    data = [[
        a.student.student_code or "", a.student.user.name, a.student.department.code,
        f"{a.student.academic.cgpa}" if a.student.academic and a.student.academic.cgpa is not None else "",
        a.job.company.name, a.job.title, a.snapshot.state if a.snapshot else "", a.status, f"{a.applied_at:%Y-%m-%d}",
    ] for a in rows]
    audit.record(db, "report.export", "Applications CSV", actor=actor, reason=f"Applications CSV ({len(data)} rows)")
    db.commit()
    return to_csv(["Student ID", "Name", "Department", "CGPA", "Company", "Job", "Eligibility", "Stage", "Applied on"], data)

