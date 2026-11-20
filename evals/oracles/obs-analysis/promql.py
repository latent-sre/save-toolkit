"""Evaluate the two numbered PromQL answers against independent, hand-calculated app vectors."""

import json
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


# At t=10m the five-minute rate uses the samples from t=6m through t=10m.
# Checkout's success counter resets independently. Its production deltas are
# 80 successes, 4 client errors and 8 server errors; search has 72, 8 and 20.
REQUESTS = [
    ("checkout", "prod", "a", "200", "0+20x5 160 175 190 15 30"),
    ("checkout", "prod", "b", "200", "0+20x5 110 115 120 125 130"),
    ("checkout", "prod", "b", "404", "0+2x5 20 21 22 23 24"),
    ("checkout", "prod", "b", "500", "0+1x5 5 6 7 7 8"),
    ("checkout", "prod", "b", "503", "0+2x5 10 10 11 12 15"),
    ("search", "prod", "c", "200", "0+60x5 320 340 360 376 392"),
    ("search", "prod", "c", "404", "0+3x5 20 22 24 26 28"),
    ("search", "prod", "c", "500", "0+2x5 16 18 20 23 28"),
    ("search", "prod", "c", "511", "0+1x5 10 11 15 16 18"),
    ("checkout", "stage", "d", "200", "0+100x10"),
    ("checkout", "stage", "d", "503", "0+30x10"),
]
# Across production instances the <=0.5, <=1 and +Inf buckets gained
# (36, 40, 40) observations in checkout and (20, 40, 40) in search.
# The 38th observation interpolates to 0.75 and 0.95 seconds respectively.
BUCKETS = [
    ("checkout", "prod", "a", "0.5", "0+10x5 110 114 118 4 8"),
    ("checkout", "prod", "a", "1", "0+20x5 200 205 210 5 10"),
    ("checkout", "prod", "a", "+Inf", "0+25x5 240 245 250 5 10"),
    ("checkout", "prod", "b", "0.5", "0+5x5 100 105 110 115 120"),
    ("checkout", "prod", "b", "1", "0+20x5 170 175 180 185 190"),
    ("checkout", "prod", "b", "+Inf", "0+40x5 220 225 230 235 240"),
    ("search", "prod", "c", "0.5", "0+15x5 130 130 135 140 150"),
    ("search", "prod", "c", "1", "0+25x5 150 160 170 180 190"),
    ("search", "prod", "c", "+Inf", "0+45x5 250 260 270 280 290"),
    ("checkout", "stage", "d", "0.5", "0+1x10"),
    ("checkout", "stage", "d", "1", "0+100x10"),
    ("checkout", "stage", "d", "+Inf", "0+100x10"),
]


def _fenced_query(text: str) -> str:
    """Unwrap exactly one complete block; a second block is another answer."""
    lines = text.splitlines()
    if (len(lines) < 3 or not re.fullmatch(r"```(?:promql|prometheus)?", lines[0].strip(), re.I)
            or lines[-1].strip() != "```" or any(line.lstrip().startswith("```") for line in lines[1:-1])):
        return ""
    return "\n".join(lines[1:-1]).strip()


NUMBERED_LINE = re.compile(
    r"^[ \t]*(?:\*\*)?(?:#[ \t]*\(?(?P<comment>\d+)[.):]?|\(?(?P<label>\d+)[.):])"
    r"(?:\*\*)?(?=[ \t]|$)[ \t]*(?P<caption>[^\n]*)$", re.M
)


def _queries(response: str) -> list[str]:
    text = response.strip()
    if text.startswith("```"):
        text = _fenced_query(text)
    headings = list(NUMBERED_LINE.finditer(text))
    if ([m["comment"] or m["label"] for m in headings] != ["1", "2"]
            or text[:headings[0].start()].strip()):
        return []
    queries = []
    for heading, end in zip(headings, (headings[1].start(), len(text)), strict=True):
        body = text[heading.end():end].strip()
        caption = heading["caption"].strip()
        # In a numbered comment the whole line is a label. A separate fenced
        # block also makes its one-line title unambiguous.
        if caption and not heading["comment"] and not body.startswith("```"):
            body = (caption + "\n" + body).strip()
        if body.startswith("```"):
            body = _fenced_query(body)
        elif body.startswith("`") and body.endswith("`"):
            body = body[1:-1].strip()
        if not body:
            return []
        queries.append(body)
    return queries


def _fixture(ratio: str, p95: str) -> dict:
    series = [
        {"series": f'http_requests_total{{app="{app}",env="{env}",instance="{inst}",status="{status}"}}',
         "values": values}
        for app, env, inst, status, values in REQUESTS
    ] + [
        {"series": f'http_request_duration_seconds_bucket{{app="{app}",env="{env}",instance="{inst}",le="{le}"}}',
         "values": values}
        for app, env, inst, le, values in BUCKETS
    ]
    expressions = [
        {"expr": expression, "eval_time": "10m", "exp_samples": [
            {"labels": '{app="checkout"}', "value": checkout},
            {"labels": '{app="search"}', "value": search},
        ]}
        for expression, checkout, search in ((ratio, 8 / 92, 0.2), (p95, 0.75, 0.95))
    ]
    return {"fuzzy_compare": True, "tests": [
        {"name": "app vectors", "interval": "1m", "input_series": series, "promql_expr_test": expressions}
    ]}


def check(response: str) -> tuple[bool, str]:
    queries = _queries(response.replace("\r\n", "\n"))
    if len(queries) != 2:
        return False, "expected two numbered PromQL expressions"
    ratio, p95 = queries

    tool = shutil.which("promtool")
    if not tool:
        return False, "instrument: promtool is missing from PATH"
    try:
        version = subprocess.run([tool, "--version"], capture_output=True, text=True, timeout=5, check=True)
        identity = (version.stdout or version.stderr).strip().splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="obs-promql-") as temp:
            directory = Path(temp)
            (directory / "fixture.yml").write_text(json.dumps(_fixture(ratio, p95)), encoding="utf-8")
            result = subprocess.run(
                [tool, "test", "rules", "--junit=results.xml", "fixture.yml"], cwd=directory,
                capture_output=True, encoding="utf-8", errors="replace", timeout=30,
            )
            report_path = directory / "results.xml"
            if not report_path.is_file():
                return False, f"instrument: {identity} produced no JUnit report: {result.stderr.strip()[-400:]}"
            report = ET.parse(report_path)
    except (OSError, IndexError, subprocess.SubprocessError, ET.ParseError) as exc:
        return False, f"instrument: promtool could not evaluate the fixture: {exc}"

    case = report.find("./testsuite/testcase[@name='app vectors']")
    if case is not None:
        if result.returncode == 0 and not list(case):
            return True, f"{identity}: both five-minute app vectors match"
        failures = [item.text or "" for item in case.findall("failure")]
        if result.returncode == 1 and failures and all(item.lstrip().startswith("expr:") for item in failures):
            return False, f"{identity}: {'; '.join(failures).strip()}"
    return False, f"instrument: {identity} produced no usable expression verdict: {result.stderr[-400:]}"
