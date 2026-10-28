"""The tool framework: registration, permission checks at call time, argument validation and the run context.

Rules every tool follows:
  * identity comes only from `ctx.user` — tools never take a user id, role or permission argument;
  * unknown arguments are rejected (extra="forbid");
  * each tool declares the roles and permissions it needs; they are re-checked on every call and denials are audited;
  * tools return allow-listed fields only, reusing the normal service layer (and its rules);
  * `prepare_*` tools never change anything: they record a proposal the user must confirm.
"""
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy.orm import Session

from ...enums import AuditResult, RoleName
from ...errors import ApiError, Forbidden
from ...models import User
from .. import audit
from .llm import ToolSpec

log = logging.getLogger("campus")
STAFF = (RoleName.FACULTY, RoleName.ADMIN)
ALL = (RoleName.STUDENT, RoleName.FACULTY, RoleName.ADMIN)
RESULT_LIMIT = 14000
MAX_CHARTS, MAX_REPORTS = 3, 2


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NoArgs(Args):
    pass


@dataclass
class Context:
    db: Session
    user: User
    untrusted_seen: bool = False
    proposals: list = field(default_factory=list)
    charts: list = field(default_factory=list)
    reports: list = field(default_factory=list)
    job_ids: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    trace: list = field(default_factory=list)

    def remember_jobs(self, ids):
        for i in ids:
            if str(i) not in self.job_ids and len(self.job_ids) < 6:
                self.job_ids.append(str(i))


@dataclass
class Tool:
    name: str
    description: str
    args: type[Args]
    handler: Callable[[Context, Args], dict]
    roles: tuple = ALL
    perms: tuple = ()
    mode: str = "any"  # any | all
    prepares: bool = False

    def allowed(self, user: User) -> bool:
        if user.role_name not in self.roles:
            return False
        if not self.perms:
            return True
        held = [user.can(p) for p in self.perms]
        return any(held) if self.mode == "any" else all(held)


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, args: type[Args] = NoArgs, *, roles=ALL, perms=(), mode="any", prepares=False):
    def register(fn):
        REGISTRY[name] = Tool(name, description, args, fn, tuple(roles), tuple(perms), mode, prepares)
        return fn
    return register


def plain_schema(model: type[BaseModel]) -> dict:
    """A JSON schema every provider accepts: no titles, $refs inlined, Optional[X] collapsed to X."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def clean(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return clean(defs[node["$ref"].split("/")[-1]])
            node = {k: clean(v) for k, v in node.items() if k != "title"}
            any_of = node.get("anyOf")
            if any_of and len(any_of) == 2 and {"type": "null"} in any_of:
                inner = next(x for x in any_of if x != {"type": "null"})
                node.pop("anyOf")
                if node.get("default") is None:
                    node.pop("default", None)
                node = {**inner, **node}
            return node
        if isinstance(node, list):
            return [clean(x) for x in node]
        return node

    out = clean(schema)
    out.setdefault("properties", {})
    out["additionalProperties"] = False
    return out


def specs_for(user: User) -> list[ToolSpec]:
    return [ToolSpec(t.name, t.description, plain_schema(t.args)) for t in REGISTRY.values() if t.allowed(user)]


def run_tool(ctx: Context, name: str, raw_args: dict) -> dict:
    t = REGISTRY.get(name)
    if not t:
        ctx.trace.append({"tool": name, "args": {}, "status": "denied"})
        return {"error": "unknown_tool", "message": f"There is no tool called {name}."}
    if not t.allowed(ctx.user):
        audit.record(ctx.db, "assistant.tool", name, actor=ctx.user, result=AuditResult.DENIED, reason="Not permitted")
        ctx.db.commit()
        ctx.trace.append({"tool": name, "args": {}, "status": "denied"})
        return {"error": "not_permitted", "message": "You do not have permission to use this capability. Do not try to work around it."}
    if t.prepares and ctx.untrusted_seen:
        ctx.trace.append({"tool": name, "args": {}, "status": "denied"})
        return {"error": "blocked", "message": "Actions cannot be prepared in the same reply that read document text. "
                "Summarise the document and ask the user to request the action separately."}
    try:
        args = t.args.model_validate(raw_args or {})
    except ValidationError as e:
        ctx.trace.append({"tool": name, "args": {}, "status": "error"})
        return {"error": "invalid_arguments", "message": str(e)[:400]}
    trace = {"tool": name, "args": args.model_dump(exclude_none=True, mode="json"), "status": "ok"}
    ctx.trace.append(trace)
    try:
        out = t.handler(ctx, args)
    except Forbidden as e:
        ctx.db.rollback()
        audit.record(ctx.db, "assistant.tool", name, actor=ctx.user, result=AuditResult.DENIED, reason=e.message)
        ctx.db.commit()
        trace["status"] = "denied"
        return {"error": "not_permitted", "message": e.message}
    except ApiError as e:
        ctx.db.rollback()
        trace["status"] = "error"
        return {"error": e.code, "message": e.message}
    except Exception:  # never leak internals to the model
        ctx.db.rollback()
        log.exception("Assistant tool %s failed", name)
        trace["status"] = "error"
        return {"error": "tool_failed", "message": "That lookup failed. Try a different question."}
    if len(json.dumps(out, default=str)) > RESULT_LIMIT:
        return {"error": "result_too_large", "message": "The result was too large. Ask a narrower question or use a smaller limit."}
    return out


def propose(ctx: Context, kind: str, title: str, details: list[tuple[str, str]], payload: dict, *,
            description: str = "", destructive: bool = False) -> dict:
    """Record a change for the user to confirm. Only one proposal per reply."""
    if ctx.proposals:
        return {"error": "one_action_per_reply", "message": "Only one change can be prepared per reply. Ask the user to confirm this one first."}
    ctx.proposals.append({
        "kind": kind, "title": title[:200], "description": description[:500], "destructive": destructive,
        "details": [{"label": k, "value": str(v)} for k, v in details], "payload": payload,
    })
    return {"status": "awaiting_user_confirmation", "summary": title, "details": {k: str(v) for k, v in details},
            "note": "A confirmation card is shown to the user. Nothing has changed yet. Do not say it is done."}


def cannot(message: str, code: str = "cannot_prepare", **extra) -> dict:
    return {"error": code, "message": message, **extra}
