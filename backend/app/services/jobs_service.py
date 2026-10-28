"""Reading jobs: the student job board (with live eligibility) and the staff job list."""
from datetime import timedelta

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..deps import ensure_permission, is_staff
from ..enums import ApplicationStatus, EligibilityState, JobStatus, SkillKind
from ..errors import NotFound
from ..models import Application, Company, Job, JobEligibilityRule, SavedJob, Student, User, job_departments
from ..serializers import job_view
from .common import like, paginate, slice_page, student_of
from .eligibility import evaluate

STAFF_JOB_PERMS = ("jobs.create", "applications.review", "students.view", "drives.publish")


def applicant_count(db: Session, job_id: int) -> int:
    return db.scalar(select(func.count(Application.id)).where(Application.job_id == job_id)) or 0


def latest_application(db: Session, student_id: int, job_id: int) -> Application | None:
    """The student's most recent application to this job that was not withdrawn."""
    return db.scalar(
        select(Application)
        .where(Application.student_id == student_id, Application.job_id == job_id,
               Application.status != ApplicationStatus.WITHDRAWN)
        .order_by(Application.id.desc()).limit(1)
    )


def relevance(student: Student, job: Job, eligible: bool) -> int:
    mine = {s.lower() for s in student.tags(SkillKind.SKILL)}
    overlap = sum(1 for s in job.skills or [] if s.lower() in mine)
    return 2 * overlap + (3 if eligible else 0)


def student_job_view(db: Session, student: Student, job: Job, saved_ids: set[int] | None = None) -> dict:
    result = evaluate(db, student, job)
    app = latest_application(db, student.id, job.id)
    if saved_ids is None:
        saved_ids = {r for r in db.scalars(select(SavedJob.job_id).where(SavedJob.student_id == student.id))}
    return job_view(
        job,
        eligibility=result,
        saved=job.id in saved_ids,
        applicationId=str(app.id) if app else None,
        applicationStatus=app.status if app else None,
        relevance=relevance(student, job, result["state"] == EligibilityState.ELIGIBLE),
    )


def _apply_common_filters(q, f: dict):
    if f.get("q"):
        pattern = like(f["q"])
        q = q.where(or_(Job.title.ilike(pattern), Company.name.ilike(pattern), Job.domain.ilike(pattern),
                        cast(Job.skills, String).ilike(pattern)))
    if f.get("dept"):
        q = q.where(Job.id.in_(select(job_departments.c.job_id).where(job_departments.c.department_id == int(f["dept"]))))
    if f.get("min_cgpa") is not None:
        q = q.where(Job.id.in_(select(JobEligibilityRule.job_id).where(JobEligibilityRule.min_cgpa <= f["min_cgpa"])))
    if f.get("location"):
        q = q.where(Job.location.ilike(like(f["location"])))
    if f.get("type"):
        q = q.where(Job.job_type == f["type"])
    if f.get("deadline_days"):
        now = utcnow()
        q = q.where(Job.deadline > now, Job.deadline <= now + timedelta(days=f["deadline_days"]))
    if f.get("company_id"):
        q = q.where(Job.company_id == f["company_id"])
    return q


def list_for_student(db: Session, user: User, f: dict, page: int, page_size: int) -> tuple[list[dict], int]:
    student = student_of(db, user)
    tab = f.get("tab") or "all"
    q = select(Job).join(Company)
    if tab == "applied":
        applied = select(Application.job_id).where(Application.student_id == student.id)
        q = q.where(Job.id.in_(applied), Job.status != JobStatus.DRAFT)
    else:
        q = q.where(Job.status == JobStatus.PUBLISHED, Job.archived_at.is_(None), Company.archived_at.is_(None))
    if tab == "saved":
        q = q.where(Job.id.in_(select(SavedJob.job_id).where(SavedJob.student_id == student.id)))
    q = _apply_common_filters(q, f)

    saved_ids = set(db.scalars(select(SavedJob.job_id).where(SavedJob.student_id == student.id)))
    views = [student_job_view(db, student, j, saved_ids) for j in db.scalars(q).unique().all()]
    if tab == "eligible":
        views = [v for v in views if v["eligibility"]["state"] == EligibilityState.ELIGIBLE]
    elif tab == "not_eligible":
        views = [v for v in views if v["eligibility"]["state"] != EligibilityState.ELIGIBLE]

    sort = f.get("sort") or "deadline"
    if sort == "relevance":
        views.sort(key=lambda v: (-v["relevance"], v["job"]["deadline"]))
    elif sort == "recent":
        views.sort(key=lambda v: v["job"].get("publishedAt") or v["job"]["openDate"], reverse=True)
    else:
        views.sort(key=lambda v: v["job"]["deadline"])
    return slice_page(views, page, page_size), len(views)


def list_for_staff(db: Session, user: User, f: dict, page: int, page_size: int) -> tuple[list[dict], int]:
    ensure_permission(db, user, *STAFF_JOB_PERMS)
    q = select(Job).join(Company)
    status = f.get("status")
    if status and status != "all":
        q = q.where(Job.status == status)
    archived = f.get("archived") or "exclude"
    if archived == "exclude":
        q = q.where(Job.archived_at.is_(None))
    elif archived == "only":
        q = q.where(Job.archived_at.is_not(None))
    q = _apply_common_filters(q, f)
    sort = f.get("sort") or "deadline"
    q = q.order_by(Job.updated_at.desc() if sort == "recent" else Job.deadline.asc(), Job.id.desc())
    jobs, total = paginate(db, q, page, page_size)
    return [job_view(j, applicantCount=applicant_count(db, j.id)) for j in jobs], total


def get_job(db: Session, user: User, job_id: int) -> Job:
    """A job the user may see (students never see drafts)."""
    job = db.get(Job, job_id)
    if not job:
        raise NotFound("Job not found.")
    if is_staff(user):
        ensure_permission(db, user, *STAFF_JOB_PERMS)
    elif job.status == JobStatus.DRAFT:
        raise NotFound("Job not found.")
    return job


def job_detail(db: Session, user: User, job_id: int) -> dict:
    job = get_job(db, user, job_id)
    if is_staff(user):
        return job_view(job, applicantCount=applicant_count(db, job.id))
    return student_job_view(db, student_of(db, user), job)


def toggle_save(db: Session, user: User, job_id: int) -> bool:
    student = student_of(db, user)
    job = get_job(db, user, job_id)
    row = db.get(SavedJob, (student.id, job.id))
    if row:
        db.delete(row)
        saved = False
    else:
        db.add(SavedJob(student_id=student.id, job_id=job.id))
        saved = True
    db.commit()
    return saved
