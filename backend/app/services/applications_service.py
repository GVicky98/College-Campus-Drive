"""Student applications: apply, list, detail, withdraw (+ the view shape shared with staff screens)."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..deps import ensure_permission, is_staff
from ..enums import (
    ACTIVE_APPLICATION_STATUSES, ApplicationStatus, AuditResult, EligibilityState, InterviewStatus, JobStatus,
    NotificationKind, OfferStatus, PolicyKind, RoleName,
)
from ..errors import Conflict, Forbidden, NotFound
from ..models import (
    Application, ApplicationStatusHistory, Company, EligibilitySnapshot, Interview, Job, Notification, Student, User,
    interview_candidates,
)
from ..serializers import (
    application_dict, company_dict, interview_dict, iso, job_dict, notification_dict, offer_dict, student_brief,
)
from . import audit
from .common import like, paginate, student_of
from .eligibility import enabled_policies, evaluate
from .notifications import notify
from .profile import set_placement_status

STATUS_LABEL = {
    "applied": "Applied", "shortlisted": "Shortlisted", "interview": "Interview", "selected": "Selected",
    "offer_received": "Offer received", "rejected": "Rejected", "withdrawn": "Withdrawn",
}


def next_action(db: Session, app: Application) -> dict | None:
    """{label, at?}: the browser formats `at` in the viewer's own timezone."""
    upcoming = db.scalar(
        select(Interview).join(interview_candidates)
        .where(interview_candidates.c.application_id == app.id, Interview.status == InterviewStatus.SCHEDULED,
               Interview.scheduled_at > utcnow())
        .order_by(Interview.scheduled_at).limit(1)
    )
    if upcoming:
        return {"label": upcoming.round_name, "at": iso(upcoming.scheduled_at)}
    if app.status == ApplicationStatus.OFFER_RECEIVED and app.offer and app.offer.status == OfferStatus.RECEIVED:
        return {"label": "Respond to offer by", "at": iso(app.offer.accept_by)}
    label = {
        ApplicationStatus.SHORTLISTED: "Awaiting interview schedule",
        ApplicationStatus.APPLIED: "Awaiting screening",
        ApplicationStatus.SELECTED: "Offer being prepared",
    }.get(app.status)
    return {"label": label} if label else None


def application_view(db: Session, app: Application, *, with_student: bool = False, mask: bool = True) -> dict:
    view = {
        "application": application_dict(app),
        "job": job_dict(app.job),
        "company": company_dict(app.job.company),
    }
    action = next_action(db, app)
    if action:
        view["nextAction"] = action
    if with_student:
        view["student"] = student_brief(app.student, mask=mask)
    return view


def add_history(app: Application, status: str, note: str, actor: User | None) -> None:
    app.history.append(ApplicationStatusHistory(
        status=status, at=utcnow(), note=note[:255] if note else None,
        changed_by=actor.id if actor else None, changed_by_name=actor.name if actor else "System",
    ))


