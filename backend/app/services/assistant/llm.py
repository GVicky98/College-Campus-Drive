"""LLM provider configuration and adapters.

Two adapters cover practically every LLM service:
  * `anthropic`  — Claude models through the official `anthropic` SDK;
  * everything else speaks the OpenAI chat-completions protocol through the official `openai` SDK
    (OpenAI, Gemini, Mistral, Groq, DeepSeek, OpenRouter, Together, local Ollama, or any compatible server).
The API key lives only in the server's environment. It is never sent to the browser, the prompt or a log.
"""
import logging
from dataclasses import dataclass

from ...config import get_settings

log = logging.getLogger("campus")

NOT_CONFIGURED_MESSAGE = "The AI assistant is not configured on this server. Ask an administrator to set an LLM provider and key."


@dataclass(frozen=True)
class ProviderSpec:
    adapter: str                 # "anthropic" | "openai"
    base_url: str | None = None  # preset endpoint for OpenAI-protocol services
    needs_key: bool = True
    needs_base_url: bool = False
    default_model: str | None = None


PROVIDERS = {
    "anthropic": ProviderSpec("anthropic", default_model="claude-opus-5-5"),
    "openai": ProviderSpec("openai"),
    "gemini": ProviderSpec("openai", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "mistral": ProviderSpec("openai", "https://api.mistral.ai/v1"),
    "groq": ProviderSpec("openai", "https://api.groq.com/openai/v1"),
    "deepseek": ProviderSpec("openai", "https://api.deepseek.com"),
    "openrouter": ProviderSpec("openai", "https://openrouter.ai/api/v1"),
    "together": ProviderSpec("openai", "https://api.together.xyz/v1"),
    "ollama": ProviderSpec("openai", "http://localhost:11434/v1", needs_key=False),
    "openai_compatible": ProviderSpec("openai", needs_base_url=True),
}


@dataclass(frozen=True)
class ResolvedConfig:
    provider: str
    adapter: str
    api_key: str
    model: str
    base_url: str | None


def resolve() -> ResolvedConfig | None:
    """The usable configuration, or None (the reason is logged, never shown to users)."""
    s = get_settings()
    name = (s.llm_provider or "").strip().lower()
    spec = PROVIDERS.get(name)
    if not spec:
        log.info("Assistant not configured: unknown LLM_PROVIDER %r", name)
        return None
    key = s.llm_api_key.strip() or ("not-needed" if not spec.needs_key else "")
    model = s.llm_model.strip() or (spec.default_model or "")
    base_url = s.llm_base_url.strip() or spec.base_url
    missing = [n for n, ok in (("LLM_API_KEY", key), ("LLM_MODEL", model), ("LLM_BASE_URL", base_url or not spec.needs_base_url)) if not ok]
    if missing:
        log.info("Assistant not configured: missing %s", ", ".join(missing))
        return None
    return ResolvedConfig(name, spec.adapter, key, model, base_url)


def provider_status() -> dict:
    cfg = resolve()
    if not cfg:
        return {"available": False, "provider": get_settings().llm_provider, "reason": NOT_CONFIGURED_MESSAGE}
    return {"available": True, "provider": cfg.provider, "model": cfg.model}


# ---------------------------------------------------------------- neutral types shared by both adapters
@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class LLMReply:
    text: str
    tool_calls: list
    raw: object = None  # provider content, replayed only inside the same chat turn


class LLMError(Exception):
    """kind: not_configured | timeout | rate_limit | auth | unavailable | refused | bad_response"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message


CUT_SHORT = "\n\n_(The answer was cut short. Ask me to continue or narrow the question.)_"

# A conversation turn is one of:
#   {"role": "user", "text": str}
#   {"role": "assistant", "text": str, "tool_calls": [ToolCall], "raw": object | None}
#   {"role": "tool", "results": [{"id", "content": str, "is_error": bool}]}


class AnthropicProvider:
    def __init__(self, cfg: ResolvedConfig):
        import anthropic
        s = get_settings()
        self.sdk = anthropic
        self.cfg = cfg
        self.client = anthropic.Anthropic(api_key=cfg.api_key, base_url=cfg.base_url or None,
                                          timeout=s.llm_timeout_seconds, max_retries=s.llm_max_retries)

    def _messages(self, turns: list[dict]) -> list[dict]:
        out = []
        for t in turns:
            if t["role"] == "user":
                out.append({"role": "user", "content": t["text"]})
            elif t["role"] == "assistant":
                if t.get("raw") is not None:
                    content = t["raw"]  # replay every block unchanged (thinking blocks included)
                else:
                    content = ([{"type": "text", "text": t["text"]}] if t.get("text") else []) + [
                        {"type": "tool_use", "id": c.id, "name": c.name, "input": c.args} for c in t.get("tool_calls", [])]
                out.append({"role": "assistant", "content": content or t.get("text") or ""})
            else:  # all tool results go back in ONE user message
                out.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": r["id"], "content": r["content"], "is_error": r["is_error"]}
                    for r in t["results"]]})
        return out

    def complete(self, system: str, turns: list[dict], tools: list[ToolSpec], max_tokens: int, allow_tools: bool = True) -> LLMReply:
        s = get_settings()
        kwargs = {"model": self.cfg.model, "max_tokens": max_tokens, "system": system, "messages": self._messages(turns)}
        if tools:
            kwargs["tools"] = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]
            if not allow_tools:  # final round: tools stay defined (the history uses them) but must not be called
                kwargs["tool_choice"] = {"type": "none"}
        if s.llm_effort:
            kwargs["output_config"] = {"effort": s.llm_effort}
        if s.llm_anthropic_fallbacks:
            # Server-side refusal fallback: on a policy decline the API retries on a fallback model in the same call.
            kwargs["extra_body"] = {"fallbacks": s.llm_anthropic_fallbacks}
            kwargs["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
        sdk = self.sdk
        try:
            resp = self.client.messages.create(**kwargs)
        except sdk.APITimeoutError:
            raise LLMError("timeout", "The AI service took too long to answer. Please try again.")
        except (sdk.AuthenticationError, sdk.PermissionDeniedError) as e:
            log.error("LLM auth error: %s", type(e).__name__)
            raise LLMError("auth", NOT_CONFIGURED_MESSAGE)
        except sdk.RateLimitError:
            raise LLMError("rate_limit", "The AI service is busy right now. Please try again in a moment.")
        except (sdk.APIConnectionError, sdk.InternalServerError):
            raise LLMError("unavailable", "The AI service is unavailable right now. Please try again shortly.")
        except sdk.APIStatusError as e:
            log.error("LLM API error: HTTP %s (request id %s)", e.status_code, getattr(e, "request_id", None))
            raise LLMError("unavailable", "The AI service could not answer this request. Please try again.")
        if resp.stop_reason == "refusal":
            raise LLMError("refused", "The AI service declined to answer this request.")
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [ToolCall(b.id, b.name, b.input if isinstance(b.input, dict) else {"_unparseable_arguments": True})
                 for b in resp.content if b.type == "tool_use"]
        if resp.stop_reason == "max_tokens" and not calls:
            text += CUT_SHORT
        raw = [b.model_dump(mode="json", exclude_none=True) for b in resp.content]
        return LLMReply(text, calls, raw)


class OpenAIProvider:
    def __init__(self, cfg: ResolvedConfig):
        import openai
        s = get_settings()
        self.sdk = openai
        self.cfg = cfg
        self.client = openai.OpenAI(api_key=cfg.api_key, base_url=cfg.base_url or None,
                                    timeout=s.llm_timeout_seconds, max_retries=s.llm_max_retries)

    def _messages(self, system: str, turns: list[dict]) -> list[dict]:
        import json
        out = [{"role": "system", "content": system}]
        for t in turns:
            if t["role"] == "user":
                out.append({"role": "user", "content": t["text"]})
            elif t["role"] == "assistant":
                m = {"role": "assistant", "content": t.get("text") or (None if t.get("tool_calls") else "")}
                if t.get("tool_calls"):
                    m["tool_calls"] = [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.args)}}
                                       for c in t["tool_calls"]]
                out.append(m)
            else:
                out.extend({"role": "tool", "tool_call_id": r["id"], "content": r["content"]} for r in t["results"])
        return out

    def complete(self, system: str, turns: list[dict], tools: list[ToolSpec], max_tokens: int, allow_tools: bool = True) -> LLMReply:
        import json
        s = get_settings()
        kwargs = {"model": self.cfg.model, "messages": self._messages(system, turns)}
        # api.openai.com takes max_completion_tokens; most compatible servers still expect max_tokens.
        kwargs["max_tokens" if self.cfg.base_url else "max_completion_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.input_schema}}
                               for t in tools]
            if not allow_tools:
                kwargs["tool_choice"] = "none"
        if s.llm_effort:
            kwargs["reasoning_effort"] = s.llm_effort
        sdk = self.sdk
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except sdk.APITimeoutError:
            raise LLMError("timeout", "The AI service took too long to answer. Please try again.")
        except (sdk.AuthenticationError, sdk.PermissionDeniedError) as e:
            log.error("LLM auth error: %s", type(e).__name__)
            raise LLMError("auth", NOT_CONFIGURED_MESSAGE)
        except sdk.RateLimitError:
            raise LLMError("rate_limit", "The AI service is busy right now. Please try again in a moment.")
        except (sdk.APIConnectionError, sdk.InternalServerError):
            raise LLMError("unavailable", "The AI service is unavailable right now. Please try again shortly.")
        except sdk.APIStatusError as e:
            log.error("LLM API error: HTTP %s", e.status_code)
            raise LLMError("unavailable", "The AI service could not answer this request. Please try again.")
        if not resp.choices:
            raise LLMError("bad_response", "The AI service returned an empty answer.")
        choice = resp.choices[0]
        if choice.finish_reason == "content_filter":
            raise LLMError("refused", "The AI service declined to answer this request.")
        calls = []
        for i, c in enumerate(choice.message.tool_calls or []):
            try:
                args = json.loads(c.function.arguments or "{}")
                if not isinstance(args, dict):
                    raise ValueError
            except ValueError:
                args = {"_unparseable_arguments": True}
            calls.append(ToolCall(c.id or f"call_{i}", c.function.name, args))
        text = choice.message.content or ""
        if choice.finish_reason == "length" and not calls:
            text += CUT_SHORT
        return LLMReply(text, calls)


def get_provider():
    """The configured provider, or None. Tests replace this function with a scripted fake."""
    cfg = resolve()
    if not cfg:
        return None
    return AnthropicProvider(cfg) if cfg.adapter == "anthropic" else OpenAIProvider(cfg)
