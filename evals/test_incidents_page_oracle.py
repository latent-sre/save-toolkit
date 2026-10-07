"""Opt-in UI oracle calibration using a caller-selected, already installed dependency tree.

Set INCIDENTS_PAGE_NODE_MODULES and INCIDENTS_PAGE_MODE=bounded|full, then run this
file with pytest. Both modes exercise only bars 1, 2, 3, and 5. Bounded mode
substitutes MSW transport and the unused axe import; full mode uses the scenario's
MSW setup. Neither mode installs anything or establishes native browser behavior.
INCIDENTS_PAGE_ORACLE may select an older oracle for red-before-green evidence.
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
SCENARIO = ROOT / "build-scenarios/build-software-engineer-incidents-page.yaml"
ORACLE = ROOT / "oracles/incidents-page/probe_ui.test.tsx"
FIXTURES = ROOT / "fixtures/incidents-page"
BARS = ("bar1", "bar2", "bar3", "bar5")
FAILURE_REASONS = {
    "bar1": ("no visible loading state", "the loading signal never changed"),
    "bar2": ("without a new visible inline error",),
    "bar3": ("without a new visible empty-state message",),
    "bar5": ("filtered results still show the nonmatching row",),
}
# Each named mutant varies one behavior. All other bars must still pass.
CASES = [
    ("reference", "text", "client", set()),
    ("reference-status", "status", "client", set()),
    ("reference-named-role", "named-role", "client", set()),
    ("reference-labelledby-role", "labelledby-role", "client", set()),
    ("reference-progressbar", "progressbar", "client", set()),
    ("reference-label", "label", "client", set()),
    ("reference-busy", "busy", "client", set()),
    ("same-node", "none", "client", set()),
    ("reference-server", "text", "server", set()),
    ("reference-hidden-rows", "text", "hidden-rows", set()),
    ("hidden-loading", "text", "client", {"bar1"}),
    ("hidden-error", "text", "client", {"bar2"}),
    ("hidden-empty", "text", "client", {"bar3"}),
    ("hidden-child-loading", "none", "client", {"bar1"}),
    ("hidden-child-error", "text", "client", {"bar2"}),
    ("permanent-loading", "text", "client", {"bar1"}),
    ("permanent-error", "text", "client", {"bar2"}),
    ("permanent-empty", "text", "client", {"bar3"}),
    ("remounted-permanent", "text", "client", {"bar1", "bar2", "bar3"}),
    ("outside-main", "text", "client", {"bar1", "bar2", "bar3"}),
    ("url-only", "text", "client", {"bar5"}),
    ("ignore-deep-link", "text", "client", {"bar5"}),
]


@pytest.fixture(scope="module")
def calibration():
    location = os.environ.get("INCIDENTS_PAGE_NODE_MODULES")
    mode = os.environ.get("INCIDENTS_PAGE_MODE")
    if not location or not mode:
        pytest.skip("opt in with INCIDENTS_PAGE_NODE_MODULES and INCIDENTS_PAGE_MODE=bounded|full")
    assert mode in {"bounded", "full"}, f"unsupported calibration mode: {mode}"
    modules = Path(location).resolve(strict=True)
    oracle = Path(os.environ.get("INCIDENTS_PAGE_ORACLE", ORACLE)).resolve(strict=True)
    required = ["react", "react-dom", "react-router-dom", "@testing-library/react",
                "@testing-library/jest-dom", "@testing-library/user-event", "vitest", "jsdom"]
    if mode == "full":
        required += ["msw", "axe-core"]
    versions = {}
    for package in required:
        manifest = modules / package / "package.json"
        assert manifest.is_file(), f"missing installed {package}: {manifest}; no install attempted"
        versions[package] = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    node = shutil.which("node")
    assert node, "node must already be available"
    fixture = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))["fixture"]["files"]
    print(f"\nUI oracle calibration mode={mode}; bars={','.join(BARS)}; versions={versions}")
    if mode == "bounded":
        print("MSW replaced by a fetch transport double; axe not exercised. "
              "Full fixture integration and browser/accessibility behavior remain unverified.")

    with tempfile.TemporaryDirectory(prefix="incidents-oracle-",
                                     dir=os.environ.get("INCIDENTS_PAGE_SCRATCH")) as directory:
        work = Path(directory)
        aliases = {package: (modules / package).as_posix() for package in required}
        # Vitest's own module has runtime identity; use its actual entry, not a second package copy.
        aliases["vitest"] = (modules / "vitest/dist/index.js").as_posix()
        if mode == "bounded":
            transport = work / "transport-double.ts"
            shutil.copyfile(FIXTURES / "transport-double.ts", transport)
            aliases["msw"] = aliases["axe-core"] = transport.as_posix()
        (work / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (work / "vitest.config.mjs").write_text(
            "export default " + json.dumps({
                "resolve": {"alias": aliases},
                "test": {"environment": "jsdom", "include": [
                    "*/probe_ui.test.tsx" if mode == "bounded" else "*/calibration.test.ts"],
                         "maxWorkers": 2, "testNamePattern": "^bar[1235] "},
            }) + ";\n", encoding="utf-8",
        )
        for case, loading, filtering, _ in CASES:
            root = work / case
            root.mkdir()
            for name, content in fixture.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            prefix = (f"const CASE = {json.dumps(case)};\n"
                      f"const LOADING = {json.dumps(loading)};\n"
                      f"const FILTER = {json.dumps(filtering)};\n")
            (root / "src/App.tsx").write_text(
                prefix + (FIXTURES / "CalibrationApp.tsx").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            shutil.copyfile(oracle, root / "probe_ui.test.tsx")
            if mode == "bounded":
                (root / "src/test/server.ts").write_text(
                    "export { server } from '../../../transport-double';\n", encoding="utf-8",
                )
            else:
                # Preserve the oracle bytes and the fixture's original MSW setup/teardown.
                (root / "calibration.test.ts").write_text(
                    "import './src/test/setup';\nimport './probe_ui.test';\n", encoding="utf-8",
                )
        report = work / "results.json"
        result = subprocess.run(
            [node, str(modules / "vitest/vitest.mjs"), "run", "--config", "vitest.config.mjs",
             "--reporter=json", f"--outputFile={report}"], cwd=work,
            text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=240,
        )
        assert report.is_file(), result.stdout + result.stderr
        data = json.loads(report.read_text(encoding="utf-8"))
        assert result.returncode in (0, 1), result.stdout + result.stderr
        assert len(data["testResults"]) == len(CASES), result.stdout + result.stderr
        yield {Path(item["name"]).parent.name: item for item in data["testResults"]}


@pytest.mark.parametrize("case,loading,filtering,rejected", CASES, ids=[c[0] for c in CASES])
def test_actual_oracle_accepts_reference_and_rejects_named_mutants(
    calibration, case, loading, filtering, rejected,
):
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
            assert any("AssertionError" in message and any(
                reason in message for reason in FAILURE_REASONS[bar]
            ) for message in assertion["failureMessages"]), assertion
