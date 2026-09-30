"""Run the shipped operator-cli contract test against its reference command."""

import importlib.util
from pathlib import Path
import unittest

ASSET = Path(__file__).resolve().parents[1] / "skills/operator-cli/assets/test_cli_contract.py"
_spec = importlib.util.spec_from_file_location("operator_cli_contract_asset", ASSET)
_asset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_asset)

OperatorContractTests = _asset.OperatorContractTests


class OperatorGuidanceTests(unittest.TestCase):
    def test_reference_is_optional_and_existing_contracts_remain_authoritative(self):
        guidance = (ASSET.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("optional starter for a compatible new Python", guidance)
        self.assertIn("Read-only commands and existing CLIs", " ".join(guidance.split()))
        self.assertIn("test the applicable cases", guidance)
        self.assertNotIn("keep every case", guidance)
