"""Reminders (students only, always owner-scoped)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..enums import JobStatus, ReminderKind
from ..errors import NotFound, ValidationFailed
from ..models import Job, Reminder, User
from ..serializers import reminder_dict
from .common import student_of


def reminder_view(r: Reminder) -> dict:
    out = {"reminder": reminder_dict(r)}
    if r.job:
        out["jobTitle"] = r.job.title
        out["companyName"] = r.job.company.name
    return out


def list_reminders(db: Session, user: User) -> list[dict]:
    s = student_of(db, user)
    rows = db.scalars(select(Reminder).where(Reminder.student_id == s.id).order_by(Reminder.remind_at))
    return [reminder_view(r) for r in rows]


def _owned(db: Session, user: User, reminder_id: int) -> Reminder:
    s = student_of(db, user)
    r = db.get(Reminder, reminder_id)
    if not r or r.student_id != s.id:
        raise NotFound("Reminder not found.")
    return r


def save_reminder(db: Session, user: User, body, reminder_id: int | None = None) -> dict:
    s = student_of(db, user)
    r = _owned(db, user, reminder_id) if reminder_id else Reminder(student_id=s.id)
    if body.job_id is not None:
        job = db.get(Job, body.job_id)
        if not job or job.status == JobStatus.DRAFT:
            raise ValidationFailed("That job does not exist.", field="jobId")
    r.title = body.title
    r.remind_at = body.at
    r.job_id = body.job_id
    r.kind = body.kind or (ReminderKind.DRIVE if body.job_id else ReminderKind.CUSTOM)
    db.add(r)
    db.commit()
    db.refresh(r)
    return reminder_view(r)


def toggle_reminder(db: Session, user: User, reminder_id: int) -> dict:
    r = _owned(db, user, reminder_id)
    r.done = not r.done
    db.commit()
    return reminder_view(r)


def delete_reminder(db: Session, user: User, reminder_id: int) -> None:
    db.delete(_owned(db, user, reminder_id))
    db.commit()
