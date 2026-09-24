"""Calibrate the operator-cli requeue oracle against a correct CLI, the seed, and single-rule breaks."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "oracles/operator-cli/check_requeue.py"
SCENARIO = ROOT / "build-scenarios/build-operator-cli-safe-requeue.yaml"

CORRECT = '''"""Requeue every failed settlement job."""

import argparse
import json
import os
import signal
import sys
from pathlib import Path

import jobs_api

LOCK = Path("requeue.lock")


class Stopped(BaseException):
    def __init__(self, signum):
        super().__init__(signum)
        self.signum = signum


def _stop(signum, frame):
    signal.signal(signum, signal.SIG_DFL)
    raise Stopped(signum)


def requeue_one(job_id):
    try:
        jobs_api.requeue(job_id)
        return "succeeded"
    except jobs_api.JobServiceError as exc:
        print(f"error: {job_id}: {exc}", file=sys.stderr)
        return "failed"
    except TimeoutError:
        try:
            return "succeeded" if jobs_api.get_status(job_id) == "queued" else "unknown"
        except Exception:
            return "unknown"


def report(items, as_json):
    if as_json:
        print(json.dumps({"items": items}))
    else:
        for item in items:
            print(f"{item['id']}\\t{item['status']}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    plan = jobs_api.list_failed()
    if args.dry_run:
        print(json.dumps({"plan": plan}) if args.json else "\\n".join(plan))
        return 0
    if not args.yes:
        if not sys.stdin.isatty():
            print("error: pass --yes or run on a terminal", file=sys.stderr)
            return 2
        if input(f"Requeue {len(plan)} jobs? [y/N] ").strip().lower() != "y":
            return 2
    items = [{"id": job_id, "status": "skipped"} for job_id in plan]
    LOCK.write_text("locked", encoding="utf-8")
    try:
        for item in items:
            item["status"] = "unknown"
            item["status"] = requeue_one(item["id"])
    except Stopped as stop:
        report(items, args.json)
        return 128 + stop.signum
    finally:
        LOCK.unlink(missing_ok=True)
    report(items, args.json)
    return 0 if all(item["status"] == "succeeded" for item in items) else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def seed():
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    return spec["fixture"]["files"]["requeue_failed.py"]


class OperatorCliOracleTests(unittest.TestCase):
    def run_oracle(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "requeue_failed.py"
            candidate.write_text(source, encoding="utf-8")
            return subprocess.run([sys.executable, "-I", "-B", str(ORACLE), str(candidate)],
                                  capture_output=True, text=True, timeout=180)

    def test_correct_cli_passes(self):
        result = self.run_oracle(CORRECT)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("contract passed", result.stdout)

    def test_seed_fails_at_the_dry_run(self):
        result = self.run_oracle(seed())
        self.assertNotEqual(0, result.returncode)
        self.assertIn("dry run: exit 2", result.stderr)

    def test_single_rule_breaks_fail_with_their_own_diagnostic(self):
        mutants = [
            ("no SIGTERM handler", CORRECT.replace("    signal.signal(signal.SIGTERM, _stop)\n", ""),
             "SIGTERM: exit 3"),
            ("no report on interrupt", CORRECT.replace("        report(items, args.json)\n        return 128",
                                                       "        return 128"),
             "SIGINT: stdout is not the README's --json object"),
            ("lock left on interrupt", CORRECT.replace("    finally:\n        LOCK.unlink(missing_ok=True)\n",
                                                       "    finally:\n        pass\n"),
             "SIGINT: requeue.lock was left behind"),
            ("work continues after a signal", CORRECT.replace("    raise Stopped(signum)\n", "    return None\n"),
             "SIGINT: exit 0, expected 130"),
            ("pipe confirms", CORRECT.replace("        if not sys.stdin.isatty():\n", "        if False:\n"),
             "piped confirmation: exit 0, expected 2"),
            ("timeout replayed", CORRECT.replace("    except TimeoutError:\n        try:\n",
                                                 "    except TimeoutError:\n        jobs_api.requeue(job_id)\n        try:\n"),
             "timeout: j2 requeued 2 times"),
            ("timeout called a failure", CORRECT.replace(
                '            return "succeeded" if jobs_api.get_status(job_id) == "queued" else "unknown"\n',
                '            return "failed"\n'),
             "timeout: j2 reported 'failed'"),
            ("partial failure exits 0", CORRECT.replace("    return 0 if all(", "    return 0 if True or all("),
             "partial failure: exit 0"),
            ("diagnostics on stdout", CORRECT.replace('print(f"error: {job_id}: {exc}", file=sys.stderr)',
                                                      'print(f"error: {job_id}: {exc}")'),
             "partial failure: stdout is not the README's --json object"),
            ("dry run requeues", CORRECT.replace("    if args.dry_run:\n", "    if args.dry_run:\n        jobs_api.requeue(plan[0])\n"),
             "dry run: requeued ['j1']"),
        ]
        for name, source, diagnostic in mutants:
            with self.subTest(mutant=name):
                self.assertNotEqual(source, CORRECT, "mutation did not apply")
                result = self.run_oracle(source)
                self.assertNotEqual(0, result.returncode)
                self.assertIn(diagnostic, result.stderr)

    def test_scenario_binds_this_oracle_and_the_skill(self):
        spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
        outcome = [check for check in spec["checks"] if "writes_from" in check]
        self.assertEqual([{"_operator_oracle.py": "evals/oracles/operator-cli/check_requeue.py"}],
                         [check["writes_from"] for check in outcome])
        self.assertTrue(any(check["check"] == "skill_loaded" and check["skill"] == "operator-cli"
                            for check in spec["checks"]))
        self.assertNotIn("signal", spec["fixture"]["files"]["jobs_api.py"].lower())


if __name__ == "__main__":
    unittest.main()
