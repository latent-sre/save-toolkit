"""Authority and design-record regressions for the principal design lane; no model calls."""

from pathlib import Path
import re
import unittest

import validate_fleet
from test_validate_fleet import DesignLaneAuthorityContract
from testkit import markdown_section


ROOT = Path(__file__).resolve().parents[1]
PRINCIPAL = ROOT / "skills/eng-ladder/references/principal.md"


class PrincipalContractTests(DesignLaneAuthorityContract, unittest.TestCase):
    NAME = "principal-engineer"

    def test_worked_example_carries_every_design_record_slot_and_label(self):
        # A worked example is copied as a shape: a slot it omits is a slot the output drops.
        record = markdown_section(PRINCIPAL.read_text(encoding="utf-8"), "## Design record")
        slots = [slot for slot in re.findall(r"^\| ([A-Z][^|]*?) \|", record, re.MULTILINE)
                 if slot != "Slot"]
        example = [line for line in record.splitlines() if line.startswith("> **")]
        shown = [re.match(r"> \*\*([^*]+)\*\*", line).group(1) for line in example]
        self.assertEqual(slots, shown)
        for required in ("Contracts and consumers", "Verification", "Decision needed"):
            self.assertIn(required, slots)
        for label in validate_fleet.EVIDENCE_TRIAD:
            self.assertIn(label, "\n".join(example))
        by_slot = dict(zip(shown, example))
        # The contract labels each option's costs and constraints, not only the example as a whole.
        options = re.split(r"\(\d\)", by_slot["Options"])[1:]
        self.assertGreater(len(options), 1)
        for number, option in enumerate(options, 1):
            with self.subTest(option=number):
                self.assertTrue(any(label in option for label in validate_fleet.EVIDENCE_TRIAD))
        # Every failure mode carries its detection and the owner of the response.
        modes = [mode for mode in by_slot["Failure modes"].split(":", 1)[1].split(";") if mode.strip()]
        self.assertGreater(len(modes), 1)
        for number, mode in enumerate(modes, 1):
            with self.subTest(failure_mode=number):
                self.assertIn("detected by", mode)
                self.assertIn("owned by", mode)


if __name__ == "__main__":
    unittest.main()
