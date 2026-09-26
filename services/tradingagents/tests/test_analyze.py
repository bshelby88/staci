"""Tests for analyze.py — the per-paid-request subprocess.

Riskiest properties for a PAID endpoint:
  1. Output must be honest: never present simulated data as live analysis.
  2. Input validation must reject garbage before spending compute.
  3. Contract: exactly one parseable JSON line on stdout with required keys.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = str(Path(__file__).resolve().parent.parent / "analyze.py")


def run(args, env=None):
    e = {**os.environ, **(env or {})}
    p = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True, timeout=60, env=e,
    )
    last_json = None
    for line in reversed(p.stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            last_json = json.loads(line)
            break
    return p.returncode, last_json, p.stderr


# ---------- input validation ----------

def test_rejects_invalid_ticker_shell_metachars():
    code, out, _ = run(["--ticker", "NVDA; rm -rf /"])
    assert code != 0
    assert out and "error" in out


def test_rejects_overlong_ticker():
    code, out, _ = run(["--ticker", "A" * 11])
    assert code != 0 and out and "error" in out


def test_rejects_bad_date():
    code, out, _ = run(["--ticker", "NVDA", "--date", "2026-13-45"])
    assert code != 0 and out and "error" in out


def test_rejects_nonsense_date_string():
    code, out, _ = run(["--ticker", "NVDA", "--date", "tomorrow"])
    assert code != 0 and out and "error" in out


# ---------- output contract ----------

REQUIRED_KEYS = {"ticker", "date", "decision", "summary", "reports"}


def test_mock_mode_emits_valid_contract(monkeypatch=None):
    code, out, _ = run(["--ticker", "nvda"], env={"TRADINGAGENTS_MOCK": "1"})
    assert code == 0
    assert out and REQUIRED_KEYS <= set(out)
    assert out["ticker"] == "NVDA"  # normalized upper
    assert out["decision"] in {"BUY", "HOLD", "SELL"}


# ---------- honesty: the P0 bug ----------

def test_simulated_output_is_labeled_simulated():
    """A paid customer must never receive fabricated analysis presented as
    real. If the engine did not run, the payload MUST carry simulated=True
    and a disclaimer."""
    code, out, _ = run(["--ticker", "NVDA"], env={"TRADINGAGENTS_MOCK": "1"})
    assert code == 0 and out
    assert out.get("simulated") is True, (
        "mock payload not labeled: fabricated analysis would be sold as real"
    )
    assert "simulat" in json.dumps(out).lower() or "disclaimer" in out


def test_default_mode_never_silently_mocks():
    """Without TRADINGAGENTS_MOCK=1 the script must either run the real
    engine or fail loudly (nonzero exit + error JSON) — it must NOT return
    an unlabeled canned BUY."""
    code, out, _ = run(["--ticker", "NVDA"])
    if code == 0:
        blob = json.dumps(out)
        # canned-mock fingerprint must never appear unlabeled in default mode
        assert "12.4%" not in blob or out.get("simulated") is True
        assert out.get("simulated") is not None or "12.4%" not in blob
    else:
        assert out and "error" in out, "must fail loudly, not emit garbage"


def test_mock_not_constant_buy_masquerading():
    """Regression trap: the old bug returned decision=BUY + 'beat consensus
    estimates by 12.4%' for every ticker with no marker."""
    code, out, _ = run(["--ticker", "ZZZZ"], env={"TRADINGAGENTS_MOCK": "1"})
    assert code == 0 and out
    blob = json.dumps(out)
    if "12.4%" in blob or out.get("decision") == "BUY":
        assert out.get("simulated") is True
