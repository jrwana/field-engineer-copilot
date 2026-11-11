# Design decisions

Each entry: the choice, what else I considered, and why. Where a measurement
backs the choice, the number is here. These are the talking points for the video.

## D1. Fictional company, synthetic data
**Considered:** scraping a real vendor's public product pages.
**Chose:** a fictional company ("Halo Interconnect") with products modeled on public
PCIe/CXL concepts.
**Why:** (1) I control the ground truth, so every eval label is mechanically checkable.
(2) No copyright or impersonation issues. (3) I can plant realistic traps: an EOL part
with a replacement, an erratum fixed in a later silicon revision, a sampling-only part,
and NDA-only information.
**Cost:** synthetic docs are cleaner than real ones. The README says so.

## D2. An agent with tools, not one-shot RAG
**Considered:** retrieve the top-k chunks, stuff them into one prompt, answer.
**Chose:** a tool-using agent that decides which source to consult per question.
**Why:** customer emails mix question types. "What's the power?" is an exact catalog
fact. "Do I need a retimer for 30 dB?" needs an app note. "What's the price?" needs no
retrieval at all; it needs escalation. One retrieval pass can't serve all three well.
**Evidence:** searching the raw email text finds the right *document* 94% of the time
(recall@5, `evals/retrieval_check.py`), but the one miss, "typical power of HX-R6016",
is a spec that lives only in the catalog. Text search can't answer it at any k.

## D3. Structured catalog in SQLite, separate from text search
**Why:** a SQL row is either right or missing. It can't be "almost" retrieved or
paraphrased wrong. Unknown part numbers return `found: false` plus the list of real
parts, which gives the model an explicit signal not to guess (eval case E13).

## D4. BM25 only, no embeddings, no vector database
**Why:** ~50 chunks, and the hardest queries are exact tokens (part numbers, "SRIS",
firmware "2.4.1") where keyword search is strongest. A vector DB adds a service and an
embedding model for no measured gain. **Rule I set:** add a dense retriever only if the
retrieval check or the eval shows misses that keywords can't fix.

## D5. Citations are checked in code, not trusted
Every tool result carries a `source_id`. The toolbox records every ID it actually
returned. After the draft, `check_grounding()` flags any cited ID that was never
retrieved, and the UI shows it as a warning. The model can't cite its way out of
having no evidence.

## D6. Escalation is part of the draft, not a separate action tool
**Considered:** an `escalate()` tool that "files" an escalation.
**Chose:** escalations are a field in the final draft, with a category and owning team.
**Why:** a human approves everything anyway, so there's no side effect to trigger
mid-run. It also makes escalation directly gradeable: in both directions, did it
escalate exactly when it should?

## D7. Structured final output via a strict `submit_draft` tool
The draft schema (answers + sources + confidence, escalations, reply) is enforced with
`strict: true`, so the UI and the graders never parse free text. Forced `tool_choice`
isn't available on the model I used, so the prompt asks for `submit_draft`, and the
loop nudges once if the model ends without it (tested in `test_nudge_recovers`).

## D8. Hand-written agent loop
**Considered:** the SDK's tool runner.
**Chose:** a ~60-line manual loop.
**Why:** I wanted every step recorded (tool, input, output, tokens, time) for the UI
trace, the eval and the cost numbers, plus explicit handling of refusals, max_tokens
and a hard turn cap.

## D9. Deterministic graders, no LLM judge
**Why:** a regex/ID/tool-name label can be explained line by line, costs nothing to
re-run, and doesn't drift. **Cost:** a correct paraphrase can fail a regex. I read
every failure before trusting a score drop, and I record grader misses in the results notes.

## D10. Cost and reliability defaults
- Prompt caching: the system prompt and tool definitions are identical on every call,
  so they're cached.
- Server-side refusal fallback is on: if the model declines a request on policy
  grounds, the API retries on a fallback model in the same call.
- Effort is a parameter (`--effort`), so the eval can measure the quality/cost trade-off
  instead of guessing it.

## D11. A local model backend behind the same loop
**Chose:** an adapter (`copilot/local.py`) that translates the agent's requests to a
self-hosted vLLM server's OpenAI-compatible API and translates responses back. The loop,
tools, grounding check and graders don't change.
**Why:** (1) free iteration on prompts and tools during development; (2) a fair
local-vs-hosted comparison, because everything except the model is held fixed.
**What it exposed:** Claude's `strict` schema guarantees a well-formed draft; local models
don't. So the loop now validates every draft in code and sends errors back for one retry
(`validate_draft`). The check is a no-op for Claude, but it makes the loop safe for any
backend.

## D12. `read_doc`: search to locate, then read
**Problem found:** a question worded "maximum capacity" never keyword-matches a doc that
says "up to 2 TB". Search found the right document but not the section, and the local
model kept re-searching.
**Tried first:** tagging every chunk with its document's part numbers. It didn't fix the
case and lowered retrieval recall@5 from 94% to 88%, so I reverted it.
**Chose:** a `read_doc` tool. Docs are short, so once search finds the right one, reading
it whole is cheap and avoids guessing at keywords. That's how a person uses docs too.
**Not chosen (yet):** embeddings. This is the kind of vocabulary mismatch dense
retrieval fixes, but `read_doc` solved it with no new dependency. Revisit if the
held-out set shows more mismatches.

## Open questions (to settle with data)
- Does `low` effort keep accuracy while cutting cost and latency? Run both.
- Do testers trust the confidence labels, or ignore them?
- How far behind a 20B local model is on tool choice and escalation, at $0.
