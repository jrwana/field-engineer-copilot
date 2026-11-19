"""Streamlit UI: paste an email, watch the agent work, review and approve the draft.

    uv run streamlit run app.py
"""

import difflib
import json
import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv

from copilot import config, demo
from copilot.agent import Copilot, RunResult, save_trace
from evals.run import load_cases

load_dotenv()
st.set_page_config(page_title="Field Engineer Copilot", layout="wide")
st.title("Field Engineer Copilot")
st.caption("Halo Interconnect is a fictional company. Drafts are reviewed by an engineer before sending.")

PUBLIC = demo.enabled()


@st.cache_resource
def quota() -> demo.Quota:  # one set of counters per server process, shared by all sessions
    return demo.Quota()


@st.cache_data
def replays() -> dict[str, dict]:
    return demo.load_replays()


with st.sidebar:
    if PUBLIC:
        # Hosted demo: no model choice, so visitors can't pick an expensive one.
        model, effort = config.OPENAI_MODELS[0], "low"
        st.markdown(
            "**Sample emails** replay a saved, graded eval run of the self-hosted "
            "`gpt-oss-20b` model (instant, free).\n\n"
            f"**Your own email** runs live on OpenAI `{model.removeprefix('openai:')}`, "
            "a few runs per visitor per day."
        )
    else:
        model = st.selectbox("Model", [*config.PRICES, *config.LOCAL_MODELS, *config.OPENAI_MODELS],
                             index=0)
        effort = st.selectbox("Effort", ["low", "medium", "high"], index=1)
    samples = {f"{c['id']} · {c['category']}": c["email"] for c in load_cases()}
    if not PUBLIC:
        pick = st.selectbox("Sample email", ["(type your own)", *samples])

if PUBLIC:  # in the page, not the sidebar, so it's visible on narrow screens too
    pick = st.selectbox("Sample email (replays a saved run)", ["(type your own)", *samples])

email = st.text_area("Customer email", value=samples.get(pick, ""), height=140,
                     max_chars=demo.MAX_EMAIL_CHARS if PUBLIC else None)


def show_step(status, e: dict) -> None:
    if e["type"] == "tool":
        status.write(f"`{e['t']}s` **{e['name']}** `{json.dumps(e['input'])}`")
    elif e["type"] == "nudge":
        status.write("Model ended without a draft; asked it to submit one.")


def cost_label(res: RunResult) -> str:
    if res.model in config.PRICES:
        return f"${res.cost_usd:.4f}"
    if res.model.startswith("local:"):
        return "$0 (self-hosted)"
    u = res.usage
    return f"{u.get('input_tokens', 0):,} in / {u.get('output_tokens', 0):,} out tokens"


if st.button("Draft reply", type="primary", disabled=not email.strip()):
    saved = replays().get(email.strip()) if PUBLIC else None
    if saved:
        status = st.status("Replaying saved run...", expanded=True)
        res = RunResult(**saved["result"])
        for e in res.trace:
            show_step(status, e)
        verdict = "passed" if saved["grade"]["passed"] else "failed"
        status.update(label=f"Replay of eval run {saved['run'][:15]} · self-hosted "
                            f"{res.model.removeprefix('local:').removeprefix('openai/')} · "
                            f"{res.latency_s}s when recorded · {verdict} the eval",
                      state="complete" if res.status == "draft" else "error", expanded=False)
        st.session_state.res = res
    else:
        blocked = None
        if PUBLIC:
            sid = st.session_state.setdefault("sid", uuid.uuid4().hex)
            if not os.getenv("OPENAI_API_KEY"):
                blocked = "Live runs aren't configured on this server. Pick a sample email to see a replay."
            else:
                blocked = quota().try_consume(demo.client_ip(st.context.headers), sid)
        if blocked:
            st.warning(blocked)
        else:
            status = st.status("Working...", expanded=True)
            res = Copilot(model=model, effort=effort).run(email, on_step=lambda e: show_step(status, e))
            save_trace(res)
            status.update(label=f"{res.status} · {res.latency_s}s · {cost_label(res)}",
                          state="complete" if res.status == "draft" else "error", expanded=False)
            st.session_state.res = res

res = st.session_state.get("res")
if res and res.draft:
    d = res.draft
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Answers")
        for a in d["answers"]:
            icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}[a["confidence"]]
            with st.container(border=True):
                st.markdown(f"**{a['question']}**  {icon} {a['confidence']}")
                st.write(a["answer"])
                tags = []
                for s in a["sources"]:
                    ok = s in res.retrieved
                    tags.append(f"`{s}`" if ok else f"⚠️ `{s}` (not retrieved)")
                st.caption("Sources: " + (", ".join(tags) or "none"))
        if res.ungrounded_citations:
            st.error(f"Cites sources the agent never retrieved: {res.ungrounded_citations}. Verify before sending.")
        if d["escalations"]:
            st.subheader("Escalations")
            for e in d["escalations"]:
                st.warning(f"**{e['category']} → {e['route_to']}**: {e['question']}  \n{e['reason']}")
    with right:
        st.subheader("Reply (edit before approving)")
        edited = st.text_area("Reply", value=d["reply_email"], height=360, label_visibility="collapsed")
        comment = st.text_input("Comment (optional)")
        c1, c2 = st.columns(2)
        decision = "approved" if c1.button("Approve") else "rejected" if c2.button("Reject") else None
        if decision:
            fb = {"run_id": res.run_id, "decision": decision, "comment": comment,
                  "edited": edited != d["reply_email"],
                  "edit_similarity": round(difflib.SequenceMatcher(None, d["reply_email"], edited).ratio(), 3),
                  "ts": time.time()}
            config.RUNS.mkdir(exist_ok=True)
            with open(config.RUNS / "feedback.jsonl", "a") as f:
                f.write(json.dumps(fb) + "\n")
            st.success(f"Logged: {decision}" + (" (with edits)" if fb["edited"] else ""))
    with st.expander("Agent trace"):
        st.json(res.trace)
elif res:
    st.error(f"No draft: {res.status} {res.error or ''}")
