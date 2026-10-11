"""Opt-in calibration of the incidents-console oracle's write, filter and markup bars.

Set INCIDENTS_CONSOLE_NODE_MODULES to an installed node_modules for the scenario's fixture
(`npm install --ignore-scripts` in a materialized copy), then run this file with pytest. It
exercises bars 5, 10, 11 and 12 with the fixture's own MSW setup; it installs nothing and
establishes no native browser behavior. INCIDENTS_CONSOLE_ORACLE may select an older oracle for
red-before-green evidence.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "build-scenarios/build-software-engineer-incidents-console.yaml"
ORACLE = ROOT / "oracles/incidents-console/probe_ui.test.tsx"
FIXTURES = ROOT / "fixtures/incidents-console"
BARS = ("bar5", "bar10", "bar11", "bar12")
# Each named mutant varies one behavior and must fail its own bar with its own message; every
# other bar must still pass. The reference variants vary only what a correct page may choose.
CASES = [
    ("reference", {}),
    ("reference-service-select", {}),
    ("reference-open-form", {}),
    ("reference-describedby", {}),
    ("client-filter", {"bar5": "never reached the server"}),
    ("no-key", {"bar10": "carried no Idempotency-Key"}),
    ("fresh-key", {"bar10": "different Idempotency-Key"}),
    ("stop-on-409", {"bar10": "never sent it again"}),
    ("summary-errors", {"bar11": "not beside the service field"}),
    ("cleared-input", {"bar11": "cleared the title"}),
    ("html-title", {"bar12": "rendered as HTML"}),
]


@pytest.fixture(scope="module")
def calibration():
    location = os.environ.get("INCIDENTS_CONSOLE_NODE_MODULES")
    if not location:
        pytest.skip("opt in with INCIDENTS_CONSOLE_NODE_MODULES")
    modules = Path(location).resolve(strict=True)
    oracle = Path(os.environ.get("INCIDENTS_CONSOLE_ORACLE", ORACLE)).resolve(strict=True)
    required = ["react", "react-dom", "react-router-dom", "@testing-library/react",
                "@testing-library/jest-dom", "@testing-library/user-event", "vitest", "jsdom",
                "msw", "axe-core"]
    versions = {}
    for package in required:
        manifest = modules / package / "package.json"
        assert manifest.is_file(), f"missing installed {package}: {manifest}; no install attempted"
        versions[package] = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    node = shutil.which("node")
    assert node, "node must already be available"
    fixture = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))["fixture"]["files"]
    print(f"\nconsole oracle calibration; bars={','.join(BARS)}; versions={versions}")

    with tempfile.TemporaryDirectory(prefix="console-oracle-",
                                     dir=os.environ.get("INCIDENTS_CONSOLE_SCRATCH")) as directory:
        work = Path(directory)
        aliases = {package: (modules / package).as_posix() for package in required}
        # Vitest's own module has runtime identity; use its actual entry, not a second package copy.
        aliases["vitest"] = (modules / "vitest/dist/index.js").as_posix()
        (work / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (work / "vitest.config.mjs").write_text(
            "export default " + json.dumps({
                "resolve": {"alias": aliases},
                "test": {"environment": "jsdom", "include": ["*/calibration.test.ts"],
                         "maxWorkers": 2, "testNamePattern": "^bar(5|10|11|12) "},
            }) + ";\n", encoding="utf-8",
        )
        for case, _ in CASES:
            root = work / case
            root.mkdir()
            for name, content in fixture.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            (root / "src/App.tsx").write_text(
                f"const CASE = {json.dumps(case)};\n" + (FIXTURES / "CalibrationApp.tsx").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            shutil.copyfile(oracle, root / "probe_ui.test.tsx")
            # Preserve the oracle bytes and the fixture's original MSW setup/teardown.
            (root / "calibration.test.ts").write_text(
                "import './src/test/setup';\nimport './probe_ui.test';\n", encoding="utf-8",
            )
        report = work / "results.json"
        result = subprocess.run(
            [node, str(modules / "vitest/vitest.mjs"), "run", "--config", "vitest.config.mjs",
             "--reporter=json", f"--outputFile={report}"], cwd=work,
            text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=300,
        )
        assert report.is_file(), result.stdout + result.stderr
        data = json.loads(report.read_text(encoding="utf-8"))
        assert result.returncode in (0, 1), result.stdout + result.stderr
        assert len(data["testResults"]) == len(CASES), result.stdout + result.stderr
        yield {Path(item["name"]).parent.name: item for item in data["testResults"]}


@pytest.mark.parametrize("case,rejected", CASES, ids=[c[0] for c in CASES])
def test_actual_oracle_accepts_references_and_rejects_named_mutants(calibration, case, rejected):
    assertions = {a["title"].split()[0]: a for a in calibration[case]["assertionResults"]}
    assert set(BARS).issubset(assertions), calibration[case]
    for bar in BARS:
        assertion = assertions[bar]
        expected = "failed" if bar in rejected else "passed"
        assert assertion["status"] == expected, (
            f"{case}/{bar}: expected {expected}, got {assertion['status']}; "
            + "\n".join(assertion.get("failureMessages", []))
        )
        if expected == "failed":
            # Confirm the rendered-behavior rejection, not an import, setup, or request failure.
            assert any("AssertionError" in message and rejected[bar] in message
                       for message in assertion["failureMessages"]), assertion
