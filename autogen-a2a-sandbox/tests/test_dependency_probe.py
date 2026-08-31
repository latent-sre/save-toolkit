import sys
import unittest
from pathlib import Path


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX_ROOT))

from interop_sandbox import dependency_probe


EXPECTED_DISTRIBUTIONS = {
    "a2a-sdk": "1.1.2",
    "agent-framework-a2a": "1.0.0b260821",
    "agent-framework-core": "1.16.0",
    "autogen-agentchat": "0.7.5",
}
EXPECTED_TRANSPORT_PINS = {
    "fastapi": "0.116.1",
    "httpx": "0.28.1",
    "sse-starlette": "2.4.1",
    "uvicorn": "0.35.0",
}


class DependencyProbeTests(unittest.TestCase):
    def test_runtime_dependencies_are_the_exact_framework_and_transport_pins(self) -> None:
        requirement_lines = {
            line
            for line in (SANDBOX_ROOT / "requirements.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line and not line.startswith("#")
        }

        self.assertEqual(
            requirement_lines,
            {
                f"{name}=={version}"
                for name, version in {
                    **EXPECTED_DISTRIBUTIONS,
                    **EXPECTED_TRANSPORT_PINS,
                }.items()
            },
        )

    def test_runtime_dependencies_match_the_repository_pin_set(self) -> None:
        sandbox_pins = {
            line
            for line in (SANDBOX_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        }
        repository_pins = {
            line
            for line in (SANDBOX_ROOT.parent / "requirements-dev.txt")
            .read_text(encoding="utf-8")
            .splitlines()
            if line and not line.startswith("#")
        }

        self.assertEqual(set(), sandbox_pins - repository_pins)

    def test_report_contract_accepts_exact_expected_shape(self) -> None:
        report = {
            "distributions": EXPECTED_DISTRIBUTIONS.copy(),
            "probe_version": "autogen-a2a-dependency-probe/v1",
            "python": "3.12.10",
            "surfaces": {
                "a2a_v1_models": "constructed",
                "agent_framework_a2a": "constructed",
                "agent_framework_workflow": "constructed",
                "autogen_graphflow": "constructed",
            },
        }

        self.assertEqual(dependency_probe.validate_report(report), report)

    def test_report_contract_rejects_a_missing_distribution_version(self) -> None:
        report = dependency_probe.expected_report("3.12.10")
        del report["distributions"]["a2a-sdk"]

        with self.assertRaisesRegex(ValueError, "distributions"):
            dependency_probe.validate_report(report)

    def test_report_contract_rejects_an_unexpected_top_level_key(self) -> None:
        report = dependency_probe.expected_report("3.12.10")
        report["unexpected"] = "not closed"

        with self.assertRaisesRegex(ValueError, "top-level"):
            dependency_probe.validate_report(report)


if __name__ == "__main__":
    unittest.main()
