"""Real-tree build/check/query contract; empty flagship queries fail CI."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ("owner-of", ["fleet-atlas"], "results"),
    ("evidence-for", ["GRAPH-004"], "results"),
    ("impact", ["skills/service-lifecycle/SKILL.md"], "results"),
    ("guidance", ["incident"], "results"),
    ("guidance", ["no-such-fleet-guidance-7fd198cc"], "empty"),
)


def check_response(content: bytes, expected: str) -> dict:
    """One query response body: within budget, the expected outcome, every fact labelled and cited."""
    if len(content) > 20_000:
        raise ValueError("atlas response exceeds its UTF-8 byte budget")
    response = json.loads(content)
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
    # Deferred so that importing check_response does not load the extractor.
    import fleet_atlas_v2 as atlas  # noqa: PLC0415
    import fleet_atlas_v2_artifacts as artifacts  # noqa: PLC0415

    command = [sys.executable, "-B", str(ROOT / "scripts/fleet_atlas_v2.py"), "--root", str(args.root)]
    (verb, terms, expected), *in_process = CASES
    try:
        # Every CLI call re-verifies the whole tree, and build already ends in a verification.
        # Verify once here; one real CLI query keeps the command-line path under test.
        document = artifacts.build(args.root) if args.build else artifacts.verify(args.root)
        print(f"PASS {'build' if args.build else 'check'} -> verified")
        result = subprocess.run([*command, "query", verb, *terms], capture_output=True, timeout=180)
        if result.returncode != 0:
            raise ValueError(f"atlas command failed ({result.returncode}): {result.stdout[:1500]!r}")
        check_response(result.stdout, expected)
        print(f"PASS query {verb} {' '.join(terms)} -> {expected} (command line)")
        for verb, terms, expected in in_process:
            check_response(atlas.query(document, verb, list(terms)), expected)
            print(f"PASS query {verb} {' '.join(terms)} -> {expected}")
    except (OSError, ValueError, TypeError, KeyError, ImportError, RecursionError, SyntaxError,
            subprocess.TimeoutExpired) as error:
        print(f"Fleet atlas contract FAIL: {error}", file=sys.stderr)
        return 1
    print(f"Fleet atlas contract PASS: {len(CASES)} queries on one verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
