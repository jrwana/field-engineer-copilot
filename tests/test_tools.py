import json

from copilot.catalog import Catalog
from copilot.search import BM25, load_doc_chunks, tokenize
from copilot.tools import Toolbox


def test_lookup_found_and_case_insensitive():
    rows = Catalog().lookup(["hx-r6016"])
    assert rows[0]["typical_power_w"] == 8.9
    assert rows[0]["source_id"] == "spec:HX-R6016"


def test_lookup_unknown_part_is_explicit():
    row = Catalog().lookup(["HX-R6032"])[0]
    assert row["found"] is False and "source_id" not in row


def test_find_excludes_eol_by_default():
    parts = {r["part_number"] for r in Catalog().find(device_type="retimer")}
    assert "HX-R4016" not in parts and "HX-R6016" in parts


def test_find_cxl_and_gen_filters():
    parts = {r["part_number"] for r in Catalog().find(min_pcie_gen=6, cxl_required=True)}
    assert parts == {"HX-R6008", "HX-R6016"}


def test_tokenize_splits_part_numbers():
    assert {"hx-r5016", "r5016"} <= set(tokenize("HX-R5016"))


def test_chunk_ids_stable_and_unique():
    ids = [c.source_id for c in load_doc_chunks()]
    assert len(ids) == len(set(ids)) and "AN-101#3" in ids


def test_search_finds_erratum():
    top = BM25(load_doc_chunks()).search("HX-R5016 trains 16 GT/s SRIS", k=3)
    assert top[0][0].doc_id == "ER-R5-003"


def test_toolbox_records_retrieved_ids_only_for_real_hits():
    tb = Toolbox()
    tb.run("lookup_product", {"part_numbers": ["HX-R6016", "HX-NOPE"]})
    assert tb.retrieved == {"spec:HX-R6016"}


def test_toolbox_bad_args_is_error_not_crash():
    out, is_error = Toolbox().run("search_docs", {})
    assert is_error and "error" in json.loads(out)



def test_read_doc_returns_all_sections_and_marks_them_retrieved():
    tb = Toolbox()
    out, is_error = tb.run("read_doc", {"doc_id": "pb-memory"})
    sections = json.loads(out)
    assert not is_error and any("2 TB" in s["text"] for s in sections)
    assert "PB-MEMORY#2" in tb.retrieved


def test_read_doc_unknown_id_lists_valid_ids():
    out, is_error = Toolbox().run("read_doc", {"doc_id": "NOPE"})
    assert is_error and "AN-101" in out
