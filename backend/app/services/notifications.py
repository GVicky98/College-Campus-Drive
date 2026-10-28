"""In-app notifications (e-mail and push delivery are not implemented)."""
from sqlalchemy.orm import Session

from ..enums import NotificationKind
from ..models import Notification


def notify(db: Session, user_id: int, title: str, body: str = "", kind: NotificationKind = NotificationKind.SYSTEM,
           link: str | None = None) -> Notification:
    n = Notification(user_id=user_id, title=title[:200], body=body[:500], kind=kind, link=link)
    db.add(n)
    return n
