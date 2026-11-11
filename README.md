# Field Engineer Copilot

An agent that helps a field applications engineer answer a customer's technical
email. It splits the email into questions, picks the right source for each (an
exact product catalog, technical docs or past tickets), and drafts a reply in which
every claim cites its source. It escalates pricing, roadmap, NDA and reliability
questions instead of guessing. **An engineer approves every draft before it's sent.**

> **Halo Interconnect is a fictional company.** Its products, docs and tickets are
> synthetic, modeled on public PCIe/CXL concepts, so every eval label is checkable.
> This is a portfolio prototype, not a product.

## Results

| Metric | Local gpt-oss-20b ($0) | Claude |
|---|---|---|
| Retrieval recall@5 (offline, raw email as query) | **94%** | same |
| Eval pass rate (24 emails, dev set) | **88%** | _pending_ |
| Held-out pass rate (12 emails, scored once) | _not yet run_ | _not yet run_ |
| Latency per email | ~6 s | _pending_ |
| Cost per email | $0 | _pending_ |
| User test: time saved, errors | _pending ([protocol](docs/user-testing.md))_ |

## How it works

```
customer email
   │
   ▼
agent loop (Claude, tool use) ──┬── lookup_product / find_products → SQLite catalog
                                ├── search_docs → BM25 over briefs, app notes, errata
                                ├── find_similar_tickets → BM25 over past tickets
                                └── submit_draft (strict JSON schema)
   │
   ▼
grounding check in code: every cited source must have been retrieved this run
   │
   ▼
Streamlit UI → engineer approves / edits / rejects → feedback log
```

Why it's built this way: [docs/decisions.md](docs/decisions.md).

## Run it

```bash
uv sync
cp .env.example .env        # add your ANTHROPIC_API_KEY
uv run pytest               # offline, no key needed
uv run python -m evals.retrieval_check   # offline
uv run streamlit run app.py
uv run python -m evals.run  # full eval, uses the API
uv run python -m evals.run --model claude-haiku-5-5        # ~5 cents for all 24
uv run python -m evals.run --model local:openai/gpt-oss-20b  # free, self-hosted vLLM
```

The local backend talks to any vLLM server through its OpenAI-compatible API
(set `LOCAL_LLM_ENDPOINT`). The server must be started with tool calling enabled
(`--enable-auto-tool-choice --tool-call-parser openai` for gpt-oss).

## Repo map

| Path | What |
|---|---|
| `copilot/agent.py` | agent loop, grounding check, cost tracking |
| `copilot/tools.py` | tool schemas the model sees, and the code that runs them |
| `docs/results-notes.md` | every run, every failure read by hand, grader fixes logged |
| `copilot/catalog.py`, `copilot/search.py` | SQLite catalog, BM25 search |
| `copilot/local.py` | adapter for a self-hosted vLLM model, same agent loop |
| `copilot/prompts.py` | system prompt (escalation rules live here) |
| `data/` | fictional catalog, 11 docs, 12 past tickets |
| `evals/emails.jsonl` | 24 labeled dev emails: facts, tools, sources, escalation |
| `evals/heldout.jsonl` | 12 held-out emails, scored once after freezing (`--set heldout --frozen`) |
| `evals/run.py`, `evals/grade.py` | eval runner and deterministic graders |
| `app.py` | review UI |
| `docs/` | cover letter draft, scope, decisions, governance, user test, video outline |

## Limits

- Synthetic, clean documents; real PDFs and tables would need better ingestion.
- 24 eval emails is small; per-category numbers are noisy.
- Regex graders can mark a correct paraphrase as wrong; failures are reviewed by hand.

## Changelog

- **v1:** agent, tools, eval harness, UI, governance docs.
- **v1.1:** local model backend; `read_doc` tool; grader fixes and `evals/regrade.py`
  (see [results notes](docs/results-notes.md)).
