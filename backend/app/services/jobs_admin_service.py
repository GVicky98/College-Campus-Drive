"""Creating and editing jobs, and the job lifecycle.

Lifecycle (every other move is a 409):
    draft      -> published, cancelled
    published  -> draft (unpublish, only while nobody has applied), closed, cancelled
    closed     -> published (reopen)
    cancelled  -> (final)
Publishing / reopening needs a future deadline and a company that is not archived. Cancelling needs a reason
and notifies active applicants. Archive is a separate soft flag for draft / closed / cancelled jobs.
"""
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..deps import ensure_permission
from ..enums import ACTIVE_APPLICATION_STATUSES, ApplicationStatus, EligibilityState, JobStatus, NotificationKind
from ..errors import Conflict, NotFound, ValidationFailed
from ..models import (
    Application, Company, Department, Document, DriveEvent, HiringDrive, Interview, Job, JobEligibilityRule, Offer,
    Student, User,
)
from ..serializers import document_dict, interview_dict, job_dict
from . import audit
from .eligibility import evaluate
from .jobs_service import applicant_count
from .notifications import notify
from ..serializers import job_view

TRANSITIONS = {
    JobStatus.DRAFT: {JobStatus.PUBLISHED, JobStatus.CANCELLED},
    JobStatus.PUBLISHED: {JobStatus.DRAFT, JobStatus.CLOSED, JobStatus.CANCELLED},
    JobStatus.CLOSED: {JobStatus.PUBLISHED},
    JobStatus.CANCELLED: set(),
}
ACTION_NAME = {
    (JobStatus.DRAFT, JobStatus.PUBLISHED): "publish", (JobStatus.PUBLISHED, JobStatus.DRAFT): "unpublish",
    (JobStatus.PUBLISHED, JobStatus.CLOSED): "close", (JobStatus.CLOSED, JobStatus.PUBLISHED): "reopen",
}


def _job(db: Session, job_id: int, lock: bool = False) -> Job:
    q = select(Job).where(Job.id == job_id)
    job = db.scalar(q.with_for_update() if lock else q)
    if not job:
        raise NotFound("Job not found.")
    return job


def transition(db: Session, user: User, job: Job, target: str, reason: str | None = None) -> None:
    current = JobStatus(job.status)
    target = JobStatus(target)
    if target == current:
        return
    ensure_permission(db, user, "drives.publish")
    if job.archived_at:
        raise Conflict("Restore this job before changing its status.")
    if target not in TRANSITIONS[current]:
        raise Conflict(f"A {current} job cannot be moved to {target}.")
    if target == JobStatus.CANCELLED and len((reason or "").strip()) < 3:
        raise ValidationFailed("Give a reason for cancelling (at least 3 characters).", field="reason")
    if target == JobStatus.PUBLISHED:
        if job.deadline <= utcnow():
            raise ValidationFailed("Set a deadline in the future before publishing.", field="deadline")
        if job.company.archived_at:
            raise Conflict("The company is archived. Restore it first.")
    if current == JobStatus.PUBLISHED and target == JobStatus.DRAFT and applicant_count(db, job.id):
        raise Conflict("Students have already applied, so this job cannot go back to draft. Close it instead.")

    job.status = target
    if target == JobStatus.PUBLISHED and not job.published_at:
        job.published_at = utcnow()
    if target == JobStatus.CANCELLED:
        active = db.scalars(select(Application).where(Application.job_id == job.id,
                                                      Application.status.in_(ACTIVE_APPLICATION_STATUSES))).unique().all()
        for a in active:
            notify(db, a.student.user_id, f"{job.company.name} drive cancelled",
                   f"The {job.title} drive was cancelled. Reason: {reason.strip()}", NotificationKind.DRIVE,
                   f"/student/applications/{a.id}")
    action = ACTION_NAME.get((current, target), "cancel")
    audit.record(db, f"job.{action}", f"Job {job.id} · {job.title}", actor=user, reason=reason)


def _sync_drive(db: Session, user: User, job: Job, body) -> None:
    """Each job owns a hiring drive whose events are the job's rounds (copy-on-write if a drive is shared)."""
    drive = job.drive
    if drive and db.scalar(select(func.count(Job.id)).where(Job.drive_id == drive.id, Job.id != job.id)):
        drive = None
    if not drive:
        drive = HiringDrive(company_id=job.company_id, name="", created_by=user.id)
        job.drive = drive
    drive.company_id = job.company_id
    drive.name = f"{job.title} — campus drive"[:160]
    drive.drive_date = body.drive_date
    existing = list(drive.events)
    for i, r in enumerate(body.rounds, start=1):
        ev = existing[i - 1] if i <= len(existing) else DriveEvent()
        ev.sequence, ev.name, ev.mode, ev.scheduled_at, ev.location = i, r.name, r.mode, r.date, r.location or None
        if i > len(existing):
            drive.events.append(ev)
    for ev in existing[len(body.rounds):]:
        drive.events.remove(ev)


def _snapshot(job: Job) -> dict:
    d = job_dict(job)
    flat = {k: v for k, v in d.items() if k not in ("eligibility", "updatedAt", "rounds")}
    flat.update({f"eligibility.{k}": v for k, v in d["eligibility"].items()})
    flat["rounds"] = [(r["name"], r["mode"], r.get("date"), r.get("location")) for r in d["rounds"]]
    return flat


