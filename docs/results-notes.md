# Results notes

Every number here was reviewed by reading the failing drafts, not just the score.
Grader fixes are logged separately from model/system fixes, so no improvement is
claimed twice.

## 2026-11-10 · Local model: gpt-oss-20b on a 3090 Ti (vLLM), effort=medium, $0

| Run | System version | Raw pass | After grader fixes (regraded, same outputs) |
|---|---|---|---|
| 1 | v1 | 79% (19/24) | **83%** (20/24) |
| 2 | v1 + `read_doc` tool + "tool names are not sources" | 79% (19/24) | **88%** (21/24) |

Mean latency ~6 s per email. Runs vary from one to the next even at temperature 0
(batched GPU inference), so single-email differences between runs are noise, not signal.

### Grader bugs found by reading failures (fixed, then re-scored with `evals/regrade.py`)
1. **Typographic characters.** The model writes `HX‑R5016` with a non-breaking hyphen
   (U+2011), narrow no-break spaces and curly apostrophes. The regexes missed correct
   answers (E04, E08, E13). Fix: normalize before matching.
2. **Too-narrow phrasing.** E13's "couldn't locate that part" was correct but the regex
   only allowed "find". Added "locate".
3. **Citation check too strict.** Citing a whole document (`TG-THERMAL`) when a section of
   it was retrieved was flagged as ungrounded (E10). Now whole-doc IDs are accepted if
   any section was retrieved; invented section IDs (`AN-204#5`) still fail.

### A real error the grader had missed
- E04: the model called the HX-R5016 "PCIe 4.0" (it's 5.0). The draft "passed" only
  because nothing checked for it. Added a forbidden-claim pattern; E04 now fails
  correctly in run 1.

### System fixes
- **`read_doc` tool (E24).** "Maximum memory capacity" never matches "Up to 2 TB" by
  keyword. Search found the right document but not the right section, and the model
  searched six times. First attempt, tagging chunks with part numbers, didn't fix it
  and dropped retrieval recall@5 from 94% to 88%, so it was reverted. `read_doc` lets
  the agent read a short document whole once search has located it.
- **Prompt: "tool names are not sources" (E13).** The model had cited `lookup_product`.

### Remaining real failures (gpt-oss-20b)
- **E07, both runs:** gives the firmware workaround but never mentions that silicon
  rev B0 fixes the erratum. The answer is incomplete.
- **E24, both runs:** inefficient search. In run 2 it called `read_doc` only on its
  8th and final turn, after 6 near-duplicate searches.
- **E06 (run 2):** correct answer, but cited a section that doesn't exist (`AN-204#5`).
  The grounding check caught it, which is what the check is for.

### Caveat
The eval set is also the development set: I looked at these failures and changed the
system. The 88% is a development number, not a held-out result. Before quoting a final
number, write ~10 new emails that the system has never been tuned on, and score them once.

## Held-out set (written 2026-11-10, not yet scored)

`evals/heldout.jsonl`: 12 emails, labels written **before** any run. They cover the
same behaviors as the dev set with new questions and facts the dev set doesn't ask
about: package and temperature range, product selection without a part number,
a PCIe 5.0 loss budget, latency of a retimer in front of the memory controller,
identifying silicon revision, an Ethernet part asked to do PCIe, two escalations in
one email, a mistyped part number, answer + roadmap in one email, a heatsink
temperature limit, sample firmware, and a vague report.

**Protocol**
1. Freeze: no more changes to the prompt, tools, search or graders.
2. Run once per configuration you plan to report:
   `uv run python -m evals.run --set heldout --frozen --model <model>`
3. Each run is appended to `evals/heldout_runs.md`. Report the first run per
   configuration, whatever it says.
4. If you change the system afterwards, the held-out number describes the old
   system. Write a new held-out set for the new one.

**Known weakness:** I (the builder) wrote these, knowing how the system works. That's
better than no held-out set, but a stronger test is 3–5 extra emails written by someone
else (for example a user-test participant), labeled against the docs, and scored once.
