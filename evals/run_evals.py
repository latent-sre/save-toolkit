#!/usr/bin/env python3
"""Run (or validate) behavioral evals for the agent + skill fleet.

Implements Anthropic's eval shape — *task* (a scenario: prompt + success
criteria), *trial* (one attempt), *grader* (scores the outcome) — and grades
the OUTCOME (what the response decided), not the path taken. Run each scenario
over several trials because model output varies.

Modes:
  --validate   Check every scenario file parses, has required fields, names a
               real fleet target, and uses known graders. Needs no model — run
               it as your CI gate (or locally) to keep the eval suite honest.
  --list       Print the scenarios.
  --run        Actually invoke the agent and grade. Requires a Claude-enabled
               runner: set CLAUDE_BIN (default "claude"); each trial shells out
               `"$CLAUDE_BIN" -p <prompt>` in a FRESH process (fresh session, so
               authoring context can't mask gaps — per skills best practice).

Exit non-zero if any scenario fails its threshold, or ERRORs (the runner itself broke on a trial —
auth, rate limit, 5xx, network drop, bad flag — never scored PASS/FAIL). CI-friendly.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

import clean_room
import graders


def positive_int(v: str) -> int:
    """argparse type for --trials: reject 0/negatives (a 0 would ZeroDivision at frac = passes/trials)."""
    iv = int(v)
    if iv < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {iv}")
    return iv

try:
    import yaml
except ModuleNotFoundError:
    sys.exit("evals: PyYAML required — `python -m pip install pyyaml`")

ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parent.parent).resolve()
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios"
REQUIRED = ("id", "target", "prompt", "graders")


def load_scenarios() -> list[dict]:
    out = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            data = {"_yaml_error": str(e)}
        if not isinstance(data, dict):
            data = {"_yaml_error": f"expected mapping, got {type(data).__name__}"}
        data["_file"] = f.name
        out.append(data)
    return out


def target_exists(target: str) -> bool:
    return (
        (ROOT / "skills" / target / "SKILL.md").is_file()
        or (ROOT / "agents" / f"{target}.md").is_file()
    )


def validate(scenarios: list[dict]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    for s in scenarios:
        where = s.get("_file", "?")
        for key in REQUIRED:
            if not s.get(key):
                problems.append(f"{where}: missing '{key}'")
        sid = s.get("id")
        if sid:
            if sid in seen:
                problems.append(f"{where}: duplicate id '{sid}'")
            seen.add(sid)
        if s.get("target") and not target_exists(s["target"]):
            problems.append(f"{where}: target '{s['target']}' is not a known skill/agent")
        for g in s.get("graders", []):
            if g.get("type") not in graders.REGISTRY:
                problems.append(f"{where}: unknown grader type '{g.get('type')}'")
                continue
            # Catch a grader missing/with-wrong kwargs at --validate time (CI), instead of
            # passing here and crashing only at --run with a TypeError. A dry run against the
            # empty string exercises the call's binding (required params like of:/pattern:)
            # without needing a model; a binding error is a real suite problem.
            try:
                graders.run_grader(g, "")
            except TypeError as e:
                problems.append(f"{where}: grader '{g.get('type')}' has bad/missing kwargs: {e}")
            except re.error as e:
                problems.append(f"{where}: grader '{g.get('type')}' has an invalid regex: {e}")
    return problems


def run_agent(prompt: str, target: str, env: dict[str, str] | None = None) -> str:
    """Invoke the fleet in a fresh session. Replace with the Agent SDK if preferred.

    `env` is the CLEAN ROOM (clean_room.clean_env()): without it this inherits the operator's
    ~/.claude -- personal skills, personal agents, installed plugins, personal CLAUDE.md -- and the
    suite grades output produced under the influence of a fleet that is not this one.
    """
    claude = os.environ.get("CLAUDE_BIN", "claude")
    hint = f"(Use the {target} skill/agent.)\n\n" if target else ""
    proc = subprocess.run(
        [claude, "-p", hint + prompt, "--plugin-dir", str(ROOT)],
        capture_output=True, text=True, timeout=300, check=False,
        # Decode as UTF-8 explicitly: text=True alone uses the locale codec, which on Windows is
        # cp1252 and dies on the em-dashes/box-drawing the fleet emits. The reader thread then
        # raises, stdout comes back None, and the grader fails with a confusing AttributeError.
        encoding="utf-8", errors="replace", env=env,
    )
    # FAIL LOUD. Returning the error string here would hand it to the TEXT graders, which would
    # score it -- an auth failure would come back as a plausible-looking scenario failure. Gated
    # on proc.returncode (see clean_room.is_auth_failure): this is an SRE fleet whose agents
    # legitimately quote "Not logged in" in healthy output (Splunk triage, auth-incident
    # narratives) -- an ungated scan would abort the whole suite on a healthy rc=0 response that
    # merely mentions the phrase.
    if clean_room.is_auth_failure(proc.stdout, proc.returncode) or clean_room.is_auth_failure(proc.stderr, proc.returncode):
        raise clean_room.AuthUnavailable(
            "a trial came back UNAUTHENTICATED. This is fatal, not a result: the error text would "
            "otherwise be graded as if it were the fleet's answer. Run `claude` and /login."
        )
    if proc.returncode != 0:
        # Same invariant as the auth check above, generalized: a trial that did not complete
        # produced no measurement, whatever broke it (rate limit, 5xx, network drop, bad flag --
        # auth is only one way to get here). Raise, don't return a string: returning it would hand
        # the runner's own error text to the TEXT graders, which would score it as a plausible
        # scenario FAILURE with no hint the runner (not the fleet) broke.
        raise clean_room.RunnerFailed(f"trial exited rc={proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout


def grade_trial(scenario: dict, response: str) -> tuple[bool, list[str]]:
    details = []
    ok_all = True
    for g in scenario["graders"]:
        passed, detail = graders.run_grader(g, response)
        ok_all &= passed
        details.append(f"    [{'PASS' if passed else 'FAIL'}] {g['type']}: {detail}")
    return ok_all, details


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--validate", action="store_true", help="check the suite, no model")
    g.add_argument("--list", action="store_true")
    g.add_argument("--run", action="store_true", help="invoke the agent and grade")
    ap.add_argument("--trials", type=positive_int, default=3, help="trials per scenario (--run); must be >= 1")
    ap.add_argument("--threshold", type=float, default=1.0, help="pass fraction of trials")
    ap.add_argument("--match", help="only scenarios whose id contains this substring (--list/--run)")
    args = ap.parse_args()

    scenarios = load_scenarios()
    if not scenarios:
        print("evals: no scenarios found in evals/scenarios/")
        return 1

    if args.validate:
        problems = validate(scenarios)
        if problems:
            print("EVAL SUITE INVALID:")
            print("\n".join("  - " + p for p in problems))
            return 1
        print(f"eval suite OK — {len(scenarios)} scenario(s), graders and targets resolve.")
        return 0

    if args.match:
        scenarios = [s for s in scenarios if args.match in (s.get("id") or "")]
        if not scenarios:
            print(f"no scenarios match '{args.match}'")
            return 1

    if args.list:
        for s in scenarios:
            print(f"- {s['id']}  (target: {s['target']})\n    {s['prompt'].strip().splitlines()[0]}")
        return 0

    # --run
    # clean_env() wraps ONLY --run -- the path that invokes a model. It raises AuthUnavailable
    # immediately (before a single trial runs) if there are no credentials, so a credential-less
    # invocation aborts with zero scenario results instead of scoring the runner's error text.
    # --validate/--list return above this line and so never touch it -- they run no model and are
    # CI gates that must work on machines with no ~/.claude at all.
    try:
        with clean_room.clean_env() as env:
            failures = 0
            errors = 0
            for s in scenarios:
                passes = 0
                runner_failed = False
                print(f"\n== {s['id']} (target: {s['target']}) ==")
                for t in range(args.trials):
                    try:
                        response = run_agent(s["prompt"], s["target"], env=env)
                    except clean_room.RunnerFailed as e:
                        # The runner, not the fleet, broke on this trial: no measurement exists to
                        # grade. A single unmeasurable trial taints the whole scenario -- we cannot
                        # honestly report a pass fraction with an unknown number of denominators --
                        # so the scenario is ERROR, never PASS/FAIL.
                        print(f"  trial {t + 1}: ERROR (runner) -- {e}")
                        runner_failed = True
                        continue
                    ok, details = grade_trial(s, response)
                    passes += ok
                    print(f"  trial {t + 1}: {'PASS' if ok else 'FAIL'}")
                    if not ok:
                        print("\n".join(details))
                if runner_failed:
                    print(f"  -> ERROR (runner failed on >=1 trial; excluded from pass fraction)")
                    errors += 1
                    continue
                frac = passes / args.trials
                verdict = "PASS" if frac >= args.threshold else "FAIL"
                print(f"  -> {verdict} ({passes}/{args.trials} trials, threshold {args.threshold})")
                failures += verdict == "FAIL"
    except clean_room.AuthUnavailable as e:
        print(f"run_evals: {e}", file=sys.stderr)
        return 1

    scored = len(scenarios) - errors
    print(f"\n{scored - failures}/{scored} scenarios passed" + (f" ({errors} ERRORED, excluded)." if errors else "."))
    return 1 if (failures or errors) else 0


if __name__ == "__main__":
    raise SystemExit(main())
