"""`python -m app.cli assistant-check [--ping]`: show the assistant configuration (never the key) and each role's tools."""
from ...enums import RoleName
from . import tools_staff, tools_student  # noqa: F401
from .framework import REGISTRY
from .llm import LLMError, get_provider, provider_status, resolve


def run_check(ping: bool = False) -> None:
    status = provider_status()
    print("Assistant:", "configured" if status["available"] else "NOT configured")
    cfg = resolve()
    if cfg:
        print(f"  provider={cfg.provider} adapter={cfg.adapter} model={cfg.model} base_url={cfg.base_url or '(default)'}")
    for role in RoleName:
        names = [t.name for t in REGISTRY.values() if role in t.roles]
        print(f"  {role}: {len(names)} tools")
    if ping and cfg:
        try:
            reply = get_provider().complete("Reply with the single word: ok", [{"role": "user", "text": "ping"}], [], 64)
            print("  ping:", (reply.text or "").strip()[:60] or "(empty reply)")
        except LLMError as e:
            print(f"  ping failed: {e.kind} — {e.message}")
