"""The agent loop.

Written by hand (not the SDK tool runner) so every step is recorded: which tool,
what input, what came back, tokens and time. That trace feeds the UI, the eval
and the cost numbers.
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass, field

import anthropic

from . import config
from .local import LocalClient
from .prompts import NUDGE, SYSTEM_PROMPT
from .tools import TOOLS, Toolbox

FALLBACK_BETA = "server-side-fallback-2026-07-01"
# Models that accept server-side refusal fallbacks. Haiku 5.5 has none.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}


@dataclass
class RunResult:
    run_id: str
    email: str
    model: str
    effort: str
    status: str  # draft | no_draft | refusal | max_turns | max_tokens | error
    draft: dict | None = None
    trace: list[dict] = field(default_factory=list)
    tools_called: list[str] = field(default_factory=list)
    retrieved: list[str] = field(default_factory=list)
    ungrounded_citations: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    cost_usd: float = 0.0
    latency_s: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _add_usage(total: dict, usage) -> None:
    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                "cache_creation_input_tokens"):
        total[key] = total.get(key, 0) + (getattr(usage, key, 0) or 0)


def estimate_cost(model: str, usage: dict) -> float:
    p = config.PRICES.get(model)
    if not p:
        return 0.0
    return round((usage.get("input_tokens", 0) * p["input"]
                  + usage.get("output_tokens", 0) * p["output"]
                  + usage.get("cache_read_input_tokens", 0) * p["cache_read"]
                  + usage.get("cache_creation_input_tokens", 0) * p["cache_write"]) / 1e6, 5)


_DRAFT_KEYS = {"answers": list, "escalations": list, "reply_email": str}
_ANSWER_KEYS = {"question", "answer", "sources", "confidence"}
_ESC_KEYS = {"question", "category", "route_to", "reason"}


def validate_draft(draft: dict) -> str | None:
    """Claude's strict tool schema guarantees this shape; local models don't.
    Returns an error message for the model, or None if the draft is valid."""
    for key, typ in _DRAFT_KEYS.items():
        if not isinstance(draft.get(key), typ):
            return f"submit_draft needs '{key}' as a {typ.__name__}."
    for a in draft["answers"]:
        if not isinstance(a, dict) or not _ANSWER_KEYS <= a.keys() or not isinstance(a["sources"], list):
            return f"Each answer needs {sorted(_ANSWER_KEYS)}, with sources as a list."
        if a["confidence"] not in ("high", "medium", "low"):
            return "confidence must be high, medium or low."
    for e in draft["escalations"]:
        if not isinstance(e, dict) or not _ESC_KEYS <= e.keys():
            return f"Each escalation needs {sorted(_ESC_KEYS)}."
    return None


def check_grounding(draft: dict, retrieved: set[str]) -> list[str]:
    """Cited source IDs that no tool returned during this run.

    A whole-document ID ("TG-THERMAL") counts as grounded if any of its sections was
    retrieved. A section ID must match exactly, so an invented "AN-204#5" still fails.
    """
    retrieved_docs = {r.split("#")[0] for r in retrieved}
    cited = {s for a in draft.get("answers", []) for s in a.get("sources", [])}
    return sorted(s for s in cited
                  if s not in retrieved and ("#" in s or s not in retrieved_docs))


class Copilot:
    def __init__(self, client=None, model: str = config.MODEL, effort: str = config.EFFORT,
                 max_turns: int = config.MAX_TURNS):
        # "local:<model>" runs on a self-hosted vLLM server; anything else is Claude.
        if client is None:
            client = (LocalClient(model.removeprefix("local:")) if model.startswith("local:")
                      else anthropic.Anthropic())
        self.client = client
        self.model, self.effort, self.max_turns = model, effort, max_turns

    def _call(self, messages: list) -> object:
        extra = {}
        if self.model in FALLBACK_MODELS:
            # on a policy refusal, the API retries on a fallback model in the same call
            extra = {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return self.client.beta.messages.create(
            model=self.model,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            output_config={"effort": self.effort},
            cache_control={"type": "ephemeral"},  # system + tools are identical every call
            **extra,
        )

    def run(self, email: str, on_step=None) -> RunResult:
        """on_step(event_dict) is called after each step, for live UI updates."""
        toolbox = Toolbox()
        res = RunResult(run_id=uuid.uuid4().hex[:12], email=email, model=self.model,
                        effort=self.effort, status="error")
        messages = [{"role": "user", "content": f"Customer email:\n\n{email}"}]
        nudged = False
        start = time.monotonic()

        def log(event: dict):
            event["t"] = round(time.monotonic() - start, 2)
            res.trace.append(event)
            if on_step:
                on_step(event)

        try:
            for _ in range(self.max_turns):
                response = self._call(messages)
                _add_usage(res.usage, response.usage)
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                for b in response.content:
                    if b.type == "text" and b.text.strip():
                        log({"type": "model_text", "text": b.text})

                if response.stop_reason == "refusal":
                    res.status = "refusal"
                    break
                if response.stop_reason == "max_tokens":
                    res.status = "max_tokens"
                    break
                if response.stop_reason == "pause_turn":
                    messages.append({"role": "assistant", "content": response.content})
                    continue

                submit = next((b for b in tool_uses if b.name == "submit_draft"), None)
                if submit:
                    problem = validate_draft(dict(submit.input))
                    if problem is None:
                        res.draft = dict(submit.input)
                        res.status = "draft"
                        log({"type": "submit_draft"})
                        break
                    # malformed draft: tell the model what's wrong and let it retry
                    log({"type": "invalid_draft", "error": problem})
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": b.id, "is_error": True,
                         "content": problem if b is submit else "Not run: fix submit_draft first."}
                        for b in tool_uses]})
                    continue

                if not tool_uses:  # ended its turn without a draft
                    if nudged:
                        res.status = "no_draft"
                        break
                    nudged = True
                    messages.append({"role": "assistant", "content": response.content})
                    messages.append({"role": "user", "content": NUDGE})
                    log({"type": "nudge"})
                    continue

                messages.append({"role": "assistant", "content": response.content})
                results = []
                for b in tool_uses:
                    output, is_error = toolbox.run(b.name, dict(b.input))
                    res.tools_called.append(b.name)
                    log({"type": "tool", "name": b.name, "input": dict(b.input),
                         "output_preview": output[:400], "is_error": is_error})
                    results.append({"type": "tool_result", "tool_use_id": b.id,
                                    "content": output, "is_error": is_error})
                messages.append({"role": "user", "content": results})  # all results in one message
            else:
                res.status = "max_turns"
        except (anthropic.APIError, OSError) as e:  # OSError: local server unreachable
            res.status, res.error = "error", f"{type(e).__name__}: {e}"

        res.latency_s = round(time.monotonic() - start, 2)
        res.retrieved = sorted(toolbox.retrieved)
        if res.draft:
            res.ungrounded_citations = check_grounding(res.draft, toolbox.retrieved)
        res.cost_usd = estimate_cost(self.model, res.usage)
        return res


def save_trace(res: RunResult) -> None:
    out = config.RUNS / "traces"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{res.run_id}.json").write_text(json.dumps(res.to_dict(), indent=2))
