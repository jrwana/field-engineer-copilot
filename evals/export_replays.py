"""Export a saved eval run as the public demo's replay file, re-scored with the current graders.

The hosted demo replays these runs for the sample emails instead of calling a model, so the
samples cost nothing and show exactly the outputs the README's numbers were measured on.

    uv run python -m evals.export_replays results/<run-dir>    # writes demo/replays.jsonl
"""

import json
import sys
from pathlib import Path

from copilot import config
from copilot.agent import check_grounding
from evals.grade import grade
from evals.run import load_cases

OUT = config.ROOT / "demo" / "replays.jsonl"


def main() -> None:
    run = Path(sys.argv[1])
    cases = {c["id"]: c for c in load_cases("dev")}  # the sample emails the app offers
    rows = [json.loads(line) for line in (run / "results.jsonl").read_text().splitlines()]
    out = []
    for row in rows:
        case = cases.get(row["case"]["id"])
        if case is None:
            continue
        r = row["result"]
        if r["draft"]:
            r["ungrounded_citations"] = check_grounding(r["draft"], set(r["retrieved"]))
        out.append({"id": case["id"], "category": case["category"], "email": case["email"],
                    "run": run.name, "result": r, "grade": grade(case, r)})
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("".join(json.dumps(x) + "\n" for x in out))
    passed = sum(x["grade"]["passed"] for x in out)
    print(f"wrote {len(out)} replays to {OUT.relative_to(config.ROOT)} ({passed}/{len(out)} pass)")


if __name__ == "__main__":
    main()
