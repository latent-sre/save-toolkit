"""Require a completed Vitest assertion; separate test failure from runner failure."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def candidate_origin(diagnostics):
    """Use compiler location or the first project stack frame, not error prose."""
    normalized = diagnostics.replace("\\", "/")
    location = re.search(r"^\s*File:\s*(.+?):\d+:\d+\s*$", normalized, re.MULTILINE)
    if location:
        return bool(re.search(r"(?:^|/)src/", location[1]))
    for line in normalized.splitlines():
        frame = re.match(r"\s*❯\s+(.+?):\d+:\d+\s*$", line)
        if not frame or "node_modules/" in frame[1]:
            continue
        # An oracle frame before a candidate frame means its callback crashed.
        return bool(re.search(r"(?:^|[ /])src/", frame[1]))
    return False


def assessment(report, case, exit_code, diagnostics=""):
    assertions = [assertion for suite in report.get("testResults", [])
                  for assertion in suite.get("assertionResults", [])
                  if assertion.get("title", "").startswith(case + " ")]
    if len(assertions) != 1:
        messages = "\n".join(suite.get("message", "") for suite in report.get("testResults", []))
        # Collection errors, including intercepted process.exit, need source
        # attribution: the oracle can terminate prematurely just as a candidate can.
        normalized = messages.replace("\\", "/")
        candidate_source_error = (
            "Transform failed" in normalized and re.search(r"\bsrc/[\w./-]+\.[cm]?[jt]sx?:", normalized)
        ) or re.search(r'Failed to resolve import "\./src/[^"\n]+" from "probe_ui\.test\.tsx"', normalized)
        if candidate_source_error or candidate_origin(diagnostics):
            print(messages)
            return 10
        raise RuntimeError("oracle assertion did not produce exactly one result")
    assertion = assertions[0]
    if assertion.get("status") == "failed":
        messages = "\n".join(assertion.get("failureMessages", []))
        if "AssertionError" in messages or candidate_origin(diagnostics):
            print(messages)
            return 10
        raise RuntimeError("oracle assertion crashed: " + messages)
    if (assertion.get("status") != "passed" or exit_code != 0
            or report.get("numRuntimeErrorTestSuites", 0) or report.get("unhandledErrors") or diagnostics):
        raise RuntimeError("oracle runner did not complete cleanly")
    return 0


def main():
    case = sys.argv[1]
    if case not in {"bar1", "bar2", "bar3", "bar4", "bar5", "bar6", "bar7"}:
        raise ValueError("unknown UI oracle case")
    with tempfile.TemporaryDirectory(prefix="ui-oracle-report-") as directory:
        report = Path(directory) / "result.json"
        junit = Path(directory) / "result.xml"
        result = subprocess.run(["node", "node_modules/vitest/vitest.mjs", "run", "probe_ui.test.tsx",
                                 "-t", case, "--reporter=json", "--reporter=junit",
                                 "--outputFile.json=" + str(report), "--outputFile.junit=" + str(junit)])
        if not report.is_file() or not junit.is_file():
            raise RuntimeError("Vitest ended without a completed assertion report")
        diagnostics = "\n".join(node.text or "" for node in ET.parse(junit).getroot().iter()
                                if node.tag in ("failure", "error"))
        return assessment(json.loads(report.read_text(encoding="utf-8")), case, result.returncode, diagnostics)


if __name__ == "__main__":
    raise SystemExit(main())
