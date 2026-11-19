"""Public-demo support: free replays for the sample emails and caps on live runs.

Enabled by PUBLIC_DEMO=1 (the hosted deployment). Sample emails replay a saved, graded eval run
from demo/replays.jsonl, so they cost nothing and show the outputs the README's numbers came from.
Anything else a visitor types runs live on the hosted model, within the caps below. The counters
live in memory: a restart resets them, which is fine for a single small demo instance.
"""

import json
import os
import threading
import time
from dataclasses import dataclass

from . import config

REPLAYS = config.ROOT / "demo" / "replays.jsonl"
MAX_EMAIL_CHARS = 2000  # bounds the tokens a single live run can spend


def enabled() -> bool:
    return os.getenv("PUBLIC_DEMO") == "1"


def load_replays() -> dict[str, dict]:
    """Saved runs keyed by the exact sample email text."""
    if not REPLAYS.exists():
        return {}
    rows = [json.loads(line) for line in REPLAYS.read_text().splitlines() if line.strip()]
    return {r["email"].strip(): r for r in rows}


def client_ip(headers) -> str:
    # Caddy sets X-Forwarded-For to the real client address and drops any value the client sent.
    forwarded = (headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or "unknown"


@dataclass(frozen=True)
class Limits:
    daily: int = int(os.getenv("MAX_DAILY_RUNS", "100"))
    per_ip_daily: int = int(os.getenv("MAX_IP_RUNS_PER_DAY", "10"))
    per_session: int = int(os.getenv("MAX_SESSION_RUNS", "5"))


class Quota:
    """Thread-safe counters for live runs: per UTC day overall, per IP per day, per session."""

    def __init__(self, limits: Limits | None = None, clock=time.time):
        self.limits = limits or Limits()
        self.clock = clock
        self._lock = threading.Lock()
        self._day = ""
        self._total = 0
        self._by_ip: dict[str, int] = {}
        self._by_session: dict[str, int] = {}

    def try_consume(self, ip: str, session: str) -> str | None:
        """Count one live run. Returns None if allowed, else the reason it isn't."""
        with self._lock:
            day = time.strftime("%Y-%m-%d", time.gmtime(self.clock()))
            if day != self._day:
                self._day, self._total, self._by_ip = day, 0, {}
            if self._total >= self.limits.daily:
                return "The demo's daily limit for live runs is used up. Sample emails still replay."
            if self._by_ip.get(ip, 0) >= self.limits.per_ip_daily:
                return "You've reached today's limit of live runs. Sample emails still replay."
            if self._by_session.get(session, 0) >= self.limits.per_session:
                return "This session has used its live runs. Sample emails still replay."
            self._total += 1
            self._by_ip[ip] = self._by_ip.get(ip, 0) + 1
            self._by_session[session] = self._by_session.get(session, 0) + 1
            return None
