"""Scheduling interviews.

Candidates must be shortlisted / interview applicants of that job; nobody may be in two overlapping scheduled
rounds. Status: scheduled -> completed | no_show (only once the start time has passed), scheduled -> cancelled
(any time); every other state is final. Interviews never change application status.
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import utcnow
from ..enums import ApplicationStatus, InterviewStatus, JobStatus, NotificationKind
from ..errors import Conflict, NotFound, ValidationFailed
from ..models import Application, Interview, Job, User
from . import audit
from .notifications import notify


def _interview(db: Session, interview_id: int) -> Interview:
    i = db.get(Interview, interview_id)
    if not i:
        raise NotFound("Interview not found.")
    return i


def _candidates(db: Session, job: Job, ids: list[int]) -> list[Application]:
    apps = []
    for app_id in dict.fromkeys(ids):
        a = db.get(Application, app_id)
        if not a:
            raise ValidationFailed(f"Application {app_id} does not exist.", field="applicationIds")
        if a.job_id != job.id:
            raise ValidationFailed(f"{a.student.user.name} did not apply to this job.", field="applicationIds")
        if a.status not in (ApplicationStatus.SHORTLISTED, ApplicationStatus.INTERVIEW):
            raise ValidationFailed(f"{a.student.user.name} is {a.status}; only shortlisted or interview-stage applicants can be scheduled.",
                                   field="applicationIds")
        apps.append(a)
    return apps


def _check_clash(db: Session, apps: list[Application], start, minutes: int, ignore_id: int | None) -> None:
    end = start + timedelta(minutes=minutes)
    others = db.scalars(select(Interview).where(
        Interview.status == InterviewStatus.SCHEDULED,
        Interview.scheduled_at < end, Interview.scheduled_at > start - timedelta(hours=10),
        Interview.id != (ignore_id or 0),
    )).unique().all()
    student_ids = {a.student_id: a for a in apps}
    for other in others:
        if other.scheduled_at + timedelta(minutes=other.duration_mins) <= start:
            continue
        for c in other.candidates:
            if c.student_id in student_ids:
                raise Conflict(f"{c.student.user.name} already has {other.round_name} for {other.job.company.name} at that time.")


def save(db: Session, user: User, body, interview_id: int | None = None) -> Interview:
    if interview_id:
        i = _interview(db, interview_id)
        if i.status != InterviewStatus.SCHEDULED:
            raise Conflict("Only a scheduled interview can be edited.")
        if body.job_id != i.job_id:
            raise ValidationFailed("The job of an interview cannot change.", field="jobId")
        if body.at != i.scheduled_at and body.at <= utcnow():
            raise ValidationFailed("Choose a time in the future.", field="at")
        job = i.job
    else:
        job = db.get(Job, body.job_id)
        if not job or job.status not in (JobStatus.PUBLISHED, JobStatus.CLOSED) or job.archived_at:
            raise ValidationFailed("Interviews can be scheduled for published or closed jobs only.", field="jobId")
        if body.at <= utcnow():
            raise ValidationFailed("Choose a time in the future.", field="at")
        i = Interview(job_id=job.id, status=InterviewStatus.SCHEDULED)
        db.add(i)
    apps = _candidates(db, job, body.application_ids)
    _check_clash(db, apps, body.at, body.duration_mins, interview_id)
    i.round_name, i.scheduled_at, i.duration_mins, i.location = body.round, body.at, body.duration_mins, body.location
    i.candidates = apps
    i.notified = False
    db.flush()
    audit.record(db, "interview.update" if interview_id else "interview.create", f"Interview {i.id} · {job.title}",
                 actor=user, reason=f"{len(apps)} candidate(s) at {i.scheduled_at:%Y-%m-%d %H:%M} UTC")
    db.commit()
    return i


def set_status(db: Session, user: User, interview_id: int, status: str) -> Interview:
    i = _interview(db, interview_id)
    target = InterviewStatus(status)
    if i.status != InterviewStatus.SCHEDULED:
        raise Conflict(f"This interview is already {i.status.replace('_', ' ')}.")
    if target == InterviewStatus.SCHEDULED:
        return i
    if target in (InterviewStatus.COMPLETED, InterviewStatus.NO_SHOW) and i.scheduled_at > utcnow():
        raise Conflict("An interview can be marked completed or no-show only after it starts.")
    if target == InterviewStatus.CANCELLED and i.notified:
        for a in i.candidates:
            notify(db, a.student.user_id, f"Interview cancelled — {i.job.company.name}",
                   f"{i.round_name} for {i.job.title} has been cancelled.", NotificationKind.INTERVIEW, f"/student/applications/{a.id}")
    i.status = target
    audit.record(db, f"interview.{target}", f"Interview {i.id} · {i.job.title}", actor=user)
    db.commit()
    return i


def notify_candidates(db: Session, user: User, interview_id: int) -> int:
    i = _interview(db, interview_id)
    if i.status != InterviewStatus.SCHEDULED:
        raise Conflict("Only a scheduled interview can be announced.")
    for a in i.candidates:
        notify(db, a.student.user_id, f"Interview scheduled — {i.job.company.name}",
               f"{i.round_name} for {i.job.title} on {i.scheduled_at:%d %b %Y, %H:%M} UTC at {i.location}.",
               NotificationKind.INTERVIEW, f"/student/applications/{a.id}")
    i.notified = True
    audit.record(db, "interview.notify", f"Interview {i.id}", actor=user, reason=f"{len(i.candidates)} candidate(s)")
    db.commit()
    return len(i.candidates)
