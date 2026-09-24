"""Run the shipped operator-cli contract test against its reference command."""

import importlib.util
from pathlib import Path

ASSET = Path(__file__).resolve().parents[1] / "skills/operator-cli/assets/test_cli_contract.py"
_spec = importlib.util.spec_from_file_location("operator_cli_contract_asset", ASSET)
_asset = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_asset)

OperatorContractTests = _asset.OperatorContractTests
