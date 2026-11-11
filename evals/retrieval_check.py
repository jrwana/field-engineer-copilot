"""Offline retrieval check: no API key, no cost.

For each labeled email whose expected sources include a document, does BM25 put
that document in the top k when searched with the raw email text? This is a
pessimistic test: the agent writes its own, sharper queries.

    uv run python -m evals.retrieval_check
"""

from copilot.search import BM25, load_doc_chunks, load_ticket_chunks
from evals.run import load_cases


def recall_at_k(k: int = 5) -> tuple[float, list[str]]:
    index = BM25(load_doc_chunks() + load_ticket_chunks())
    hits, misses, n = 0, [], 0
    for c in load_cases():
        expected = {s for s in c["expected_sources"] if not s.startswith("spec:")}
        if not expected:
            continue
        n += 1
        top = {ch.doc_id for ch, _ in index.search(c["email"], k=k)}
        if top & expected:
            hits += 1
        else:
            misses.append(c["id"])
    return hits / n, misses


if __name__ == "__main__":
    for k in (1, 3, 5):
        r, misses = recall_at_k(k)
        print(f"recall@{k}: {r:.0%}  misses: {misses}")
