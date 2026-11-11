import json
import urllib.request
from types import SimpleNamespace as NS

from copilot.agent import Copilot
from copilot.local import from_openai_response, to_openai_messages, to_openai_tools
from copilot.tools import TOOLS


def test_tools_translate_to_functions():
    fns = to_openai_tools(TOOLS)
    assert fns[0]["type"] == "function" and fns[0]["function"]["name"] == "lookup_product"
    assert "strict" not in fns[-1]["function"]


def test_message_translation_round_trip():
    msgs = [
        {"role": "user", "content": "Customer email: hi"},
        {"role": "assistant", "content": [NS(type="text", text="Looking up."),
                                          NS(type="tool_use", id="c1", name="search_docs",
                                             input={"query": "SRIS"})]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1",
                                      "content": "[]", "is_error": False}]},
    ]
    out = to_openai_messages("SYS", msgs)
    assert [m["role"] for m in out] == ["system", "user", "assistant", "tool"]
    assert json.loads(out[2]["tool_calls"][0]["function"]["arguments"]) == {"query": "SRIS"}
    assert out[3]["tool_call_id"] == "c1"


def test_response_parsing_tool_call_and_bad_json():
    data = {"choices": [{"finish_reason": "stop", "message": {"content": None, "tool_calls": [
        {"id": "c1", "function": {"name": "lookup_product", "arguments": '{"part_numbers": ["HX-R6016"]}'}},
        {"id": "c2", "function": {"name": "search_docs", "arguments": "{not json"}},
    ]}}], "usage": {"prompt_tokens": 50, "completion_tokens": 7}}
    r = from_openai_response(data)
    assert r.stop_reason == "tool_use"  # corrected from "stop"
    assert r.content[0].input == {"part_numbers": ["HX-R6016"]}
    assert "_invalid_json" in r.content[1].input
    assert r.usage.input_tokens == 50


class _Resp:
    def __init__(self, payload): self.payload = payload
    def read(self): return json.dumps(self.payload).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


def test_full_local_run_with_fake_server(monkeypatch):
    draft = {"answers": [{"question": "power?", "answer": "8.9 W", "sources": ["spec:HX-R6016"],
                          "confidence": "high"}], "escalations": [], "reply_email": "8.9 W."}
    replies = [
        {"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
            {"id": "c1", "function": {"name": "lookup_product",
                                      "arguments": '{"part_numbers": ["HX-R6016"]}'}}]}}]},
        {"choices": [{"finish_reason": "tool_calls", "message": {"content": None, "tool_calls": [
            {"id": "c2", "function": {"name": "submit_draft", "arguments": json.dumps(draft)}}]}}]},
    ]
    sent = []
    def fake_urlopen(req, timeout):
        sent.append(json.loads(req.data))
        return _Resp(replies.pop(0))
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    res = Copilot(model="local:openai/gpt-oss-20b", effort="low").run("Power of HX-R6016?")
    assert res.status == "draft" and res.ungrounded_citations == []
    assert sent[0]["model"] == "openai/gpt-oss-20b" and sent[0]["reasoning_effort"] == "low"
    assert "fallbacks" not in sent[0] and "cache_control" not in sent[0]
    assert sent[1]["messages"][-1]["role"] == "tool"
