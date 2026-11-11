from conftest import response, text, tool

from copilot.agent import Copilot, check_grounding

DRAFT = {
    "answers": [{"question": "power?", "answer": "8.9 W typical.", "sources": ["spec:HX-R6016"],
                 "confidence": "high"}],
    "escalations": [],
    "reply_email": "Hi Priya, the HX-R6016 draws 8.9 W typical.",
}


def test_happy_path_tool_then_draft(fake):
    client = fake([
        response([tool("lookup_product", {"part_numbers": ["HX-R6016"]})]),
        response([tool("submit_draft", DRAFT, "tu_2")]),
    ])
    res = Copilot(client=client).run("What is the power of the HX-R6016?")
    assert res.status == "draft"
    assert res.tools_called == ["lookup_product"]
    assert res.ungrounded_citations == []
    assert res.cost_usd > 0
    # the tool result was sent back in one user message, matched by id
    sent = client.calls[1]["messages"][-1]["content"][0]
    assert sent["type"] == "tool_result" and sent["tool_use_id"] == "tu_1"


def test_request_shape(fake):
    client = fake([response([tool("submit_draft", DRAFT)])])
    Copilot(client=client, effort="low").run("x")
    kw = client.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"] == {"effort": "low"}
    assert kw["fallbacks"] == "default" and kw["betas"] == ["server-side-fallback-2026-07-01"]
    assert "tool_choice" not in kw  # forced tool_choice is rejected on this model


def test_haiku_gets_no_fallback_params(fake):
    client = fake([response([tool("submit_draft", DRAFT)])])
    Copilot(client=client, model="claude-haiku-5-5").run("x")
    assert "fallbacks" not in client.calls[0] and "betas" not in client.calls[0]


def test_citation_never_retrieved_is_flagged(fake):
    client = fake([response([tool("submit_draft", DRAFT)])])  # cites without looking up
    res = Copilot(client=client).run("x")
    assert res.ungrounded_citations == ["spec:HX-R6016"]


def test_nudge_once_then_give_up(fake):
    client = fake([response([text("Here you go")], "end_turn"),
                   response([text("Still no tool")], "end_turn")])
    res = Copilot(client=client).run("x")
    assert res.status == "no_draft"
    assert any(e["type"] == "nudge" for e in res.trace)


def test_nudge_recovers(fake):
    client = fake([response([text("Answer in prose")], "end_turn"),
                   response([tool("submit_draft", {**DRAFT, "answers": []})])])
    assert Copilot(client=client).run("x").status == "draft"


def test_refusal_stops(fake):
    client = fake([response([], "refusal")])
    assert Copilot(client=client).run("x").status == "refusal"


def test_max_turns_cap(fake):
    loop = [response([tool("search_docs", {"query": "x"}, f"tu_{i}")]) for i in range(3)]
    res = Copilot(client=fake(loop), max_turns=3).run("x")
    assert res.status == "max_turns" and len(res.tools_called) == 3


def test_check_grounding():
    assert check_grounding(DRAFT, {"spec:HX-R6016"}) == []
    assert check_grounding(DRAFT, set()) == ["spec:HX-R6016"]


def test_malformed_draft_gets_one_more_chance(fake):
    bad = {"answers": [{"question": "q", "answer": "a"}], "escalations": [], "reply_email": ""}
    client = fake([response([tool("submit_draft", bad)]),
                   response([tool("submit_draft", {**DRAFT, "answers": []}, "tu_2")])])
    res = Copilot(client=client).run("x")
    assert res.status == "draft"
    assert any(e["type"] == "invalid_draft" for e in res.trace)
    err = client.calls[1]["messages"][-1]["content"][0]
    assert err["is_error"] and "Each answer needs" in err["content"]


def test_unreachable_local_server_is_error_not_crash(monkeypatch):
    import urllib.request
    def boom(*a, **k):
        raise urllib.error.URLError("timed out")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    res = Copilot(model="local:openai/gpt-oss-20b").run("x")
    assert res.status == "error" and "timed out" in res.error and res.cost_usd == 0


def test_doc_level_citation_grounded_but_invented_section_not():
    d = {"answers": [{"question": "q", "answer": "a", "sources": ["TG-THERMAL", "AN-204#5"],
                      "confidence": "high"}], "escalations": [], "reply_email": ""}
    assert check_grounding(d, {"TG-THERMAL#2", "AN-204#2"}) == ["AN-204#5"]
