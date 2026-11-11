# Scope: Field Engineer Copilot

*One page, written before building. Updated only by adding a "Changed" note.*

## The problem

A field applications engineer (FAE) at a connectivity-chip company gets a steady
stream of customer emails such as: "Does your Gen 6 retimer work with our Gen 5
SSD? What's the latency? And what's the price at 50k units?" To answer, they
search product briefs, app notes, errata and old tickets, then write a careful
reply. A wrong spec costs credibility. Answering a pricing or roadmap question
they shouldn't answer causes a different problem.

## The user

One FAE, mid-conversation with a customer, who wants a **checkable first draft**
in under a minute. The FAE stays responsible for what gets sent.

## What it does (v1)

1. Takes a pasted customer email.
2. Splits it into separate questions.
3. For each question, chooses a tool:
   - `lookup_product` / `find_products`: exact specs from a structured catalog
   - `search_docs`: product briefs, app notes, errata, firmware notes
   - `find_similar_tickets`: how past questions were answered
4. Returns a draft: an answer per question with source IDs and a confidence
   level, a list of escalations with the owning team, and a customer-ready reply.
5. **Code checks the citations.** Any cited source the agent never actually
   retrieved is flagged in the UI.
6. The FAE approves, edits or rejects the draft. That decision is logged as feedback.

## Success criteria

| Metric | How it's measured | v1 target |
|---|---|---|
| Fact accuracy | Required facts (regex) found in the draft, over 24 labeled emails | ≥ 90% |
| Escalation accuracy | Escalates exactly when it should (both directions) | ≥ 90% |
| Citation grounding | Cited IDs that were actually retrieved this run | 100% |
| Tool choice | Required tools were called | ≥ 90% |
| Time saved | User test: time per email with and without the tool | ≥ 30% faster |
| Errors | User test: factual errors in sent replies, with and without the tool | fewer with the tool |
| Cost / latency | Per email, from API usage | report it; no target in v1 |

## Non-goals

- Sending email or connecting to a real inbox. A human copies the approved reply.
- Real company data. The company ("Halo Interconnect") and its products are
  **fictional**, built on public PCIe/CXL concepts.
- Multi-turn chat. One email in, one draft out.
- Fine-tuning or a vector database. The corpus is small; see `decisions.md`.

## Anti-goals (it fails even if it "works" when it...)

- States a spec that isn't in the catalog or docs.
- Answers a pricing, roadmap, NDA or reliability question.
- Cites a source it didn't retrieve.
- Hides uncertainty to sound confident.

## Plan

| Step | Output |
|---|---|
| 1. Scope + cover letter | this doc, `01-cover-letter-draft.md` |
| 2. Data | catalog CSV, 11 docs, 12 tickets, 24 labeled emails |
| 3. Tools + agent | `copilot/` with offline tests |
| 4. Eval | `evals/run.py`, first numbers in `results/` |
| 5. UI + logging | `app.py`, traces + feedback in `runs/` |
| 6. User test (5 people) | `user-testing.md` protocol, results table |
| 7. v2 from feedback | change log entry + before/after numbers |
| 8. Video + README | `video-outline.md` |

## Risks

- **Regex grading misses correct paraphrases.** Mitigation: spot-check failures
  by hand and record misses in the results notes.
- **The eval set is small (24).** Mitigation: report per-category results and
  don't overclaim.
- **Synthetic data is easier than real data.** Mitigation: say so in the README
  and video.
