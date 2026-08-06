"""Mutation tests for scripts/validate_improvements.py.

Proves the stdlib schema validator actually rejects the failures it claims to — a validator whose
tests only exercise the happy path is the repo's own documented dead-rule mode.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_improvements as vi

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evals/improvements/fi_agent_routing_discovery/record.json"


class ValidateImprovementsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))
        self.schema = json.loads(vi.SCHEMA.read_text(encoding="utf-8"))

    def _errors(self, record: dict) -> list[str]:
        return vi._errors(record, self.schema, self.schema, "record")

    def test_real_record_is_valid(self) -> None:
        # Anchor: the shipped record must pass, or every mutation below is meaningless.
        self.assertEqual([], self._errors(self.record))
        self.assertEqual([], vi.check(ROOT))

    def test_missing_required_field_is_rejected(self) -> None:
        bad = copy.deepcopy(self.record)
        del bad["status"]
        self.assertTrue(any("missing required 'status'" in e for e in self._errors(bad)))

    def test_unknown_top_level_field_is_rejected(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["surprise"] = 1
        self.assertTrue(any("unexpected propert" in e and "surprise" in e for e in self._errors(bad)))

    def test_bad_status_enum_is_rejected(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["status"] = "totally-made-up-status"
        self.assertTrue(any("not in" in e for e in self._errors(bad)))

    def test_schema_version_const_is_enforced(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["schema_version"] = 2
        self.assertTrue(any("must equal 1" in e for e in self._errors(bad)))

    def test_budget_cap_over_maximum_is_rejected(self) -> None:
        # The lifecycle's three-attempts ceiling is a real safety bound; the schema pins it.
        bad = copy.deepcopy(self.record)
        bad["budget"]["max_attempts"] = 4
        errs = self._errors(bad)
        self.assertTrue(any("max_attempts" in e and "maximum" in e for e in errs), errs)

    def test_id_pattern_is_enforced(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["improvement_id"] = "not-an-fi-id"
        self.assertTrue(any("improvement_id" in e and "does not match" in e for e in self._errors(bad)))

    def test_a_parseable_but_wrong_record_on_disk_fails_check(self) -> None:
        # End-to-end through check(): a temp record tree with a broken record must fail.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills/agent-authoring/assets").mkdir(parents=True)
            (root / vi.SCHEMA.relative_to(ROOT)).write_text(
                vi.SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
            )
            rec_dir = root / "evals/improvements/fi_broken"
            rec_dir.mkdir(parents=True)
            bad = copy.deepcopy(self.record)
            del bad["owner"]
            (rec_dir / "record.json").write_text(json.dumps(bad), encoding="utf-8")
            failures = vi.check(root)
        self.assertTrue(any("missing required 'owner'" in e for e in failures), failures)


if __name__ == "__main__":
    unittest.main()
