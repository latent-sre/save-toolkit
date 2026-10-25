"""No-model CLI and saved-record controls for the bounded four-model smoke block."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import testing_block as block


class TestingBlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan = block.prepare(block.DEFAULT_MANIFEST, block.ROOT, self.root / "block", "native-host", "codex-host")

    def record(self, index: int = 2, **changes: object) -> Path:
        slot = self.plan["slots"][index]
        record = {
            "schema": "codex-record-v1",
            "scenario_id": slot["case"],
            "case_sha256": slot["case_sha256"],
            "model_requested": slot["model"],
            "pin": "prompt-injected",
            "reasoning_effort": "high",
            "candidate": {"plugin_source_sha256": self.plan["plugin_sha256"]},
            "shared_runner": {"runner_source_sha256": self.plan["runner_sha256"]},
            "adapter_sha256": self.plan["adapter_sha256"],
            "host": {
                "hostname": "codex-host",
                "account_id": "uid:1001",
                "elevated": False,
                "identity_source": "posix_effective_uid",
            },
            "runtime": {"cli_version": "synthetic", "host_platform": {"system": "Linux"}},
            "thread_id": f"synthetic-thread-{index}",
            "identity_verified": True,
            "state": "FAIL",
            "cost_usd": None,
            "evidence_complete": True,
        }
        record.update(changes)
        path = self.root / "records" / f"trial-{slot.get('trial', 1)}" / str(index) / "record.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        record["runtime"]["host_identity"] = record["host"]
        session = "\n".join(
            json.dumps(row)
            for row in [
                {"type": "session_meta", "payload": {"id": record["thread_id"]}},
                {"type": "turn_context", "payload": {"model": slot["model"]}},
            ]
        )
        (path.parent / "session.jsonl").write_text(session)
        record["artifacts"] = {"session.jsonl": hashlib.sha256(session.encode()).hexdigest()}
        path.write_text(json.dumps(record))
        return path

    def test_prepare_cli_binds_eight_slots_without_launch_and_refuses_overwrite(self) -> None:
        self.assertEqual(8, len(self.plan["slots"]))
        self.assertEqual(5, len(self.plan["commands"]))
        self.assertTrue(all(isinstance(command["argv"], list) for command in self.plan["commands"]))
        argv = [sys.executable, str(block.__file__), "validate", str(self.root / "block")]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        prepare_argv = [
            sys.executable,
            str(block.__file__),
            "prepare",
            "--candidate-root",
            str(block.ROOT),
            "--native-host",
            "native-host",
            "--codex-host",
            "codex-host",
            "--out",
            str(self.root / "cli"),
        ]
        result = subprocess.run(prepare_argv, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        result = subprocess.run(prepare_argv, capture_output=True, text=True)
        self.assertEqual(3, result.returncode)
        with self.assertRaises(FileExistsError):
            block.prepare(block.DEFAULT_MANIFEST, block.ROOT, self.root / "block", "native-host", "codex-host")

    def test_validation_detects_changed_binding_and_plan(self) -> None:
        path = self.root / "block/case-bindings.json"
        path.write_text("[]")
        with self.assertRaisesRegex(ValueError, "binding"):
            block.validate(self.root / "block")
        path.write_text(json.dumps(self.plan["case_bindings"]))
        plan_path = self.root / "block/plan.json"
        changed = dict(self.plan, plugin_sha256="0" * 64)
        plan_path.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "digest"):
            block.validate(self.root / "block")

    def test_failures_count_missing_stays_visible_unknown_cost_blocks_spend(self) -> None:
        self.record()
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(1, report["attempt_count"])
        self.assertEqual(7, report["missing_slots"])
        self.assertEqual("FAIL", report["attempts"][0]["state"])
        self.assertIsNone(report["cost_usd"])
        self.assertFalse(report["ready_for_further_spend"])
        self.assertNotIn("verdict", report)
        argv = [
            sys.executable,
            str(block.__file__),
            "report",
            str(self.root / "block"),
            "--records",
            str(self.root / "records"),
            "--out",
            str(self.root / "report.json"),
        ]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, json.loads((self.root / "report.json").read_text())["attempt_count"])
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(3, result.returncode)

    def test_model_mismatch_and_duplicate_attempt_remain_counted(self) -> None:
        path = self.record()
        duplicate = path.parent / "retry" / "record.json"
        duplicate.parent.mkdir()
        duplicate.write_bytes(path.read_bytes())
        self.record(3, model_requested="other-model")
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(3, report["attempt_count"])
        self.assertTrue(any("duplicate" in error for error in report["problems"]))
        self.assertTrue(any("unplanned" in error for error in report["problems"]))
        self.assertFalse(report["ready_for_further_spend"])

    def native_record(self) -> Path:
        slot = self.plan["slots"][0]
        fixture = block.ROOT / "evals/fixtures/v1-bundle/runs/eval-synthetic-gain/candidate/run-1/record.json"
        raw = json.loads(fixture.read_text())
        raw["case"].update(id=slot["case"], case_sha256=slot["case_sha256"])
        raw["candidate"]["plugin_source_sha256"] = self.plan["plugin_sha256"]
        raw["runner"]["runner_source_sha256"] = self.plan["runner_sha256"]
        raw["conditions"].update(requested_model=slot["model"], observed_models=[slot["model"]])
        raw["conditions"]["runtime"]["host_identity"]["hostname"] = "native-host"
        raw["cost"].update(judge_usd=0.0, known_usd=0.1, judge_calls=0, judge_live_calls=0)
        path = self.root / "records/native/record.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(raw))
        return path

    def test_native_v1_is_validated_and_kept_separate(self) -> None:
        path = self.native_record()
        raw = json.loads(path.read_text())
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual("PASS", report["attempts"][0]["state"])
        self.assertIsNone(report["attempts"][0]["record_execution_profile"])
        raw["conditions"]["observed_models"] = ["wrong-model"]
        path.write_text(json.dumps(raw))
        report = block.report(self.root / "block", self.root / "records")
        self.assertTrue(report["attempts"][0]["problems"])

    def test_missing_runtime_identity_remains_an_explicit_gap(self) -> None:
        path = self.native_record()
        raw = json.loads(path.read_text())
        raw["conditions"]["runtime"]["cli_version"] = None
        path.write_text(json.dumps(raw))
        report = block.report(self.root / "block", self.root / "records")
        self.assertTrue(any("runtime identity" in problem for problem in report["problems"]))

    def test_saved_codex_observed_model_mismatch_is_not_hidden_by_requested_model(self) -> None:
        path = self.record()
        session = (path.parent / "session.jsonl").read_text().replace(self.plan["slots"][2]["model"], "wrong-model")
        (path.parent / "session.jsonl").write_text(session)
        raw = json.loads(path.read_text())
        raw["artifacts"]["session.jsonl"] = hashlib.sha256(session.encode()).hexdigest()
        path.write_text(json.dumps(raw))
        report = block.report(self.root / "block", self.root / "records")
        self.assertTrue(any("observed Codex model" in problem for problem in report["problems"]))

    def test_known_total_does_not_use_an_inconsistent_native_floor(self) -> None:
        path = self.native_record()
        raw = json.loads(path.read_text())
        raw["conditions"]["observed_models"] = [raw["conditions"]["requested_model"]]
        raw["cost"]["known_usd"] = 0.0
        path.write_text(json.dumps(raw))
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(0.1, report["cost_usd"])
        self.assertTrue(any("cost floor" in error for error in report["problems"]))

    def test_recordless_native_attempt_is_counted_but_not_a_measurement(self) -> None:
        folder = self.root / "records/native" / ("eval-" + block.CASES[0]) / "claude-sonnet-5-5/run-1"
        folder.mkdir(parents=True)
        (folder / "attempt.json").write_text("{}")
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(1, report["attempt_count"])
        self.assertEqual(7, report["missing_slots"])
        self.assertIsNone(report["attempts"][0]["state"])
        self.assertTrue(report["attempts"][0]["problems"])

    def test_invalid_attempt_and_symlink_do_not_disappear(self) -> None:
        self.record()
        path = self.root / "records/broken/record.json"
        path.parent.mkdir()
        path.write_text("not json")
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(2, report["attempt_count"])
        self.assertEqual(2, report["unknown_cost_attempts"])
        (self.root / "records/linked").symlink_to(self.root / "block", target_is_directory=True)
        with self.assertRaises(ValueError):
            block.report(self.root / "block", self.root / "records")

    def selected_manifest(self, trials: int = 3) -> Path:
        manifest = json.loads(block.DEFAULT_MANIFEST.read_text())
        manifest.update(
            cases=[
                *block.CASES,
                "build-injection-log-role-benign",
                "build-injection-log-role-malicious",
                "build-reliability-engineer-proportionate-options",
            ],
            trials_per_case=trials,
            attempt_limit=5 * 4 * trials,
            approved_total_usd=12.5,
        )
        path = self.root / "selected.json"
        path.write_text(json.dumps(manifest))
        return path

    def test_cli_selects_complete_existing_pairs_and_singleton_with_three_trials(self) -> None:
        manifest = self.selected_manifest()
        argv = [
            sys.executable,
            str(block.__file__),
            "prepare",
            "--manifest",
            str(manifest),
            "--candidate-root",
            str(block.ROOT),
            "--native-host",
            "native-host",
            "--codex-host",
            "codex-host",
            "--out",
            str(self.root / "selected"),
        ]
        result = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        plan = block.load_plan(self.root / "selected")
        self.assertEqual(60, len(plan["slots"]))
        self.assertEqual(42, len(plan["commands"]))
        self.assertEqual({1, 2, 3}, {slot["trial"] for slot in plan["slots"]})
        self.assertEqual(12.5, plan["budget"]["approved_total_usd"])
        native = [cmd for cmd in plan["commands"] if cmd["profile"] == "native-claude-cli"]
        self.assertEqual({"0", "1", "2"}, {cmd["argv"][cmd["argv"].index("--run-offset") + 1] for cmd in native})
        codex = [cmd for cmd in plan["commands"] if cmd["profile"] == "codex-structured-file-v1"]
        self.assertEqual(
            {"log", "log-role", "reliability"}, {cmd["argv"][cmd["argv"].index("--pair") + 1] for cmd in codex}
        )
        self.assertEqual(60, block.validate(self.root / "selected")["attempt_limit"])
        self.assertEqual(12, sum(slot["semantic_review_required"] for slot in plan["slots"]))

    def test_repeated_slots_stay_separate_and_semantic_review_is_not_acceptance(self) -> None:
        self.plan = block.prepare(
            self.selected_manifest(2), block.ROOT, self.root / "selected", "native-host", "codex-host"
        )
        for trial, state in ((1, "FAIL"), (2, "PASS")):
            index = next(
                index
                for index, slot in enumerate(self.plan["slots"])
                if slot["model"] == "gpt-6-luna" and slot["case"] == block.CASES[0] and slot["trial"] == trial
            )
            self.record(index, state=state)
        index = next(
            index
            for index, slot in enumerate(self.plan["slots"])
            if slot["model"] == "gpt-6-luna" and slot["semantic_review_required"] and slot["trial"] == 2
        )
        self.record(index, state="PASS", semantic_review_required=True)
        path = self.native_record()
        native = json.loads(path.read_text())
        native["attempt"]["slot"] = 2
        path.write_text(json.dumps(native))
        report = block.report(self.root / "selected", self.root / "records")
        self.assertEqual(4, report["attempt_count"])
        self.assertEqual(36, report["missing_slots"])
        self.assertFalse(any(slot["status"] in {"duplicate", "duplicate_execution"} for slot in report["slots"]))
        self.assertTrue(all(row["fresh_coverage"] for row in report["attempts"]))
        reviewed = next(row for row in report["attempts"] if row.get("semantic_review_required"))
        self.assertEqual("PASS", reviewed["state"])
        self.assertEqual("required_not_assessed", reviewed["semantic_review_status"])
        self.assertIsNone(report["cost_usd"])

    def test_copied_execution_cannot_fill_another_trial_but_keeps_both_costs(self) -> None:
        self.plan = block.prepare(
            self.selected_manifest(2), block.ROOT, self.root / "selected", "native-host", "codex-host"
        )
        index = next(
            index
            for index, slot in enumerate(self.plan["slots"])
            if slot["model"] == "gpt-6-luna" and slot["case"] == block.CASES[0] and slot["trial"] == 1
        )
        source = self.record(index, state="PASS", cost_usd=0.2)
        copied = self.root / "records/trial-2/copied"
        copied.mkdir(parents=True)
        for name in ("record.json", "session.jsonl"):
            (copied / name).write_bytes((source.parent / name).read_bytes())
        report = block.report(self.root / "selected", self.root / "records")
        self.assertEqual(2, report["attempt_count"])
        self.assertEqual(0.4, report["known_usd"])
        self.assertEqual(2, sum(slot["status"] == "duplicate_execution" for slot in report["slots"]))
        self.assertTrue(all(not row["fresh_coverage"] for row in report["attempts"]))
        self.assertFalse(report["ready_for_further_spend"])

    def test_reused_execution_is_detected_across_case_and_model_buckets(self) -> None:
        self.record(2, state="PASS", cost_usd=0.1, thread_id="reused-thread")
        self.record(5, state="PASS", cost_usd=0.1, thread_id="reused-thread")
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(2, report["attempt_count"])
        self.assertTrue(all(row.get("duplicate_execution") for row in report["attempts"]))
        self.assertTrue(any("duplicate execution" in problem for problem in report["problems"]))

    def test_legacy_default_plan_without_trial_fields_remains_reportable(self) -> None:
        plan_path = self.root / "block/plan.json"
        legacy = json.loads(plan_path.read_text())
        for slot in legacy["slots"]:
            slot.pop("trial")
            slot.pop("semantic_review_required")
        legacy["plan_sha256"] = block.digest({key: value for key, value in legacy.items() if key != "plan_sha256"})
        plan_path.write_text(json.dumps(legacy))
        self.record()
        report = block.report(self.root / "block", self.root / "records")
        self.assertEqual(1, report["attempt_count"])
        self.assertEqual(7, report["missing_slots"])

    def test_gcp_pair_is_admitted_together_and_marked_for_semantic_review(self) -> None:
        path = self.selected_manifest(1)
        manifest = json.loads(path.read_text())
        manifest.update(cases=["build-gcp01-startup-b", "build-gcp01-startup-a"], attempt_limit=8)
        path.write_text(json.dumps(manifest))
        plan = block.prepare(path, block.ROOT, self.root / "gcp", "native-host", "codex-host")
        self.assertTrue(all(slot["semantic_review_required"] for slot in plan["slots"]))
        self.assertEqual("build-gcp01-startup-a", plan["slots"][0]["case"])
        self.assertEqual(5, len(plan["commands"]))

    def test_incomplete_pairs_unsupported_profiles_and_invalid_limits_are_refused(self) -> None:
        path = self.selected_manifest()
        original = json.loads(path.read_text())
        for change in (
            {"cases": [block.CASES[0]]},
            {"trials_per_case": 4},
            {"trials_per_case": True},
            {"approved_total_usd": -1},
            {"approved_total_usd": True},
            {"attempt_limit": 1},
            {"models": [{"model": "gpt-6-luna", "profile": "other", "host_group": "codex"}]},
        ):
            with self.subTest(change=change):
                path.write_text(json.dumps({**original, **change}))
                with self.assertRaises(ValueError):
                    block.prepare(path, block.ROOT, self.root / "bad", "native-host", "codex-host")

    def test_unsupported_cases_profiles_and_path_escape_are_rejected(self) -> None:
        for field, value in (("cases", ["unsupported"]), ("models", [])):
            manifest = json.loads(block.DEFAULT_MANIFEST.read_text())
            manifest[field] = value
            path = self.root / f"{field}.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                block.prepare(path, block.ROOT, self.root / field, "native-host", "codex-host")
        with self.assertRaises(ValueError):
            block.prepare(block.DEFAULT_MANIFEST, block.ROOT, self.root / ".." / "escape", "a", "b")


if __name__ == "__main__":
    unittest.main()
