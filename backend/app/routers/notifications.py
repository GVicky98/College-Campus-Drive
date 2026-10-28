"""/notifications: always scoped to the signed-in user (another user's id is a 404)."""
from fastapi import APIRouter
from pydantic import StrictBool
from sqlalchemy import select, update

from ..deps import CurrentUser, Db
from ..errors import NotFound
from ..models import Notification, NotificationPreference
from ..schemas.common import CamelModel, ok
from ..serializers import notification_dict

router = APIRouter(prefix="/notifications", tags=["notifications"])


class PrefsIn(CamelModel):
    email: StrictBool
    push: StrictBool
    drive_reminders: StrictBool
    deadline_reminders: StrictBool
    interview_alerts: StrictBool
    offer_updates: StrictBool


def _prefs_dict(p: NotificationPreference) -> dict:
    return {"email": p.email, "push": p.push, "driveReminders": p.drive_reminders, "deadlineReminders": p.deadline_reminders,
            "interviewAlerts": p.interview_alerts, "offerUpdates": p.offer_updates}


def _prefs(db, user) -> NotificationPreference:
    p = db.get(NotificationPreference, user.id)
    if not p:
        p = NotificationPreference(user_id=user.id)
        db.add(p)
        db.flush()
    return p


@router.get("")
def list_notifications(user: CurrentUser, db: Db):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id)
                      .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(200))
    return ok([notification_dict(n) for n in rows])


@router.post("/read-all")
def read_all(user: CurrentUser, db: Db):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)).values(is_read=True))
    db.commit()
    return ok({"ok": True})


@router.post("/{notification_id}/read")
def read_one(notification_id: int, user: CurrentUser, db: Db):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise NotFound("Notification not found.")
    n.is_read = True
    db.commit()
    return ok(notification_dict(n))


@router.get("/preferences")
def get_preferences(user: CurrentUser, db: Db):
    p = _prefs(db, user)
    db.commit()
    return ok(_prefs_dict(p))


@router.put("/preferences")
def save_preferences(body: PrefsIn, user: CurrentUser, db: Db):
    p = _prefs(db, user)
    for field, value in body.model_dump().items():
        setattr(p, field, value)
    db.commit()
    return ok(_prefs_dict(p))
