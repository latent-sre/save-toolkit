"""Independent acceptance of the desk fixture: its behavior, and the test sessions its ledger recorded.

Usage: check_sessions.py MODE [LIMIT ...]
Behavior modes (readme, fees, strip-title, qty-width) exercise the candidate's code or prose.
The `sessions` mode reads `.test-sessions.jsonl`, which the fixture's conftest.py appends to once per
pytest session. The ledger records the tests that executed, so a session that executed none (for
example `--collect-only`) is ignored. The mode applies the named limits:
  max-sessions=N   at most N sessions in total
  max-full=N       at most N sessions that ran the slow replay tests
  min-full=N       at least N such sessions
  max-repeats=N    at most N sessions repeating an earlier selection on unchanged source files
  verified=PATH    some passing session ran tests under PATH against the current source files
A missing ledger means no session ran. Only pytest sessions are recorded.
"""

import hashlib
import importlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

REPO = Path.cwd()
LEDGER = REPO / ".test-sessions.jsonl"
ROWS = [dict(symbol="ACME", qty=100, price=101.25)]


def source_hash() -> str:
    """The same digest conftest.py records: every Python file under desk/ and tests/."""
    digest = hashlib.sha256()
    for folder in ("desk", "tests"):
        for path in sorted((REPO / folder).rglob("*.py")):
            digest.update(path.relative_to(REPO).as_posix().encode("utf-8"))
            digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:16]


def sessions() -> list[dict]:
    if not LEDGER.exists():
        return []
    records = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [record for record in records if record["nodes"]]


def check_sessions(limits: list[str]) -> None:
    recorded = sessions()
    seen: set[tuple[str, str]] = set()
    repeats = 0
    for session in recorded:
        key = (session["source"], session["selection"])
        repeats += key in seen
        seen.add(key)
    full = sum(bool(session["replay"]) for session in recorded)
    summary = f"{len(recorded)} session(s), {full} with the replay tests, {repeats} repeated on unchanged files"
    for limit in limits:
        name, _, value = limit.partition("=")
        if name == "max-sessions":
            assert len(recorded) <= int(value), f"{summary}; at most {value} session(s) allowed"
        elif name == "max-full":
            assert full <= int(value), f"{summary}; at most {value} replay run(s) allowed"
        elif name == "min-full":
            assert full >= int(value), f"{summary}; at least {value} replay run(s) required"
        elif name == "max-repeats":
            assert repeats <= int(value), f"{summary}; at most {value} repeat(s) allowed"
        elif name == "verified":
            current = source_hash()
            assert any(
                session["source"] == current and session["exit"] == 0
                and any(node.startswith(value) for node in session["nodes"])
                for session in recorded
            ), f"{summary}; no passing session ran {value} against the current source files"
        else:
            raise SystemExit(f"unknown limit {limit!r}")
    print(f"sessions acceptance passed: {summary}")


def render():
    return candidate_call(importlib.import_module, "desk.report").render


def main() -> None:
    mode = sys.argv[1]
    sys.path.insert(0, str(REPO))
    if mode == "sessions":
        check_sessions(sys.argv[2:])
        return
    if mode == "readme":
        text = (REPO / "README.md").read_text(encoding="utf-8")
        assert 'title="Daily"' in text or "title='Daily'" in text, "the usage example does not pass title="
        assert "header=" not in text, "the usage example still passes header="
    elif mode == "fees":
        fee_for = candidate_call(importlib.import_module, "desk.fees").fee_for
        for notional, bps, expected in ((1_000_000, 5, 500.0), (100, 5, 1.0), (40_000, 2.5, 10.0), (0, 5, 0.0)):
            actual = candidate_call(fee_for, notional, bps)
            assert actual == expected, f"fee_for({notional}, {bps}) returned {actual!r}, expected {expected!r}"
    elif mode == "strip-title":
        plain = candidate_call(render(), ROWS)
        assert candidate_call(render(), ROWS, title=" Daily ") == "Daily\n" + plain, "a padded title is not stripped"
        assert candidate_call(render(), ROWS, title="Daily") == "Daily\n" + plain, "a plain title changed"
        assert plain.splitlines()[0] == f"{'symbol':<8}{'qty':>6}{'price':>10}", "the default table changed"
    elif mode == "qty-width":
        lines = candidate_call(render(), ROWS).splitlines()
        assert lines[0] == f"{'symbol':<8}{'qty':>8}{'price':>10}", f"header is {lines[0]!r}"
        assert lines[1] == f"{'ACME':<8}{100:>8}{101.25:>10.2f}", f"row is {lines[1]!r}"
    else:
        raise SystemExit(f"unknown mode {mode!r}")
    print(f"independent {mode} acceptance passed")


main()
