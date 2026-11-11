"""Tool definitions the model sees, plus the code that runs them.

Every result carries a `source_id`. The agent must cite these IDs, and
`Toolbox.retrieved` records every ID actually returned, so citations can be
checked in code instead of trusted.
"""

import json

from .catalog import DEVICE_TYPES, Catalog
from .search import BM25, load_doc_chunks, load_ticket_chunks

ESCALATION_CATEGORIES = [
    "pricing_or_lead_time", "roadmap", "nda", "reliability",
    "unknown_part", "needs_clarification", "other",
]

TOOLS = [
    {
        "name": "lookup_product",
        "description": (
            "Exact catalog lookup by part number. Returns specs (PCIe gen, max rate, lanes, "
            "CXL version, typical latency and power, package, temperature range, lifecycle "
            "status, replacement part). Use for any question about a specific part's specs "
            "or status. Unknown part numbers return found=false; never guess their specs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "part_numbers": {"type": "array", "items": {"type": "string"},
                                 "description": "One or more part numbers, e.g. ['HX-R6016']"},
            },
            "required": ["part_numbers"],
            "additionalProperties": False,
        },
    },
    {
        "name": "find_products",
        "description": (
            "Filter the catalog when the customer describes a need but no part number, "
            "e.g. 'a PCIe 6.0 retimer with 16 lanes'. Excludes end-of-life parts unless "
            "include_eol is true."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "device_type": {"type": "string", "enum": ["any", *DEVICE_TYPES]},
                "min_pcie_gen": {"type": "integer", "description": "0 = no minimum"},
                "min_lanes": {"type": "integer", "description": "0 = no minimum"},
                "cxl_required": {"type": "boolean"},
                "include_eol": {"type": "boolean"},
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    {
        "name": "search_docs",
        "description": (
            "Keyword search over product briefs, application notes (AN-xxx), errata (ER-xxx), "
            "firmware release notes, the thermal guide and the support policy. Use for how/why "
            "questions, compatibility, known issues, design guidance and anything not in the "
            "catalog columns. Use specific terms: part numbers, error symptoms, feature names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_doc",
        "description": (
            "Read one whole document by its ID (the part before '#' in a source_id, e.g. "
            "'PB-MEMORY' or 'AN-101'; catalog rows name their product brief in brief_doc). "
            "Docs are short. Use this when search found the right document but not the exact "
            "detail, instead of repeating similar searches."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"doc_id": {"type": "string"}},
            "required": ["doc_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "find_similar_tickets",
        "description": (
            "Search past resolved support tickets for similar questions, to keep answers "
            "consistent with how the team answered before. Tickets are supporting evidence; "
            "prefer docs or the catalog as the primary source when both exist."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "submit_draft",
        "description": (
            "Submit the final draft for the field engineer to review. Call this exactly once, "
            "after gathering evidence. Every answer must list the source_ids it relies on."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "answer": {"type": "string"},
                            "sources": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                        },
                        "required": ["question", "answer", "sources", "confidence"],
                        "additionalProperties": False,
                    },
                },
                "escalations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "category": {"type": "string", "enum": ESCALATION_CATEGORIES},
                            "route_to": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["question", "category", "route_to", "reason"],
                        "additionalProperties": False,
                    },
                },
                "reply_email": {"type": "string"},
            },
            "required": ["answers", "escalations", "reply_email"],
            "additionalProperties": False,
        },
    },
]


class Toolbox:
    """Runs tools for one agent run and remembers which source IDs it returned."""

    def __init__(self, catalog: Catalog | None = None):
        self.catalog = catalog or Catalog()
        self.docs = BM25(load_doc_chunks())
        self.tickets = BM25(load_ticket_chunks())
        self.retrieved: set[str] = set()

    def run(self, name: str, args: dict) -> tuple[str, bool]:
        """Returns (json_result, is_error)."""
        try:
            if name == "lookup_product":
                result = self.catalog.lookup(args["part_numbers"])
            elif name == "find_products":
                result = self.catalog.find(**args)
            elif name == "search_docs":
                result = self._search(self.docs, args["query"], k=5)
            elif name == "read_doc":
                key = args["doc_id"].strip().upper().split("#")[0]
                result = [{"source_id": c.source_id, "title": c.title, "text": c.text}
                          for c in self.docs.chunks if c.doc_id == key]
                if not result:
                    valid = sorted({c.doc_id for c in self.docs.chunks})
                    return json.dumps({"error": f"No document '{key}'. Valid IDs: {valid}"}), True
            elif name == "find_similar_tickets":
                result = self._search(self.tickets, args["query"], k=3)
            else:
                return json.dumps({"error": f"Unknown tool {name}"}), True
        except (KeyError, TypeError) as e:
            return json.dumps({"error": f"Bad arguments for {name}: {e}"}), True
        for item in result:
            if "source_id" in item:
                self.retrieved.add(item["source_id"])
        return json.dumps(result), False

    @staticmethod
    def _search(index: BM25, query: str, k: int) -> list[dict]:
        hits = index.search(query, k=k)
        if not hits:
            return [{"note": "No matching documents."}]
        return [{"source_id": c.source_id, "title": c.title, "text": c.text,
                 "score": round(s, 2)} for c, s in hits]
