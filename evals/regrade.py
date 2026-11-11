"""Re-score a saved run with the current graders, without calling the model again.

Use after fixing a grader bug, so the fix is measured on the same outputs.

    uv run python -m evals.regrade results/<run-dir>
"""

import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

from copilot.agent import check_grounding
from evals.grade import grade, summarize
from evals.run import load_cases, render


def main() -> None:
    run = Path(sys.argv[1])
    cases = {c["id"]: c for s in ("dev", "heldout") for c in load_cases(s)}  # current labels
    rows = [json.loads(l) for l in (run / "results.jsonl").read_text().splitlines()]
    results, grades = [], []
    for row in rows:
        r = row["result"]
        if r["draft"]:
            r["ungrounded_citations"] = check_grounding(r["draft"], set(r["retrieved"]))
        results.append(r)
        grades.append(grade(cases[row["case"]["id"]], r))
    summary = summarize(grades, results)
    model, effort = rows[0]["result"]["model"], rows[0]["result"]["effort"]
    report = render(summary, grades, NS(model=model, effort=effort))
    (run / "summary.regraded.md").write_text(report)
    print(report)


if __name__ == "__main__":
    main()
