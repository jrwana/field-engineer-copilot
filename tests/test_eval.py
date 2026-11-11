from copilot.catalog import Catalog
from copilot.search import load_doc_chunks, load_ticket_chunks
from evals.grade import grade
from evals.run import load_cases


def _result(draft, tools=("lookup_product",), ungrounded=()):
    return {"status": "draft", "draft": draft, "tools_called": list(tools),
            "ungrounded_citations": list(ungrounded), "latency_s": 1, "cost_usd": 0}


def _case(**kw):
    base = dict(id="T", category="x", required_tools=[], expected_sources=[], expected_facts=[],
                should_escalate=False, escalation_categories=[], forbidden=[])
    return {**base, **kw}


def test_every_label_points_at_real_data():
    docs = {c.doc_id for c in load_doc_chunks()} | {c.doc_id for c in load_ticket_chunks()}
    specs = {f"spec:{p}" for p in Catalog().part_numbers()}
    for name in ("dev", "heldout"):
        for c in load_cases(name):
            for s in c["expected_sources"]:
                assert s in docs | specs, (c["id"], s)


def test_heldout_is_disjoint_from_dev():
    dev, held = load_cases("dev"), load_cases("heldout")
    assert not {c["id"] for c in dev} & {c["id"] for c in held}
    assert not {c["email"] for c in dev} & {c["email"] for c in held}


def test_heldout_expected_facts_appear_in_the_data():
    """Each required fact must be stated somewhere in the docs or catalog, so the label
    is answerable. Skips "not found"-style patterns, which describe behavior, not data."""
    import csv
    import re
    from copilot.config import DATA
    corpus = " ".join(c.text for c in load_doc_chunks())
    corpus += " " + " ".join(" ".join(r.values()) for r in csv.DictReader(open(DATA / "products.csv")))
    for c in load_cases("heldout"):
        if c["category"] in ("escalate", "clarify"):
            continue
        for pat in c["expected_facts"]:
            if "HX-R6008" in pat:  # part name, answered from the catalog
                continue
            assert re.search(pat, corpus, re.I), (c["id"], pat)


def test_heldout_needs_frozen_flag(monkeypatch):
    import sys
    import pytest
    from evals import run
    monkeypatch.setattr(sys, "argv", ["run", "--set", "heldout"])
    with pytest.raises(SystemExit, match="scored once"):
        run.main()


def test_grade_pass():
    draft = {"answers": [{"question": "q", "answer": "8.9 W", "sources": ["spec:HX-R6016"],
                          "confidence": "high"}], "escalations": [], "reply_email": ""}
    case = _case(required_tools=["lookup_product"], expected_sources=["spec:HX-R6016"],
                 expected_facts=[r"8\.9\s*W"])
    assert grade(case, _result(draft))["passed"]


def test_grade_wrong_escalation_and_forbidden():
    draft = {"answers": [{"question": "q", "answer": "About $12 each", "sources": [],
                          "confidence": "low"}], "escalations": [], "reply_email": ""}
    g = grade(_case(should_escalate=True, forbidden=[r"\$\s*\d"]), _result(draft))
    assert not g["escalation"] and not g["forbidden_ok"] and not g["passed"]


def test_grade_chunk_citation_counts_for_doc():
    draft = {"answers": [{"question": "q", "answer": "x", "sources": ["AN-101#3"],
                          "confidence": "high"}], "escalations": [], "reply_email": ""}
    assert grade(_case(expected_sources=["AN-101"]), _result(draft))["citation"]


def test_grade_no_draft():
    g = grade(_case(), {"status": "refusal", "draft": None})
    assert not g["passed"]


def test_grader_normalizes_typographic_hyphens():
    draft = {"answers": [{"question": "q", "answer": "Use the HX\u2011R5016 with hot\u2011plug.",
                          "sources": [], "confidence": "high"}], "escalations": [], "reply_email": ""}
    g = grade(_case(expected_facts=[r"HX-R5016", r"hot[- ]?plug"]), _result(draft))
    assert g["facts"] == 1.0
