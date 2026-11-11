"""Run the copilot on the labeled emails and score it.

    uv run python -m evals.run                      # all 24, default model/effort
    uv run python -m evals.run --effort low --limit 5
    uv run python -m evals.run --ids E07 E13
    uv run python -m evals.run --set heldout --frozen   # once, after the system is frozen

Writes results/<timestamp>-<model>-<effort>/ with per-email results and summary.md.
"""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

from copilot import config
from copilot.agent import Copilot
from evals.grade import grade, summarize

HERE = Path(__file__).parent


SETS = {"dev": "emails.jsonl", "heldout": "heldout.jsonl"}
HELDOUT_LOG = HERE / "heldout_runs.md"


def load_cases(name: str = "dev") -> list[dict]:
    path = HERE / SETS[name]
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def main() -> None:
    load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=config.MODEL)
    ap.add_argument("--effort", default=config.EFFORT)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--ids", nargs="*")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--set", choices=list(SETS), default="dev")
    ap.add_argument("--frozen", action="store_true",
                    help="required for --set heldout: confirms no more changes to prompt, tools or graders")
    args = ap.parse_args()

    if args.set == "heldout" and not args.frozen:
        prior = HELDOUT_LOG.read_text() if HELDOUT_LOG.exists() else "none"
        raise SystemExit(
            "The held-out set is scored once, after the system is frozen. Re-run with --frozen "
            f"to confirm. Previous held-out runs:\n{prior}")

    cases = load_cases(args.set)
    if args.ids:
        cases = [c for c in cases if c["id"] in args.ids]
    if args.limit:
        cases = cases[: args.limit]

    bot = Copilot(model=args.model, effort=args.effort)
    print(f"Running {len(cases)} emails on {args.model} (effort={args.effort})...")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = [r.to_dict() for r in pool.map(lambda c: bot.run(c["email"]), cases)]
    grades = [grade(c, r) for c, r in zip(cases, results)]
    summary = summarize(grades, results)

    safe_model = args.model.replace(":", "-").replace("/", "-")
    out = config.ROOT / "results" / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.set}-{safe_model}-{args.effort}"
    out.mkdir(parents=True)
    with open(out / "results.jsonl", "w") as f:
        for c, r, g in zip(cases, results, grades):
            f.write(json.dumps({"case": c, "result": r, "grade": g}) + "\n")
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    (out / "summary.md").write_text(render(summary, grades, args))
    print(render(summary, grades, args))
    if args.set == "heldout":
        with open(HELDOUT_LOG, "a") as f:
            f.write(f"- {time.strftime('%Y-%m-%d %H:%M')} · {args.model} · effort={args.effort} · "
                    f"pass {summary['pass_rate']:.0%} · {out.name}\n")
    print(f"\nSaved to {out}")


def render(s: dict, grades: list[dict], args) -> str:
    pct = lambda x: f"{100 * x:.0f}%"
    lines = [f"# Eval: {args.model}, effort={args.effort}, n={s['n']}", "",
             "| Metric | Value |", "|---|---|"]
    for k in ("pass_rate", "fact_accuracy", "tool_choice", "citation_hit", "escalation_accuracy",
              "escalation_category", "no_forbidden_claims", "grounding", "drafts_returned"):
        lines.append(f"| {k} | {pct(s[k])} |")
    lines += [f"| mean_latency_s | {s['mean_latency_s']:.1f} |",
              f"| mean_cost_usd | ${s['mean_cost_usd']:.4f} |",
              f"| total_cost_usd | ${s['total_cost_usd']:.3f} |", "",
              "## Failures", ""]
    fails = [g for g in grades if not g["passed"]]
    if not fails:
        lines.append("None.")
    for g in fails:
        why = [k for k in ("tools", "citation", "escalation", "forbidden_ok", "grounded") if not g.get(k)]
        if g.get("facts", 0) < 1:
            why.append(f"missed facts {g.get('missed_facts')}")
        lines.append(f"- **{g['id']}** ({g['category']}, status={g['status']}): {', '.join(why) or 'no draft'}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
