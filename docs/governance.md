# Governance and operations

How this prototype would be run responsibly inside a company. The posting asks for
projects that go through "maintenance and governance", so the answers are written down.

## Human in the loop
The agent drafts only. It has no tool that sends email or changes any system. An
engineer approves, edits or rejects every draft, and that decision is logged.

## What it must not answer
Pricing, lead times, roadmap, NDA material and reliability data are escalated to a
named owning team (see `data/docs/POLICY-SUPPORT.md` and the system prompt). The eval
has a case for each, and E11 and E15 also check that no price or MTBF number appears.

## Evidence and auditability
- Every claim must cite a source ID returned by a tool in the same run.
- Code flags any citation that was never retrieved (`check_grounding`).
- Each run is saved to `runs/traces/<run_id>.json`: the email, every tool call and
  its result, the draft, token usage, cost and latency.
- Feedback goes to `runs/feedback.jsonl`: decision, whether it was edited, and how much.

## Data handling
- Customer emails go to the model API. In a real deployment, check the vendor's data
  retention terms and strip personal data the model doesn't need (names, addresses).
- `runs/` is gitignored. In production, traces would need a retention period and
  access control.
- API keys live in `.env` (gitignored), never in code.

## Monitoring (what I'd watch weekly)
| Signal | Source | Why |
|---|---|---|
| Approval rate, edit rate | feedback.jsonl | the main quality signal from real users |
| Ungrounded-citation rate | traces | should be ~0; a rise means a prompt or model regression |
| Escalation rate by category | traces | sudden changes mean drift in inputs or behavior |
| Cost and p90 latency per email | traces | budget and user experience |
| Eval pass rate on every change | `evals/run.py` | catches regressions before users do |

## Change process
Any change to the prompt, tools, model or effort: run the full eval, compare with the
last saved run in `results/`, and record the result in the README changelog.
Don't ship a change that lowers escalation accuracy or grounding, even if other
metrics improve.

## Known limits
- Synthetic, clean documents. Real docs (scanned PDFs, tables, conflicting versions)
  would need better ingestion.
- 24 eval emails is small; per-category results are noisy.
- Regex grading can mark a correct paraphrase as wrong.
