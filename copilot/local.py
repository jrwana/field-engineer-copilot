"""OpenAI-compatible backend: a self-hosted vLLM server, or OpenAI's hosted API.

The agent loop is written against Anthropic's response shape. This adapter
translates requests to OpenAI chat-completions format and translates responses
back, so the loop, tools, grounding check and eval are identical for every
backend. That's what makes a local-vs-hosted comparison fair.

Raw HTTP on purpose: no extra SDK dependency for a backend used only in testing.

Server requirement: vLLM must be started with tool calling enabled, e.g.
    vllm serve openai/gpt-oss-20b --enable-auto-tool-choice --tool-call-parser openai
"""

import json
import os
import urllib.error
import urllib.request
from types import SimpleNamespace as NS

DEFAULT_ENDPOINT = "http://localhost:8000/v1"
OPENAI_ENDPOINT = "https://api.openai.com/v1"
_STOP = {"tool_calls": "tool_use", "stop": "end_turn", "length": "max_tokens"}


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["description"],
                          "parameters": t["input_schema"]}} for t in tools]


def _get(block, key):
    return block[key] if isinstance(block, dict) else getattr(block, key)


def to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    out = [{"role": "system", "content": system}]
    for m in messages:
        content = m["content"]
        if isinstance(content, str):
            out.append({"role": m["role"], "content": content})
        elif m["role"] == "assistant":
            texts = [_get(b, "text") for b in content if _get(b, "type") == "text"]
            calls = [{"id": _get(b, "id"), "type": "function",
                      "function": {"name": _get(b, "name"),
                                   "arguments": json.dumps(_get(b, "input"))}}
                     for b in content if _get(b, "type") == "tool_use"]
            msg = {"role": "assistant", "content": "\n".join(texts) or None}
            if calls:
                msg["tool_calls"] = calls
            out.append(msg)
        else:  # user turn carrying tool results
            for b in content:
                if _get(b, "type") == "tool_result":
                    out.append({"role": "tool", "tool_call_id": _get(b, "tool_use_id"),
                                "content": _get(b, "content")})
                elif _get(b, "type") == "text":
                    out.append({"role": "user", "content": _get(b, "text")})
    return out


def from_openai_response(data: dict) -> NS:
    choice = data["choices"][0]
    msg = choice["message"]
    content = []
    if msg.get("content"):
        content.append(NS(type="text", text=msg["content"]))
    for call in msg.get("tool_calls") or []:
        try:
            args = json.loads(call["function"]["arguments"] or "{}")
        except json.JSONDecodeError:
            args = {"_invalid_json": call["function"]["arguments"][:500]}
        content.append(NS(type="tool_use", id=call["id"], name=call["function"]["name"],
                          input=args))
    stop = _STOP.get(choice.get("finish_reason"), "end_turn")
    if stop == "end_turn" and any(b.type == "tool_use" for b in content):
        stop = "tool_use"  # some parsers report "stop" even when they emitted calls
    usage = data.get("usage") or {}
    return NS(content=content, stop_reason=stop,
              usage=NS(input_tokens=usage.get("prompt_tokens", 0),
                       output_tokens=usage.get("completion_tokens", 0),
                       cache_read_input_tokens=0, cache_creation_input_tokens=0))


class LocalClient:
    """Drop-in for the slice of the Anthropic client the agent uses."""

    def __init__(self, model: str, endpoint: str | None = None, timeout: float = 300,
                 api_key: str | None = None):
        self.model = model
        self.endpoint = (endpoint or os.getenv("LOCAL_LLM_ENDPOINT", DEFAULT_ENDPOINT)).rstrip("/")
        self.timeout = timeout
        self.api_key = api_key  # set for OpenAI's hosted API; vLLM needs none
        self.beta = NS(messages=NS(create=self.create))

    def create(self, *, max_tokens: int, system: str, tools: list, messages: list,
               output_config: dict | None = None, **_ignored) -> NS:
        # Anthropic-only parameters (cache_control, betas, fallbacks) are ignored.
        body = {
            "model": self.model,
            "messages": to_openai_messages(system, messages),
            "tools": to_openai_tools(tools),
            "tool_choice": "auto",
        }
        if self.api_key:
            # OpenAI reasoning models take max_completion_tokens and only the default temperature.
            body["max_completion_tokens"] = min(max_tokens, 8192)
        else:
            body["max_tokens"] = min(max_tokens, 8192)
            body["temperature"] = 0.0
        effort = (output_config or {}).get("effort")
        if self.api_key:
            # OpenAI's chat-completions endpoint rejects tools combined with any reasoning effort
            # other than "none" (it wants the Responses API for that), so hosted runs don't reason.
            body["reasoning_effort"] = "none"
        elif effort in ("low", "medium", "high"):
            body["reasoning_effort"] = effort  # gpt-oss reasoning models accept this
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib.request.Request(f"{self.endpoint}/chat/completions",
                                     data=json.dumps(body).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # raises OSError subclasses
                return from_openai_response(json.loads(r.read()))
        except urllib.error.HTTPError as e:  # surface the server's reason, not just the status
            detail = e.read().decode(errors="replace")[:500]
            raise OSError(f"HTTP {e.code} from {self.endpoint}: {detail}") from e