# ---------------------------------------------------------------- student actions
def apply(db: Session, user: User, job_id: int) -> Application:
    student = db.scalar(select(Student).where(Student.user_id == user.id).with_for_update())
    if not student:
        raise NotFound("Student profile not found.")
    job = db.get(Job, job_id)
    if not job or job.status == JobStatus.DRAFT:
        raise NotFound("Job not found.")
    if job.status != JobStatus.PUBLISHED or job.archived_at:
        raise Conflict("This job is not accepting applications.")
    if job.deadline < utcnow():
        raise Conflict("The application deadline has passed.")
    existing = db.scalar(select(Application.id).where(
        Application.student_id == student.id, Application.job_id == job.id,
        Application.status != ApplicationStatus.WITHDRAWN))
    if existing:
        raise Conflict("You have already applied to this job.")

    result = evaluate(db, student, job)
    if result["state"] != EligibilityState.ELIGIBLE:
        audit.deny(db, user, "application.create", f"Job {job.id}", result["summary"])
        raise Forbidden(result["summary"])

    for policy in enabled_policies(db, PolicyKind.APPLICATION_LIMIT)[:1]:
        limit = int(policy.params.get("maxActiveApplications", 8))
        active = db.scalar(select(func.count(Application.id)).where(
            Application.student_id == student.id, Application.status.in_(ACTIVE_APPLICATION_STATUSES))) or 0
        if active >= limit:
            raise Conflict(f"You already have {active} active applications; the limit is {limit}.")

    now = utcnow()
    app = Application(student_id=student.id, job_id=job.id, status=ApplicationStatus.APPLIED, applied_at=now, updated_at=now)
    app.snapshot = EligibilitySnapshot(state=result["state"], summary=result["summary"], checks=result["checks"], evaluated_at=now)
    add_history(app, ApplicationStatus.APPLIED, "Application submitted", user)
    db.add(app)
    db.flush()
    set_placement_status(db, student)
    notify(db, user.id, f"Application submitted — {job.company.name}", f"You applied for {job.title}.",
           NotificationKind.APPLICATION, f"/student/applications/{app.id}")
    audit.record(db, "application.create", f"Application {app.id} · Job {job.id}", actor=user)
    db.commit()
    return app


def list_mine(db: Session, user: User, status: str | None, q: str | None, page: int, page_size: int):
    student = student_of(db, user)
    query = select(Application).join(Job).join(Company).where(Application.student_id == student.id)
    if status:
        query = query.where(Application.status == status)
    if q:
        query = query.where(or_(Job.title.ilike(like(q)), Company.name.ilike(like(q))))
    rows, total = paginate(db, query.order_by(Application.updated_at.desc(), Application.id.desc()), page, page_size)
    return [application_view(db, a) for a in rows], total


def get_for_viewer(db: Session, user: User, application_id: int) -> Application:
    app = db.get(Application, application_id)
    if not app:
        raise NotFound("Application not found.")
    if user.role_name == RoleName.STUDENT:
        if app.student.user_id != user.id:
            audit.deny(db, user, "application.read", f"Application {application_id}", "Not the owner")
            raise Forbidden("You can only view your own applications.")
    else:
        ensure_permission(db, user, "applications.review", "students.view")
    return app


def detail(db: Session, user: User, application_id: int) -> dict:
    app = get_for_viewer(db, user, application_id)
    staff = is_staff(user)
    view = application_view(db, app, with_student=staff, mask=user.role_name != RoleName.ADMIN)
    interviews = db.scalars(
        select(Interview).join(interview_candidates).where(interview_candidates.c.application_id == app.id)
        .order_by(Interview.scheduled_at)
    ).unique().all()
    view["interviews"] = [interview_dict(i) for i in interviews]
    notes = db.scalars(
        select(Notification).where(
            Notification.user_id == app.student.user_id,
            Notification.kind.in_([NotificationKind.INTERVIEW, NotificationKind.APPLICATION, NotificationKind.OFFER]))
        .order_by(Notification.created_at.desc()).limit(5)
    )
    view["notifications"] = [notification_dict(n) for n in notes]
    if app.offer:
        view["offer"] = offer_dict(app.offer)
    return view


def withdraw(db: Session, user: User, application_id: int) -> Application:
    student = student_of(db, user)
    app = db.get(Application, application_id)
    if not app or app.student_id != student.id:
        raise NotFound("Application not found.")
    if app.status not in (ApplicationStatus.APPLIED, ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW):
        raise Conflict(f"An application that is {STATUS_LABEL[app.status].lower()} cannot be withdrawn.")
    app.status = ApplicationStatus.WITHDRAWN
    app.updated_at = utcnow()
    add_history(app, ApplicationStatus.WITHDRAWN, "Withdrawn by student", user)
    audit.record(db, "application.withdraw", f"Application {app.id}", actor=user, result=AuditResult.SUCCESS)
    db.commit()
    return app
