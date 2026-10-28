"""/assistant: chat, conversations and confirmation of proposed actions. Everything is scoped to the signed-in user."""
from fastapi import APIRouter
from pydantic import Field

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..ratelimit import hit
from ..schemas.common import CamelModel, ok
from ..services.assistant import actions, conversations, orchestrator, suggestions
from ..services.assistant.llm import provider_status

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatIn(CamelModel):
    conversation_id: int | None = Field(None, ge=1)
    message: str = Field(max_length=20000)


@router.get("/status")
def status(user: CurrentUser):
    return ok(provider_status())


@router.get("/suggestions")
def get_suggestions(user: CurrentUser):
    return ok(suggestions.for_user(user))


@router.get("/conversations")
def list_conversations(user: CurrentUser, db: Db):
    return ok(conversations.list_mine(db, user))


@router.post("/conversations", status_code=201)
def create_conversation(user: CurrentUser, db: Db):
    return ok(conversations.conversation_dict(db, conversations.create(db, user)))


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, user: CurrentUser, db: Db):
    return ok(conversations.conversation_dict(db, conversations.get_owned(db, user, conversation_id)))


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, user: CurrentUser, db: Db):
    conversations.archive(db, user, conversation_id)
    return ok({"ok": True})


@router.post("/chat")
def chat(body: ChatIn, user: CurrentUser, db: Db):
    hit(f"assistant:{user.id}", get_settings().assistant_chat_rate_limit)  # per user, not per IP
    return ok(orchestrator.chat(db, user, body.message, body.conversation_id))


@router.post("/actions/{action_id}/confirm")
def confirm(action_id: int, user: CurrentUser, db: Db):
    return ok(actions.action_dict(actions.confirm(db, user, action_id)))


@router.post("/actions/{action_id}/reject")
def reject(action_id: int, user: CurrentUser, db: Db):
    return ok(actions.action_dict(actions.reject(db, user, action_id)))
