"""Public-demo pieces: replay file, client IP, and live-run caps."""

from copilot import demo
from evals.run import load_cases


def test_every_sample_email_has_a_graded_replay():
    replays = demo.load_replays()
    samples = [c["email"].strip() for c in load_cases("dev")]
    assert set(samples) <= set(replays)
    r = replays[samples[0]]
    assert r["result"]["draft"] and "passed" in r["grade"]
    # The replay file is the run the README's dev pass rate (88%) was measured on.
    assert sum(x["grade"]["passed"] for x in replays.values()) == 21


def test_client_ip_uses_first_forwarded_address():
    assert demo.client_ip({"X-Forwarded-For": "203.0.113.9, 172.18.0.2"}) == "203.0.113.9"
    assert demo.client_ip({}) == "unknown"


def test_quota_caps_session_ip_and_day():
    now = [86_400.0 * 100]
    q = demo.Quota(demo.Limits(daily=4, per_ip_daily=3, per_session=2), clock=lambda: now[0])
    assert q.try_consume("ip1", "s1") is None
    assert q.try_consume("ip1", "s1") is None
    assert "session" in q.try_consume("ip1", "s1")       # third run in one session
    assert q.try_consume("ip1", "s2") is None
    assert "today's limit" in q.try_consume("ip1", "s3")  # fourth run from one IP
    assert q.try_consume("ip2", "s4") is None
    assert "daily limit" in q.try_consume("ip3", "s5")    # fifth run overall
    now[0] += 86_400                                       # next UTC day resets day counters
    assert q.try_consume("ip1", "s6") is None


def test_enabled_reads_env(monkeypatch):
    monkeypatch.delenv("PUBLIC_DEMO", raising=False)
    assert not demo.enabled()
    monkeypatch.setenv("PUBLIC_DEMO", "1")
    assert demo.enabled()