def save(db: Session, user: User, body, job_id: int | None = None) -> Job:
    ensure_permission(db, user, "jobs.create")
    if body.status == JobStatus.PUBLISHED:
        ensure_permission(db, user, "drives.publish")
    company = db.get(Company, body.company_id)
    if not company:
        raise ValidationFailed("Unknown company.", field="companyId")
    depts = []
    for did in body.eligibility.department_ids:
        d = db.get(Department, did)
        if not d:
            raise ValidationFailed("Unknown department.", field="departmentIds")
        depts.append(d)

    if job_id:
        job = _job(db, job_id, lock=True)
        if job.archived_at:
            raise Conflict("Restore this job before editing it.")
        if job.status in (JobStatus.CLOSED, JobStatus.CANCELLED):
            raise Conflict(f"A {job.status} job cannot be edited.")
        if company.id != job.company_id:
            if job.status != JobStatus.DRAFT or applicant_count(db, job.id):
                raise Conflict("The company can only change while the job is a draft with no applicants.")
            if company.archived_at:
                raise ValidationFailed("That company is archived.", field="companyId")
        before = _snapshot(job)
    else:
        if company.archived_at:
            raise ValidationFailed("That company is archived.", field="companyId")
        job = Job(status=JobStatus.DRAFT, created_by=user.id)
        job.rule = JobEligibilityRule()
        db.add(job)
        before = None

    job.company_id = company.id
    job.company = company
    job.title, job.domain, job.location, job.job_type = body.title, body.domain, body.location, body.type
    job.description, job.responsibilities, job.skills = body.description, body.responsibilities, body.skills
    job.ctc_lpa = Decimal(str(body.ctc_lpa)) if body.ctc_lpa is not None else None
    job.stipend_per_month = body.stipend_per_month
    job.open_date, job.deadline = body.open_date, body.deadline
    e = body.eligibility
    rule = job.rule or JobEligibilityRule()
    job.rule = rule
    rule.min_cgpa = Decimal(str(e.min_cgpa))
    rule.max_active_arrears = e.max_active_arrears
    rule.max_arrear_history = e.max_arrear_history
    rule.graduation_years = e.graduation_years
    rule.required_skills = e.required_skills
    job.departments = depts
    db.flush()
    _sync_drive(db, user, job, body)
    db.flush()

    if before is None:
        audit.record(db, "job.create", f"Job {job.id} · {job.title}", actor=user)
    else:
        after = _snapshot(job)
        changed = [k for k in after if before.get(k) != after[k]]
        if changed:
            audit.record(db, "job.update", f"Job {job.id} · {job.title}", actor=user, reason="Changed: " + ", ".join(changed)[:380])
    transition(db, user, job, body.status)
    db.commit()
    db.refresh(job)
    return job


def set_status(db: Session, user: User, job_id: int, status: str, reason: str | None) -> Job:
    job = _job(db, job_id, lock=True)
    transition(db, user, job, status, reason)
    db.commit()
    return job


def archive(db: Session, user: User, job_id: int, archived: bool) -> Job:
    job = _job(db, job_id, lock=True)
    if archived and not job.archived_at:
        if job.status == JobStatus.PUBLISHED:
            raise Conflict("Close or cancel a published job before archiving it.")
        job.archived_at = utcnow()
        audit.record(db, "job.archive", f"Job {job.id} · {job.title}", actor=user)
    elif not archived and job.archived_at:
        job.archived_at = None
        audit.record(db, "job.unarchive", f"Job {job.id} · {job.title}", actor=user)
    db.commit()
    return job


def drive_detail(db: Session, job_id: int) -> dict:
    job = _job(db, job_id)
    statuses = db.scalars(select(Application.status).where(Application.job_id == job.id)).all()
    count = lambda *s: sum(1 for x in statuses if x in s)  # noqa: E731
    students = db.scalars(select(Student)).unique().all()
    eligible = sum(1 for s in students if evaluate(db, s, job, ignore_open=True)["state"] != EligibilityState.NOT_ELIGIBLE)
    interviews = db.scalars(select(Interview).where(Interview.job_id == job.id).order_by(Interview.scheduled_at)).unique().all()
    docs = db.scalars(select(Document).where(
        Document.owner_student_id.is_(None),
        (Document.job_id == job.id) | ((Document.company_id == job.company_id) & Document.job_id.is_(None)),
    ).order_by(Document.created_at.desc())).unique().all()
    return {
        "view": job_view(job, applicantCount=len(statuses)),
        "eligibleStudents": eligible,
        "counts": {
            "applied": len(statuses),
            "shortlisted": count(ApplicationStatus.SHORTLISTED),
            "interview": count(ApplicationStatus.INTERVIEW),
            "selected": count(ApplicationStatus.SELECTED, ApplicationStatus.OFFER_RECEIVED),
            "offers": db.scalar(select(func.count(Offer.id)).where(Offer.job_id == job.id)) or 0,
            "rejected": count(ApplicationStatus.REJECTED),
        },
        "interviews": [{**interview_dict(i), "candidateCount": len(i.candidates)} for i in interviews],
        "documents": [document_dict(d) for d in docs],
    }
