"""Conversations: owner-scoped CRUD, archive (soft delete) and the retention purge."""
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ...database import utcnow
from ...enums import ActionState
from ...errors import NotFound
from ...models import AssistantAction, Conversation, Message, User
from ...serializers import iso
from .. import audit
from .actions import action_dict


def get_owned(db: Session, user: User, conversation_id: int) -> Conversation:
    c = db.get(Conversation, conversation_id)
    if not c or c.archived_at or c.user_id != user.id:
        if c and c.user_id != user.id:
            audit.deny(db, user, "assistant.conversation", f"Conversation {conversation_id}", "Not the owner")
        raise NotFound("Conversation not found.")
    return c


def list_mine(db: Session, user: User) -> list[dict]:
    counts = dict(db.execute(select(Message.conversation_id, func.count(Message.id)).group_by(Message.conversation_id)).all())
    rows = db.scalars(select(Conversation).where(Conversation.user_id == user.id, Conversation.archived_at.is_(None))
                      .order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(100))
    return [{"id": str(c.id), "title": c.title, "updatedAt": iso(c.updated_at), "count": counts.get(c.id, 0)} for c in rows]


def message_dict(m: Message, action: AssistantAction | None) -> dict:
    out = {"id": str(m.id), "role": m.role, "text": m.text, "at": iso(m.created_at)}
    out.update({k: v for k, v in (m.payload or {}).items() if v})
    if action:
        out["action"] = action_dict(action)
    return out


def conversation_dict(db: Session, c: Conversation) -> dict:
    actions = {a.message_id: a for a in db.scalars(select(AssistantAction).where(AssistantAction.conversation_id == c.id))}
    return {"id": str(c.id), "title": c.title, "updatedAt": iso(c.updated_at),
            "messages": [message_dict(m, actions.get(m.id)) for m in c.messages]}


def create(db: Session, user: User) -> Conversation:
    c = Conversation(user_id=user.id)
    db.add(c)
    db.commit()
    return c


def archive(db: Session, user: User, conversation_id: int) -> None:
    c = get_owned(db, user, conversation_id)
    c.archived_at = utcnow()
    for a in db.scalars(select(AssistantAction).where(AssistantAction.conversation_id == c.id, AssistantAction.state == ActionState.AWAITING)):
        a.state, a.result_message, a.resolved_at = ActionState.CANCELLED, "The conversation was deleted. Nothing was changed.", utcnow()
    audit.record(db, "assistant.conversation.delete", f"Conversation {c.id}", actor=user)
    db.commit()


def purge_archived(db: Session, days: int) -> int:
    """Hard-delete conversations archived more than `days` ago (messages and actions go with them; audit entries stay)."""
    cutoff = utcnow() - timedelta(days=days)
    ids = list(db.scalars(select(Conversation.id).where(Conversation.archived_at.is_not(None), Conversation.archived_at < cutoff)))
    if ids:
        db.execute(delete(AssistantAction).where(AssistantAction.conversation_id.in_(ids)))
        db.execute(delete(Message).where(Message.conversation_id.in_(ids)))
        db.execute(delete(Conversation).where(Conversation.id.in_(ids)))
        db.commit()
    return len(ids)
