"""Real-tree build/check/query contract; empty flagship queries fail CI."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("owner-of", ["fleet-atlas"], "results"),
    ("evidence-for", ["GRAPH-004"], "results"),
    ("impact", ["skills/service-lifecycle/SKILL.md"], "results"),
    ("guidance", ["incident"], "results"),
    ("guidance", ["no-such-fleet-guidance-7fd198cc"], "empty"),
)


def check_response(process: subprocess.CompletedProcess, expected: str) -> dict:
    if process.returncode != 0:
        raise ValueError(f"atlas command failed ({process.returncode}): {process.stdout[:1500]!r}")
    if len(process.stdout) > 20_000:
        raise ValueError("atlas response exceeds its UTF-8 byte budget")
    response = json.loads(process.stdout)
    if response.get("outcome") != expected:
        raise ValueError(f"expected {expected}, received {response.get('outcome')}")
    if expected == "results":
        if not response.get("results"):
            raise ValueError("flagship query returned an empty result list")
        for fact in response["results"]:
            if not fact.get("label") or not fact.get("class") or not fact.get("citations"):
                raise ValueError("query fact lacks evidence class, label, or citations")
    elif expected == "empty" and response.get("results"):
        raise ValueError("empty outcome carries results")
    return response


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--build", action="store_true", help="build outputs before checking; maintenance/CI only")
    args = parser.parse_args(argv)
    command = [sys.executable, "-B", str(ROOT / "scripts/fleet_atlas_v2.py"), "--root", str(args.root)]
    requests = [(["build"], "verified")] if args.build else []
    requests += [(["check"], "verified")]
    requests += [(["query", verb, *terms], expected) for verb, terms, expected in CASES]
    try:
        for arguments, expected in requests:
            result = subprocess.run(command + arguments, capture_output=True, timeout=180)
            check_response(result, expected)
            print(f"PASS {' '.join(arguments)} -> {expected}")
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Fleet atlas contract FAIL: {error}", file=sys.stderr)
        return 1
    print(f"Fleet atlas contract PASS: {len(requests)} commands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
