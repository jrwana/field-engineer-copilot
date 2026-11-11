# User test protocol

**Goal:** measure whether the copilot makes answering customer emails faster and
more accurate, and collect feedback for v2.

## Participants
5 people with a technical background (classmates or friends in engineering). No
chip-industry experience is needed: everyone gets the same docs, which mirrors a
new FAE.

## Setup (about 30 minutes per person)
1. Give them the 11 docs in `data/docs/` and `data/products.csv` (as the "manual" condition).
2. Prepare 6 emails **not** in `evals/emails.jsonl`, of similar difficulty. Write them
   before the first session and don't change them between sessions.
3. Split them into set A and set B (3 each, one escalation case in each).
4. Counterbalance: participants 1, 3 and 5 do A manually, then B with the tool;
   participants 2 and 4 do the reverse.

## Per email, record
| Field | How |
|---|---|
| Time to a ready-to-send reply | stopwatch, start when they open the email |
| Factual errors | compare with the answer key you wrote beforehand |
| Wrongly answered escalation cases | e.g. guessed a price or roadmap date |
| Tool condition: approved, edited or rejected | from `runs/feedback.jsonl` |

Use `user-testing-results.csv` (columns below) to record it:

```
participant,email_id,condition,seconds,factual_errors,escalation_mistake,decision,notes
```

## After the session, ask (5 minutes)
1. When did you trust the draft without checking? When didn't you?
2. Did the confidence colors and source tags change what you checked?
3. What did you edit most often?
4. What would make you use this daily? What would make you stop?
5. Rate 1–5: "I would send a reply drafted this way after a quick review."

## Report
- Median time per email, manual vs tool, and the % change.
- Total factual errors, manual vs tool.
- Top 3 feedback themes, each with one quote.
- **One v2 change driven by the feedback**, with before/after eval numbers.

Keep the honest version: if the tool didn't help on some email type, say which
and why. That's a finding, not a failure.
