"""Outcome checks for build-python-engineering-add-format.

Text and HTML output (through build_report and the CLI, `--html` included) must match the original
on seeded CSV files. `--format json` must produce the requested shape with the values the text
report shows. Structure: the sales package reads the CSV in one place and has at most two `sum`
calls (per-region and grand total), so a format that copies the aggregation fails.
"""

import ast
import contextlib
import csv
import io
import json
import random
import sys
import tempfile
from pathlib import Path

from oracle_protocol import candidate_call

ORIGINAL = '''
import csv

_cache = {}


def build_report(path, html=False, top=None):
    if path in _cache:
        rows = _cache[path]
    else:
        rows = []
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows.append(r)
        _cache[path] = rows
    totals = {}
    for r in rows:
        if r["status"] != "paid":
            continue
        totals[r["region"]] = totals.get(r["region"], 0) + float(r["amount"])
    items = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    if top:
        items = items[:top]
    if html:
        out = "<table>\\n"
        out += "<tr><th>Region</th><th>Total</th></tr>\\n"
        for region, total in items:
            out += "<tr><td>%s</td><td>%.2f</td></tr>\\n" % (region, total)
        out += "</table>"
        grand = sum(t for _, t in items)
        out += "\\n<p>Grand total: %.2f</p>" % grand
        return out
    else:
        out = "Region      Total\\n"
        for region, total in items:
            out += "%-10s %8.2f\\n" % (region, total)
        grand = sum(t for _, t in items)
        out += "Grand total: %.2f" % grand
        return out
'''


def original_report():
    namespace = {}
    exec(compile(ORIGINAL, "<original>", "exec"), namespace)
    return namespace["build_report"]


def write_csv(path, rng):
    regions = ["north", "south", "east", "west", "central", "islands"]
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "region", "status", "amount"])
        for index in range(rng.randint(0, 40)):
            writer.writerow([index, rng.choice(regions), rng.choice(["paid", "paid", "refunded", "pending"]),
                             rng.choice(["0.10", "19.99", "250", "1000.005", "3.3333"])])


def cli_output(argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            code = candidate_call(cli.main, argv)
        except SystemExit as exc:
            code = exc.code
    assert code in (0, None), f"cli {argv} exited {code!r}"
    return out.getvalue().rstrip("\n")


sys.path.insert(0, str(Path.cwd()))
import sales.cli as cli
import sales.report as report

with tempfile.TemporaryDirectory() as tmp:
    rng = random.Random(20261025)
    for case in range(40):
        path = str(Path(tmp) / f"sales-{case}.csv")
        write_csv(path, rng)
        expected_report = original_report()
        for top in (None, 0, 1, 3):
            text = expected_report(path, top=top)
            html = expected_report(path, html=True, top=top)
            assert candidate_call(report.build_report, path, top=top) == text, f"text output changed (top={top})"
            assert candidate_call(report.build_report, path, html=True, top=top) == html, f"HTML output changed (top={top})"
            top_args = [] if top is None else ["--top", str(top)]
            assert cli_output([path, *top_args]) == text, f"CLI text output changed (top={top})"
            assert cli_output([path, "--html", *top_args]) == html, f"CLI --html output changed (top={top})"
            assert cli_output([path, "--format", "text", *top_args]) == text, "--format text differs from text"
            assert cli_output([path, "--format", "html", *top_args]) == html, "--format html differs from --html"
            document = json.loads(cli_output([path, "--format", "json", *top_args]))
            totals = {}
            with open(path, newline="", encoding="utf-8") as handle:
                for row in csv.DictReader(handle):
                    if row["status"] == "paid":
                        totals[row["region"]] = totals.get(row["region"], 0) + float(row["amount"])
            items = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
            if top:
                items = items[:top]
            expected = {
                "regions": [{"region": region, "total": float("%.2f" % total)} for region, total in items],
                "grand_total": float("%.2f" % sum(total for _, total in items)),
            }
            assert document == expected, f"JSON output {document} != {expected}"
            for entry in document["regions"]:
                assert type(entry["total"]) in (int, float), "JSON totals must be numbers"

calls = {"reader": 0, "sum": 0}
for source in Path("sales").rglob("*.py"):
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name in ("DictReader", "reader"):
                calls["reader"] += 1
            elif name in ("sum", "fsum"):
                calls["sum"] += 1
assert calls["reader"] == 1, f"the CSV is read in {calls['reader']} places"
assert calls["sum"] <= 2, f"{calls['sum']} sum() calls; formats should share one aggregation"
print("report formats: PASS")
