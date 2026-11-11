"""Structured product catalog in SQLite.

Exact questions ("what is the power of HX-R6016?") go here, not to text search:
a SQL row is either right or missing, and it can't be paraphrased wrong.
"""

import csv
import sqlite3
from pathlib import Path

from .config import DATA

COLUMNS = [
    "part_number", "family", "device_type", "pcie_gen", "max_rate_gts", "lanes",
    "cxl_version", "typical_latency_ns", "typical_power_w", "package",
    "temp_range_c", "status", "replacement", "brief_doc",
]
DEVICE_TYPES = ["retimer", "switch", "cxl_memory_controller", "ethernet_retimer"]
_NUMERIC = {"pcie_gen", "max_rate_gts", "lanes", "typical_latency_ns", "typical_power_w"}


class Catalog:
    def __init__(self, csv_path: Path = DATA / "products.csv"):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute(f"CREATE TABLE products ({', '.join(COLUMNS)})")
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                values = [self._coerce(c, row[c]) for c in COLUMNS]
                self.db.execute(
                    f"INSERT INTO products VALUES ({', '.join('?' * len(COLUMNS))})", values
                )

    @staticmethod
    def _coerce(col: str, value: str):
        if value == "":
            return None
        if col in _NUMERIC:
            return float(value) if "." in value else int(value)
        return value

    @staticmethod
    def _row(r: sqlite3.Row) -> dict:
        d = {k: r[k] for k in r.keys() if r[k] is not None}
        d["source_id"] = f"spec:{r['part_number']}"
        return d

    def part_numbers(self) -> list[str]:
        return [r[0] for r in self.db.execute("SELECT part_number FROM products")]

    def lookup(self, part_numbers: list[str]) -> list[dict]:
        out = []
        for pn in part_numbers:
            key = pn.strip().upper()
            r = self.db.execute("SELECT * FROM products WHERE part_number = ?", (key,)).fetchone()
            if r:
                out.append(self._row(r))
            else:
                out.append({
                    "part_number": key,
                    "found": False,
                    "note": "No such part in the catalog. Do not guess its specs.",
                    "known_parts": self.part_numbers(),
                })
        return out

    def find(self, device_type: str = "any", min_pcie_gen: int = 0, min_lanes: int = 0,
             cxl_required: bool = False, include_eol: bool = False) -> list[dict]:
        sql, args = "SELECT * FROM products WHERE 1=1", []
        if device_type and device_type != "any":
            sql += " AND device_type = ?"
            args.append(device_type)
        if min_pcie_gen:
            sql += " AND pcie_gen >= ?"
            args.append(min_pcie_gen)
        if min_lanes:
            sql += " AND lanes >= ?"
            args.append(min_lanes)
        if cxl_required:
            sql += " AND cxl_version != 'none'"
        if not include_eol:
            sql += " AND status != 'eol'"
        return [self._row(r) for r in self.db.execute(sql, args)]
