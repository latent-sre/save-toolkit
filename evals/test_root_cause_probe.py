"""Offline instrument calibration, not native model acceptance or reasoning assessment."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import build_probe


ROOT = Path(__file__).resolve().parent
SPEC = build_probe.load_scenario(ROOT / "build-scenarios/build-software-engineer-root-cause-reassessment.yaml")


def use(name, use_id, **inputs):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": use_id, "name": name, "input": inputs}]}}


def result(use_id, **fields):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": use_id, "content": "loaded", **fields}]}}


class RootCauseProbeTests(unittest.TestCase):
    def verdict(self, events, *, ordered=True):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text("\n".join(map(json.dumps, events)), encoding="utf-8")
            trace = build_probe.parse_trace(path)
        ctx = build_probe.Context(SPEC, None, trace, None)
        return build_probe.check_skill_loaded(ctx, {"skill": "root-cause", "before_effects": ordered})[0]

    def test_ordered_load_requires_completed_exact_main_thread_skill(self):
        load = use("Skill", "skill", skill="save-toolkit:root-cause")
        done = result("skill")
        edit = use("Edit", "edit", file_path="retrying.py")
        child = {**load, "parent_tool_use_id": "child"}
        asynchronous = {**done, "tool_use_result": {"isAsync": True}}
        negatives = [
            [], [edit], [load, edit], [load, result("skill", is_error=True), edit],
            [load, result("other"), edit], [load, edit, done], [edit, load, done],
            [child, done, edit], [load, asynchronous, edit],
            [use("Skill", "skill", skill="fake-root-cause"), done, edit],
            [use("Skill", "skill", skill="other:root-cause"), done, edit],
            [use("Skill", "skill", skill="save-toolkit:code-craft"), done, edit],
        ]
        for events in negatives:
            with self.subTest(events=events):
                self.assertFalse(self.verdict(events))
        self.assertTrue(self.verdict([use("Read", "read", file_path="retrying.py"), result("read"), load, done, edit]))
        self.assertTrue(self.verdict([use("Skill", "skill", skill="root-cause"), done, edit]))
        reproduction = use("Bash", "repro", command="python -m unittest")
        self.assertFalse(self.verdict([reproduction, load, done, edit]))
        self.assertTrue(self.verdict([reproduction, load, done, edit], ordered=False))

    def test_initial_ordering_survives_followup_trace_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "followup").mkdir()
            (folder / "stdout.jsonl").write_text("\n".join(map(json.dumps, [
                use("Skill", "s", skill="root-cause"), result("s"), use("Edit", "e")])), encoding="utf-8")
            (folder / "followup/stdout.jsonl").write_text("", encoding="utf-8")
            self.assertEqual(["root-cause"], build_probe.parse_trial_trace(folder).main_skills_before_effects)

    def test_schema_and_artifact_oracle_reject_wrong_repairs(self):
        self.assertEqual([], build_probe.validate_scenario(SPEC))
        invalid = {**SPEC, "checks": [{**SPEC["checks"][0], "before_effects": "true"}]}
        self.assertTrue(any("before_effects must be boolean" in problem
                            for problem in build_probe.validate_scenario(invalid)))
        source = SPEC["fixture"]["files"]["retrying.py"]
        variants = {
            "baseline_failed_repair": (source, False),
            "increase_budget_again": (source.replace("max_attempts=4", "max_attempts=8"), False),
            "disable_retries": (source.replace("except Exception:", "except Exception:\n            raise"), False),
            "swallow_error": (source.replace("                raise", "                return None"), False),
            "supported_repair": (source.replace("except Exception:", "except TimeoutError:"), True),
        }
        oracle = (ROOT / "oracles/root-cause/probe_retry.py").read_text(encoding="utf-8")
        for name, (candidate, expected) in variants.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                folder = Path(tmp)
                (folder / "retrying.py").write_text(candidate, encoding="utf-8")
                (folder / "probe_retry.py").write_text(oracle, encoding="utf-8")
                run = subprocess.run([sys.executable, "probe_retry.py"], cwd=folder,
                                     capture_output=True, text=True, timeout=15)
                self.assertEqual(expected, run.returncode == 0, run.stderr)
                if not expected:
                    self.assertIn("AssertionError", run.stderr)
                if name in {"baseline_failed_repair", "supported_repair"}:
                    for relative, content in SPEC["fixture"]["files"].items():
                        if relative.startswith("tests/"):
                            path = folder / relative
                            path.parent.mkdir(exist_ok=True)
                            path.write_text(content, encoding="utf-8")
                    suite = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
                                           cwd=folder, capture_output=True, text=True, timeout=15)
                    self.assertEqual(expected, suite.returncode == 0, suite.stderr)
                    self.assertIn("Ran 3 tests", suite.stderr)
                    if not expected:
                        self.assertIn("AssertionError: 1 != 4", suite.stderr)
