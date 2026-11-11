"""Run the copilot on one email from the command line.

    uv run python -m copilot.cli "Does the HX-R6016 work with a Gen5 SSD?"
"""

import json
import sys

from dotenv import load_dotenv

from .agent import Copilot, save_trace


def main() -> None:
    load_dotenv()
    email = " ".join(sys.argv[1:]) or sys.stdin.read()
    res = Copilot().run(email, on_step=lambda e: print(f"  [{e['t']:>5}s] {e['type']} {e.get('name', '')} {json.dumps(e.get('input', ''))}", file=sys.stderr))
    save_trace(res)
    print(json.dumps({k: res.to_dict()[k] for k in ("status", "draft", "ungrounded_citations", "cost_usd", "latency_s", "error")}, indent=2))


if __name__ == "__main__":
    main()
