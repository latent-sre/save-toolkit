"""Run the shipped operator-cli contract test against its reference command."""

from pathlib import Path

from testkit import load_path

ASSET = Path(__file__).resolve().parents[1] / "skills/operator-cli/assets/test_cli_contract.py"

OperatorContractTests = load_path(ASSET, "operator_cli_contract_asset").OperatorContractTests
