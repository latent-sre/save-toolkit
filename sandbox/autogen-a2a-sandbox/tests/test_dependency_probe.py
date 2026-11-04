import platform
import sys
import unittest
from pathlib import Path


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX_ROOT))

from interop_sandbox import dependency_probe


EXPECTED_DISTRIBUTIONS = dependency_probe.EXPECTED_DISTRIBUTIONS
PYTHON = platform.python_version()
TRANSPORT_PACKAGES = {"fastapi", "httpx", "sse-starlette", "uvicorn"}


class DependencyProbeTests(unittest.TestCase):
    def test_runtime_dependencies_are_the_framework_and_transport_packages_exactly_pinned(self) -> None:
        pins = dependency_probe.pinned_requirements(SANDBOX_ROOT / "requirements.txt")

        self.assertEqual(set(pins), set(dependency_probe.PROBED_DISTRIBUTIONS) | TRANSPORT_PACKAGES)
        self.assertTrue(all(pins.values()))

    def test_report_contract_accepts_exact_expected_shape(self) -> None:
        report = {
            "distributions": EXPECTED_DISTRIBUTIONS.copy(),
            "probe_version": "autogen-a2a-dependency-probe/v1",
            "python": PYTHON,
            "surfaces": {
                "a2a_v1_models": "constructed",
                "agent_framework_a2a": "constructed",
                "agent_framework_workflow": "constructed",
                "autogen_graphflow": "constructed",
            },
        }

        self.assertEqual(dependency_probe.validate_report(report, PYTHON), report)

    def test_report_contract_rejects_a_missing_distribution_version(self) -> None:
        report = dependency_probe.expected_report(PYTHON)
        del report["distributions"]["a2a-sdk"]

        with self.assertRaisesRegex(ValueError, "distributions"):
            dependency_probe.validate_report(report, PYTHON)

    def test_report_contract_rejects_an_interpreter_other_than_the_base_image(self) -> None:
        report = dependency_probe.expected_report(PYTHON)

        with self.assertRaisesRegex(ValueError, "Python version"):
            dependency_probe.validate_report(report, PYTHON + ".1")

    def test_report_contract_rejects_an_unexpected_top_level_key(self) -> None:
        report = dependency_probe.expected_report(PYTHON)
        report["unexpected"] = "not closed"

        with self.assertRaisesRegex(ValueError, "top-level"):
            dependency_probe.validate_report(report, PYTHON)


if __name__ == "__main__":
    unittest.main()
