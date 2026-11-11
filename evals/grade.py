"""Deterministic graders. No LLM judge: every label is a regex, a tool name or an
ID, so a score can be explained line by line and re-run for free.
The cost: a correct paraphrase can fail a regex. Read failures before trusting a drop.
"""

import re

# Models often emit typographic characters: non-breaking hyphen (U+2011), en dash,
# narrow no-break space (U+202F). Normalize them so "HX‑R5016" matches "HX-R5016".
_HYPHENS = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2212]")
_SPACES = re.compile("[\u00a0\u2007\u202f]")
_QUOTES = re.compile("[\u2018\u2019\u201b]")


def normalize(text: str) -> str:
    return _QUOTES.sub("'", _SPACES.sub(" ", _HYPHENS.sub("-", text)))


def draft_text(draft: dict) -> str:
    parts = [a["answer"] for a in draft.get("answers", [])]
    parts.append(draft.get("reply_email", ""))
    return normalize("\n".join(parts))


def grade(case: dict, result: dict) -> dict:
    draft = result.get("draft")
    g = {"id": case["id"], "category": case["category"], "status": result["status"]}
    if not draft:
        g.update(facts=0.0, tools=False, citation=False, escalation=False,
                 escalation_category=False, forbidden_ok=False, grounded=False, passed=False)
        return g

    text = draft_text(draft)

    facts = case["expected_facts"]
    hits = [bool(re.search(p, text, re.I)) for p in facts]
    g["facts"] = sum(hits) / len(facts) if facts else 1.0
    g["missed_facts"] = [p for p, h in zip(facts, hits) if not h]

    g["tools"] = set(case["required_tools"]) <= set(result["tools_called"])

    cited = {s for a in draft.get("answers", []) for s in a["sources"]}
    cited_docs = {s.split("#")[0] for s in cited}
    exp = set(case["expected_sources"])
    g["citation"] = bool(cited_docs & exp) if exp else True

    escalated = bool(draft.get("escalations"))
    g["escalation"] = escalated == case["should_escalate"]
    cats = {e["category"] for e in draft.get("escalations", [])}
    exp_cats = set(case["escalation_categories"])
    g["escalation_category"] = bool(cats & exp_cats) if exp_cats else not escalated or not case["should_escalate"]

    g["forbidden_ok"] = not any(re.search(p, text, re.I) for p in case["forbidden"])
    g["grounded"] = not result["ungrounded_citations"]

    g["passed"] = (g["facts"] == 1.0 and g["tools"] and g["citation"] and g["escalation"]
                   and g["forbidden_ok"] and g["grounded"])
    return g


def summarize(grades: list[dict], results: list[dict]) -> dict:
    n = len(grades)
    mean = lambda key: sum(float(g[key]) for g in grades) / n if n else 0.0
    return {
        "n": n,
        "pass_rate": mean("passed"),
        "fact_accuracy": mean("facts"),
        "tool_choice": mean("tools"),
        "citation_hit": mean("citation"),
        "escalation_accuracy": mean("escalation"),
        "escalation_category": mean("escalation_category"),
        "no_forbidden_claims": mean("forbidden_ok"),
        "grounding": mean("grounded"),
        "drafts_returned": sum(r["status"] == "draft" for r in results) / n if n else 0.0,
        "mean_latency_s": sum(r["latency_s"] for r in results) / n if n else 0.0,
        "mean_cost_usd": sum(r["cost_usd"] for r in results) / n if n else 0.0,
        "total_cost_usd": sum(r["cost_usd"] for r in results),
    }
