"""Opt-in UI oracle calibration using a caller-selected, already installed dependency tree.

Set INCIDENTS_PAGE_NODE_MODULES and INCIDENTS_PAGE_MODE=bounded|full, then run this
file with pytest. Both consumers exercise bars 1, 2, 3, and 5; the console also
exercises its problem/request-ID and cursor bars 8 and 9. Bounded mode
substitutes MSW transport and the unused axe import; full mode uses the scenario's
MSW setup. Neither mode installs anything or establishes native browser behavior.
INCIDENTS_PAGE_ORACLE and INCIDENTS_CONSOLE_ORACLE may select older oracles for
red-before-green evidence. Scratch harnesses are deleted after the run.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from probe import assessment as probe_assessment
from probe.workspaces import Workspace
from probe_testkit import tiny_spec, ws_context

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures/incidents-page"
BARS = ("bar1", "bar2", "bar3", "bar5")
FAILURE_REASONS = {
    "bar1": ("no visible loading state", "the loading signal never changed"),
    "bar2": ("without a new visible inline error",),
    "bar3": ("without a new visible empty-state message",),
    "bar5": ("filtered results still show the nonmatching row", "did not restore the filter control"),
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
    ("reference-portalled-button", "text", "portal-button", set()),
    ("reference-portalled-input", "text", "portal-input", set()),
    ("reference-dynamic-button", "text", "portal-button", set()),
    ("reference-dynamic-escaped", "text", "portal-button", set()),
    ("reference-dynamic-input", "text", "portal-input", set()),
    ("reference-portalled-decoy", "text", "portal-button", set()),
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
    ("portal-url-only", "text", "portal-button", {"bar5"}),
    ("portal-ignore-deep-link", "text", "portal-input", {"bar5"}),
    ("portal-stale-control", "text", "portal-button", {"bar5"}),
    ("portal-ambiguous-name", "text", "portal-button", {"bar5"}),
    ("portal-replaced-control", "text", "portal-button", {"bar5"}),
    ("portal-unsupported-name", "text", "portal-button", {"bar5"}),
    ("portal-dynamic-stale-control", "text", "portal-button", {"bar5"}),
    ("portal-dynamic-ambiguous-name", "text", "portal-input", {"bar5"}),
    ("broken-cursor", "text", "client", {"bar9"}),
    ("no-request-id", "text", "client", {"bar8"}),
]


@pytest.fixture(scope="module", params=["incidents-page", "incidents-console"])
def calibration(request: pytest.FixtureRequest) -> Iterator[dict[str, Any]]:
    consumer = request.param
    bars = (*BARS, "bar8", "bar9") if consumer == "incidents-console" else BARS
    location = os.environ.get("INCIDENTS_PAGE_NODE_MODULES")
    mode = os.environ.get("INCIDENTS_PAGE_MODE")
    if not location or not mode:
        pytest.skip("opt in with INCIDENTS_PAGE_NODE_MODULES and INCIDENTS_PAGE_MODE=bounded|full")
    assert mode in {"bounded", "full"}, f"unsupported calibration mode: {mode}"
    modules = Path(location).resolve(strict=True)
    override = "INCIDENTS_CONSOLE_ORACLE" if consumer == "incidents-console" else "INCIDENTS_PAGE_ORACLE"
    oracle = Path(os.environ.get(override, ROOT / "oracles" / consumer / "probe_ui.test.tsx")).resolve(strict=True)
    required = [
        "react",
        "react-dom",
        "react-router-dom",
        "@testing-library/react",
        "@testing-library/jest-dom",
        "@testing-library/user-event",
        "vitest",
        "jsdom",
    ]
    if mode == "full":
        required += ["msw", "axe-core"]
    versions = {}
    for package in required:
        manifest = modules / package / "package.json"
        assert manifest.is_file(), f"missing installed {package}: {manifest}; no install attempted"
        versions[package] = json.loads(manifest.read_text(encoding="utf-8"))["version"]
    node = shutil.which("node")
    assert node, "node must already be available"
    scenario = ROOT / "build-scenarios" / f"build-software-engineer-{consumer}.yaml"
    fixture = yaml.safe_load(scenario.read_text(encoding="utf-8"))["fixture"]["files"]
    print(f"\nUI oracle calibration consumer={consumer}; mode={mode}; bars={','.join(bars)}; versions={versions}")
    if mode == "bounded":
        print(
            "MSW replaced by a fetch transport double; axe not exercised. "
            "Full fixture integration and browser/accessibility behavior remain unverified."
        )

    with tempfile.TemporaryDirectory(
        prefix="incidents-oracle-", dir=os.environ.get("INCIDENTS_PAGE_SCRATCH")
    ) as directory:
        work = Path(directory)
        aliases = {package: (modules / package).as_posix() for package in required}
        # Vitest's own module has runtime identity; use its actual entry, not a second package copy.
        aliases["vitest"] = (modules / "vitest/dist/index.js").as_posix()
        if mode == "bounded":
            transport = work / "transport-double.ts"
            shutil.copyfile(FIXTURES / "transport-double.ts", transport)
            if consumer == "incidents-console":
                transport.write_text(
                    transport.read_text(encoding="utf-8").replace("'/api/incidents'", "'/v1/incidents'"),
                    encoding="utf-8",
                )
            aliases["msw"] = aliases["axe-core"] = transport.as_posix()
        (work / "package.json").write_text('{"type":"module"}', encoding="utf-8")
        (work / "vitest.config.mjs").write_text(
            "export default "
            + json.dumps(
                {
                    "resolve": {"alias": aliases},
                    "test": {
                        "environment": "jsdom",
                        "include": ["*/probe_ui.test.tsx" if mode == "bounded" else "*/calibration.test.ts"],
                        "maxWorkers": 2,
                        "testNamePattern": "^bar[123589] " if consumer == "incidents-console" else "^bar[1235] ",
                    },
                }
            )
            + ";\n",
            encoding="utf-8",
        )
        for case, loading, filtering, _ in CASES:
            root = work / case
            root.mkdir()
            for name, content in fixture.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            prefix = (
                f"const CONSOLE = {str(consumer == 'incidents-console').lower()};\n"
                f"const CASE = {json.dumps(case)};\n"
                f"const LOADING = {json.dumps(loading)};\n"
                f"const FILTER = {json.dumps(filtering)};\n"
            )
            (root / "src/App.tsx").write_text(
                prefix + (FIXTURES / "CalibrationApp.tsx").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            shutil.copyfile(oracle, root / "probe_ui.test.tsx")
            if mode == "bounded":
                (root / "src/test/server.ts").write_text(
                    "export { server } from '../../../transport-double';\n",
                    encoding="utf-8",
                )
            else:
                # Preserve the oracle bytes and the fixture's original MSW setup/teardown.
                (root / "calibration.test.ts").write_text(
                    "import './src/test/setup';\nimport './probe_ui.test';\n",
                    encoding="utf-8",
                )
        report = work / "results.json"
        result = subprocess.run(
            [
                node,
                str(modules / "vitest/vitest.mjs"),
                "run",
                "--config",
                "vitest.config.mjs",
                "--reporter=json",
                f"--outputFile={report}",
            ],
            cwd=work,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=360,
        )
        assert report.is_file(), result.stdout + result.stderr
        data = json.loads(report.read_text(encoding="utf-8"))
        assert result.returncode in (0, 1), result.stdout + result.stderr
        assert len(data["testResults"]) == len(CASES), result.stdout + result.stderr
        yield {
            "results": {Path(item["name"]).parent.name: item for item in data["testResults"]},
            "consumer": consumer,
            "bars": bars,
            "work": work,
            "aliases": aliases,
            "modules": modules,
        }


@pytest.mark.parametrize("case,loading,filtering,rejected", CASES, ids=[c[0] for c in CASES])
def test_actual_oracle_accepts_reference_and_rejects_named_mutants(
    calibration: dict[str, Any],
    case: str,
    loading: str,
    filtering: str,
    rejected: set[str],
) -> None:
    item = calibration["results"][case]
    assertions = {a["title"].split()[0]: a for a in item["assertionResults"]}
    assert set(calibration["bars"]).issubset(assertions), item
    for bar in calibration["bars"]:
        assertion = assertions[bar]
        expected = "failed" if bar in rejected else "passed"
        assert assertion["status"] == expected, (
            f"{case}/{bar}: expected {expected}, got {assertion['status']}; "
            + "\n".join(assertion.get("failureMessages", []))
        )
        if expected == "failed":
            if case in {"portal-ambiguous-name", "portal-dynamic-ambiguous-name", "portal-unsupported-name", "portal-replaced-control"} and bar == "bar5":
                # A different control with the same accessible name must not manufacture a
                # pass. The oracle cannot disambiguate this shape; check_ui treats an Error
                # without candidate-origin frames as INCONCLUSIVE, not a candidate defect.
                diagnostic = {
                    "portal-unsupported-name": "unsupported status combobox name change",
                    "portal-replaced-control": "unsupported status combobox replacement",
                }.get(case, "ambiguous status combobox name")
                assert any(
                    f"Error: {diagnostic}" in message and "AssertionError" not in message
                    for message in assertion["failureMessages"]
                ), assertion
                continue
            # Confirm the rendered-behavior rejection, not an import, setup, or request failure.
            assert any(
                "AssertionError" in message
                and any(
                    reason in message
                    for reason in {
                        **FAILURE_REASONS,
                        "bar8": ("never showed it",),
                        "bar9": ("Unable to find", "did not pass the cursor"),
                    }[bar]
                )
                for message in assertion["failureMessages"]
            ), assertion


@pytest.mark.parametrize("case", ["portal-ambiguous-name", "portal-dynamic-ambiguous-name", "portal-unsupported-name", "portal-replaced-control", "broken-cursor"])
def test_oracle_classification_through_supervised_check(
    calibration: dict[str, Any], case: str
) -> None:
    bar = "bar9" if case == "broken-cursor" else "bar5"
    if bar not in calibration["bars"]:
        pytest.skip("cursor behavior belongs to incidents-console")
    root = calibration["work"] / case
    modules = calibration["modules"]
    entry = root / "node_modules/vitest/vitest.mjs"
    entry.parent.mkdir(parents=True)
    entry.write_text(f"import {json.dumps((modules / 'vitest/vitest.mjs').as_uri())};\n", encoding="utf-8")
    config: dict[str, Any] = {
        "resolve": {"alias": calibration["aliases"]},
        "test": {
            "environment": "jsdom",
            "include": ["probe_ui.test.tsx"],
            "maxWorkers": 2,
        },
    }
    if os.environ["INCIDENTS_PAGE_MODE"] == "full":
        config["test"]["setupFiles"] = ["./src/test/setup.ts"]
    (root / "vitest.config.mjs").write_text("export default " + json.dumps(config) + ";\n", encoding="utf-8")
    for source in (ROOT / "oracles/oracle_protocol.py", ROOT / "oracles" / calibration["consumer"] / "check_ui.py"):
        shutil.copyfile(source, root / source.name)
    command = f'"{sys.executable}" -I -B oracle_protocol.py check_ui.py {bar} > supervised.stdout 2> supervised.stderr'
    spec = tiny_spec(
        checks=[
            {
                "check": "command_exit_zero",
                "text": "classify observed UI behavior",
                "command": command,
                "failure_exit_code": 10,
                "timeout": 60,
            }
        ]
    )
    workspace = Workspace(root, root, root, root, 0, "calibration")
    result = probe_assessment.grade(ws_context(spec, workspace))
    if case == "broken-cursor":
        assert result["status"] == "FAIL", result
        diagnostics = (root / "supervised.stdout").read_text(encoding="utf-8")
        assert "AssertionError" in diagnostics, diagnostics
        assert "did not pass the cursor" in diagnostics, diagnostics
        return
    assert result["status"] == "INCONCLUSIVE", result
    assert "exit 1" in result["inconclusive"], result
    assert "not the declared failure exit 10" in result["inconclusive"], result
    diagnostics = (root / "supervised.stderr").read_text(encoding="utf-8")
    diagnostic = {
        "portal-unsupported-name": "unsupported status combobox name change",
        "portal-replaced-control": "unsupported status combobox replacement",
    }.get(case, "ambiguous status combobox name")
    assert f"oracle assertion crashed: Error: {diagnostic}" in diagnostics, diagnostics
    assert "AssertionError" not in diagnostics, diagnostics
