"""A scripted stand-in for the LLM, so assistant tests run without a network or API key."""
from app.services.assistant.llm import LLMReply, ToolCall


def say(text: str) -> LLMReply:
    return LLMReply(text, [])


def call(name: str, args: dict | None = None, text: str = "") -> LLMReply:
    return LLMReply(text, [ToolCall(f"call_{name}", name, args or {})])


def calls(*pairs) -> LLMReply:
    return LLMReply("", [ToolCall(f"call_{i}", n, a) for i, (n, a) in enumerate(pairs)])


class ScriptedProvider:
    """Replays `steps` in order. A step is an LLMReply, an Exception (raised), or a callable(request) -> LLMReply."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.requests = []

    def complete(self, system, turns, tools, max_tokens, allow_tools=True):
        self.requests.append({"system": system, "turns": [dict(t) for t in turns], "tools": [t.name for t in tools],
                              "allow_tools": allow_tools})
        step = self.steps.pop(0) if self.steps else LLMReply("Done.", [])
        if isinstance(step, Exception):
            raise step
        return step(self.requests[-1]) if callable(step) else step

    def last_tool_result(self, index: int = 0):
        import json
        for t in reversed(self.requests[-1]["turns"]):
            if t["role"] == "tool":
                return json.loads(t["results"][index]["content"])
        return None
