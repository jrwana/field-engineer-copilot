"""Settings in one place, so the eval can sweep them."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RUNS = ROOT / "runs"

MODEL = "claude-opus-5-5"
EFFORT = "medium"  # low | medium | high | xhigh | max
MAX_TOKENS = 16000
MAX_TURNS = 8  # hard cap on agent loop iterations

# Self-hosted models (vLLM, OpenAI-compatible). Free to run; endpoint from LOCAL_LLM_ENDPOINT.
LOCAL_MODELS = ["local:openai/gpt-oss-20b"]

# USD per million tokens. Check current prices before quoting cost numbers.
PRICES = {
    "claude-opus-5-5": {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00},
    "claude-sonnet-5-5": {"input": 2.00, "output": 10.00, "cache_read": 0.10, "cache_write": 2.50},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.125},
}
