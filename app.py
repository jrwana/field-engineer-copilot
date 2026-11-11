"""Streamlit UI: paste an email, watch the agent work, review and approve the draft.

    uv run streamlit run app.py
"""

import difflib
import json
import time

import streamlit as st
from dotenv import load_dotenv

from copilot import config
from copilot.agent import Copilot, save_trace
from evals.run import load_cases

load_dotenv()
st.set_page_config(page_title="Field Engineer Copilot", layout="wide")
st.title("Field Engineer Copilot")
st.caption("Halo Interconnect is a fictional company. Drafts are reviewed by an engineer before sending.")

with st.sidebar:
    model = st.selectbox("Model", [*config.PRICES, *config.LOCAL_MODELS], index=0)
    effort = st.selectbox("Effort", ["low", "medium", "high"], index=1)
    samples = {f"{c['id']} · {c['category']}": c["email"] for c in load_cases()}
    pick = st.selectbox("Sample email", ["(type your own)", *samples])

email = st.text_area("Customer email", value=samples.get(pick, ""), height=140)

if st.button("Draft reply", type="primary", disabled=not email.strip()):
    status = st.status("Working...", expanded=True)

    def on_step(e):
        if e["type"] == "tool":
            status.write(f"`{e['t']}s` **{e['name']}** `{json.dumps(e['input'])}`")
        elif e["type"] == "nudge":
            status.write("Model ended without a draft; asked it to submit one.")

    res = Copilot(model=model, effort=effort).run(email, on_step=on_step)
    save_trace(res)
    status.update(label=f"{res.status} · {res.latency_s}s · ${res.cost_usd:.4f}",
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
