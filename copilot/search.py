"""Keyword search (BM25) over the docs and past tickets.

Why BM25 and no embeddings: the corpus is ~50 chunks, and the hard queries are
exact tokens (part numbers, "SRIS", "2.4.1") where keyword match is strongest.
evals/retrieval_check.py measures this; add a dense retriever only if it fails.
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .config import DATA

_STOP = set("a an and are as at be by can do does for from has have how i if in is it its of on or our so that the this to us we what when which will with you your".split())
_TOKEN = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    out = []
    for tok in _TOKEN.findall(text.lower()):
        if tok in _STOP:
            continue
        out.append(tok)
        if "-" in tok:  # "hx-r5016" also matches "r5016"
            out.extend(p for p in tok.split("-") if p and p not in _STOP)
    return out


@dataclass
class Chunk:
    source_id: str
    doc_id: str
    title: str
    text: str


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [Counter(tokenize(c.title + " " + c.text)) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(len(self.lengths), 1)
        df = Counter(t for d in self.docs for t in d)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        q = tokenize(query)
        scored = []
        for i, d in enumerate(self.docs):
            s = 0.0
            for t in q:
                if t in d:
                    tf = d[t]
                    s += self.idf[t] * tf * (self.k1 + 1) / (
                        tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg))
            if s > 0:
                scored.append((self.chunks[i], s))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]


def load_doc_chunks(doc_dir: Path = DATA / "docs") -> list[Chunk]:
    """One chunk per '## ' section. Section IDs are stable: DOC-ID#1, DOC-ID#2, ..."""
    chunks = []
    for path in sorted(doc_dir.glob("*.md")):
        doc_id = path.stem
        lines = path.read_text().splitlines()
        title = lines[0].lstrip("# ").strip()
        sections, current = [], None
        for line in lines[1:]:
            if line.startswith("## "):
                current = [line[3:].strip(), []]
                sections.append(current)
            elif current and line.strip() and not line.startswith(">"):
                current[1].append(line.strip())
        for i, (heading, body) in enumerate(sections, 1):
            chunks.append(Chunk(f"{doc_id}#{i}", doc_id, title, f"{heading}: {' '.join(body)}"))
    return chunks


def load_ticket_chunks(path: Path = DATA / "tickets.jsonl") -> list[Chunk]:
    out = []
    for line in path.read_text().splitlines():
        t = json.loads(line)
        out.append(Chunk(t["ticket_id"], t["ticket_id"], "Past ticket",
                         f"Question: {t['question']} Resolution: {t['resolution']}"))
    return out
