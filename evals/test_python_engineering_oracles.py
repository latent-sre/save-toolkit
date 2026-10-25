"""Calibrate the python-engineering build oracles: a correct artifact passes (exit 0), the seed and
named counterexamples fail as candidate failures (exit 10), never as oracle crashes (exit 1)."""

import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from probe_testkit import scenario_file, write_tree

EVALS = Path(__file__).resolve().parent
REPO = EVALS.parent
SCENARIOS = EVALS / "build-scenarios"


def materialize(root, name, overlay=None, removed=()):
    spec = scenario_file(SCENARIOS / f"build-python-engineering-{name}.yaml")
    write_tree(root, spec["fixture"]["files"])
    for path in removed:
        (root / path).unlink()
    write_tree(root, overlay or {})
    return spec


def grade(root, name, overlay=None, removed=()):
    spec = materialize(root, name, overlay, removed)
    (check,) = [c for c in spec["checks"] if "oracle_protocol.py" in c.get("command", "")]
    for target, source in check["writes_from"].items():
        (root / target).write_text((REPO / source).read_text(encoding="utf-8"), encoding="utf-8")
    argv = shlex.split(check["command"])
    assert argv[0] == "python"
    result = subprocess.run([sys.executable, *argv[1:]], cwd=root, capture_output=True, text=True,
                            encoding="utf-8", timeout=600)
    return result.returncode, (result.stdout + result.stderr)[-3000:]


def fixture_suite(root, name):
    materialize(root, name)
    return subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                          cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=300)


def ruff(*args, cwd):
    executable = shutil.which("ruff")
    command = [executable] if executable else [sys.executable, "-m", "ruff"]
    return subprocess.run([*command, *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=120)


# --- A: requirement policy -------------------------------------------------------------------------

POLICY_GOOD = '''"""Compare an installed inventory with a requirement policy."""

from collections.abc import Iterable, Mapping
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def load_policy(path: str | Path) -> list[Requirement]:
    requirements = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            requirements.append(Requirement(line))
    return requirements


def violations(inventory: Mapping[str, str], policy: Iterable[Requirement]) -> list[tuple[str, str, Requirement]]:
    installed = {canonicalize_name(name): (name, version) for name, version in inventory.items()}
    found = []
    for requirement in policy:
        if requirement.marker is not None and not requirement.marker.evaluate():
            continue
        match = installed.get(canonicalize_name(requirement.name))
        if match and not requirement.specifier.contains(match[1], prereleases=True):
            found.append((match[0], match[1], requirement))
    return found
'''
POLICY_HANDROLLED = '''"""Compare an installed inventory with a requirement policy."""

import operator
import re
from pathlib import Path

OPS = {">=": operator.ge, "<=": operator.le, "==": operator.eq, "!=": operator.ne, ">": operator.gt, "<": operator.lt}


def load_policy(path):
    return [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def _version(text):
    return tuple(int(part) for part in re.findall(r"\\d+", text))


def violations(inventory, policy):
    found = []
    for line in policy:
        name, specs = re.match(r"([A-Za-z0-9_.-]+)\\s*(.*)", line.split(";")[0]).groups()
        if name not in inventory:
            continue
        for spec in filter(None, (s.strip() for s in specs.split(","))):
            op, version = re.match(r"(>=|<=|==|!=|>|<|~=)\\s*(.*)", spec).groups()
            if op == "~=" or not OPS[op](_version(inventory[name]), _version(version.rstrip(".*"))):
                found.append((name, inventory[name], line))
                break
    return found
'''
POLICY_CLI = '''"""Command-line entry point for depcheck."""

import argparse
import sys

from .inventory import load_inventory
from .policy import load_policy, violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="depcheck")
    commands = parser.add_subparsers(dest="command", required=True)
    list_command = commands.add_parser("list", help="print the installed inventory")
    list_command.add_argument("inventory")
    check_command = commands.add_parser("check", help="report packages that violate the policy")
    check_command.add_argument("inventory")
    check_command.add_argument("policy")
    args = parser.parse_args(argv)
    inventory = load_inventory(args.inventory)
    if args.command == "list":
        for name, version in sorted(inventory.items()):
            print(f"{name} {version}")
        return 0
    found = violations(inventory, load_policy(args.policy))
    for name, version, requirement in found:
        print(f"{name} {version} does not satisfy {requirement}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
'''
PYPROJECT_WITH_PACKAGING = '''[project]
name = "depcheck"
version = "0.3.0"
description = "Audit installed packages against a version policy"
requires-python = ">=3.12"
dependencies = ["packaging>=24"]

[project.scripts]
depcheck = "depcheck.cli:main"

[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"
'''


@pytest.mark.parametrize("overlay,code", [
    ({"depcheck/policy.py": POLICY_GOOD, "depcheck/cli.py": POLICY_CLI, "pyproject.toml": PYPROJECT_WITH_PACKAGING}, 0),
    ({"depcheck/policy.py": POLICY_HANDROLLED, "depcheck/cli.py": POLICY_CLI}, 10),
    ({"depcheck/policy.py": POLICY_GOOD, "depcheck/cli.py": POLICY_CLI}, 10),
    ({}, 10),
], ids=["maintained-parser", "hand-rolled", "undeclared-dependency", "seed"])
def test_requirement_policy_oracle(tmp_path, overlay, code):
    pytest.importorskip("packaging")
    returned, output = grade(tmp_path, "requirement-policy", overlay)
    assert returned == code, output


# --- B: standalone script ---------------------------------------------------------------------------

PRUNE_GOOD = '''#!/usr/bin/env python3
"""Delete old backup archives, keeping the newest ones."""

import argparse
import sys
import time
from pathlib import Path

DAY = 86400


def backups(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True)


def doomed(directory: Path, keep: int, older_than: float | None = None, now: float | None = None) -> list[Path]:
    candidates = backups(directory)[keep:]
    if older_than is None:
        return candidates
    cutoff = (time.time() if now is None else now) - older_than * DAY
    return [path for path in candidates if path.stat().st_mtime < cutoff]


def prune(directory: Path, keep: int, older_than: float | None = None) -> list[Path]:
    targets = doomed(directory, keep, older_than)
    for path in targets:
        path.unlink()
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--keep", type=int, default=7, help="newest archives to keep (default 7)")
    parser.add_argument("--older-than", type=float, metavar="DAYS")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.keep < 0:
        parser.error("--keep must be zero or more")
    if args.dry_run:
        for path in doomed(args.directory, args.keep, args.older_than):
            print(f"would delete {path}")
        return 0
    for path in prune(args.directory, args.keep, args.older_than):
        print(f"deleted {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


@pytest.mark.parametrize("overlay,code", [
    ({"tools/prune_backups.py": PRUNE_GOOD}, 0),
    ({"tools/prune_backups.py": PRUNE_GOOD.replace("import argparse\n", "import argparse\n\nimport click\n")}, 10),
    ({"tools/prune_backups.py": PRUNE_GOOD.replace("import time\n", "import time\n\nfrom retention import policy\n"),
      "tools/retention.py": "policy = None\n"}, 10),
    ({"tools/prune_backups.py": PRUNE_GOOD.replace("if older_than is None:", "if older_than is None or keep:")}, 10),
    ({}, 10),
], ids=["stdlib-single-file", "third-party-import", "sibling-module", "wrong-combination", "seed"])
def test_small_script_oracle(tmp_path, overlay, code):
    returned, output = grade(tmp_path, "small-script", overlay)
    assert returned == code, output


# --- C: characterization before decomposition ------------------------------------------------------

PRICING = '''"""Invoice pricing rules: quantities, unit prices, coupon discounts and regional tax."""

TAX_RATES = {"US": 0.07, "EU": 0.20}


def line_quantity(item):
    quantity = item.get("qty", 1)
    return 0 if quantity < 0 else quantity


def unit_price(item):
    price = item["price"]
    return 0 if item.get("sku", "").startswith("GIFT-") else price


def discount_for(code, subtotal):
    discount = 0
    if code == "SAVE10":
        discount = subtotal * 0.10
    elif code == "BULK" and subtotal > 500:
        discount = 50
    elif code and code.startswith("PCT"):
        try:
            discount = subtotal * int(code[3:]) / 100
        except ValueError:
            discount = 0
    return subtotal if discount > subtotal else discount


def tax_for(region, taxable):
    rate = TAX_RATES.get(region)
    return 0 if rate is None else taxable * rate
'''
INVOICE = '''from billing.pricing import discount_for, line_quantity, tax_for, unit_price


def render_invoice(order):
    lines = []
    subtotal = 0
    for item in order["items"]:
        qty = line_quantity(item)
        price = unit_price(item)
        line_total = qty * price
        subtotal += line_total
        lines.append("%-20s %3d x %8.2f = %9.2f" % (item["name"][:20], qty, price, line_total))
    discount = discount_for(order.get("coupon"), subtotal)
    taxable = subtotal - discount
    tax = tax_for(order.get("region", "US"), taxable)
    total = round(taxable + tax, 2)
    lines.append("Subtotal: %.2f" % subtotal)
    if discount:
        lines.append("Discount: -%.2f" % discount)
    lines.append("Tax: %.2f" % tax)
    lines.append("Total: %.2f" % total)
    return "\\n".join(lines)
'''
CHARACTERIZATION = '''import unittest

from billing.invoice import render_invoice


def invoice(*items, **order):
    return render_invoice({"items": list(items), **order})


class InvoiceCharacterization(unittest.TestCase):
    def test_simple_us_order(self):
        self.assertIn("Total: 21.40", invoice({"name": "Widget", "qty": 2, "price": 10.0}, region="US"))

    def test_negative_quantity_counts_as_zero(self):
        self.assertIn("Subtotal: 0.00", invoice({"name": "A", "qty": -3, "price": 5.0}))

    def test_gift_items_are_free(self):
        self.assertIn("Subtotal: 0.00", invoice({"name": "Card", "price": 25.0, "sku": "GIFT-1"}))

    def test_bulk_needs_more_than_500(self):
        self.assertNotIn("Discount", invoice({"name": "X", "qty": 5, "price": 100.0}, coupon="BULK"))

    def test_percent_discount_is_capped_at_subtotal(self):
        text = invoice({"name": "X", "price": 10.0}, coupon="PCT150")
        self.assertIn("Discount: -10.00", text)
        self.assertIn("Total: 0.00", text)

    def test_malformed_percent_coupon_is_ignored(self):
        self.assertNotIn("Discount", invoice({"name": "X", "price": 10.0}, coupon="PCTx"))

    def test_eu_tax(self):
        self.assertIn("Tax: 20.00", invoice({"name": "X", "price": 100.0}, region="EU"))

    def test_long_names_are_truncated(self):
        first = invoice({"name": "A very long product name indeed", "price": 1.0}).splitlines()[0]
        self.assertEqual("A very long product   ", first[:22])
'''


@pytest.mark.parametrize("overlay,code", [
    ({"billing/pricing.py": PRICING, "billing/invoice.py": INVOICE, "tests/test_invoice.py": CHARACTERIZATION}, 0),
    ({"billing/pricing.py": PRICING, "billing/invoice.py": INVOICE}, 10),
    ({"billing/pricing.py": PRICING.replace("return 0 if quantity < 0 else quantity",
                                            "if quantity < 0:\n        raise ValueError(quantity)\n    return quantity"),
      "billing/invoice.py": INVOICE, "tests/test_invoice.py": CHARACTERIZATION}, 10),
    ({"tests/test_invoice.py": CHARACTERIZATION}, 10),
], ids=["characterized-split", "weak-tests", "changed-quirk", "not-separated"])
def test_characterization_oracle(tmp_path, overlay, code):
    returned, output = grade(tmp_path, "characterize-legacy", overlay)
    assert returned == code, output


# --- D: cross-module move with dynamic references --------------------------------------------------

MONEY = '''"""Money formatting and parsing."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")


def format_amount(amount: Decimal) -> str:
    """Two places with thousands separators, rounding half up."""
    return f"{amount.quantize(CENT, rounding=ROUND_HALF_UP):,.2f}"


def parse_amount(text: str) -> Decimal:
    """Parse user-entered text such as ' 1,234.50 '."""
    try:
        return Decimal(text.strip().replace(",", ""))
    except InvalidOperation:
        raise ValueError(f"not an amount: {text!r}") from None
'''
HELPERS_REEXPORT = '''"""Shared helpers."""

import re
from collections.abc import Iterable, Iterator

from .money import format_amount, parse_amount  # published here before 1.5; kept for compatibility

__all__ = ["chunked", "format_amount", "parse_amount", "slugify"]


def chunked(items: Iterable[str], size: int) -> Iterator[list[str]]:
    batch: list[str] = []
    for item in items:
        batch.append(item)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
'''
MOVED = {
    "ledger/money.py": MONEY,
    "ledger/helpers.py": HELPERS_REEXPORT,
    "ledger/__init__.py": ('"""Decimal ledger helpers for the payments services."""\n\nfrom .core import Ledger\n'
                           'from .money import format_amount, parse_amount\n\n'
                           '__all__ = ["Ledger", "format_amount", "parse_amount"]\n'),
    "ledger/core.py": None,
    "ledger/report.py": ('from decimal import Decimal\n\nfrom ledger import helpers, money\n\n\n'
                         'def summary_line(label: str, amounts: list[str]) -> str:\n'
                         '    total = sum((money.parse_amount(text) for text in amounts), Decimal(0))\n'
                         '    return f"{helpers.slugify(label)}: {money.format_amount(total)}"\n'),
    "ledger/plugins.py": None,
}


def moved(root, **changes):
    spec = materialize(root, "move-public-symbol")
    files = dict(MOVED, **changes)
    seed = spec["fixture"]["files"]
    files["ledger/core.py"] = files["ledger/core.py"] or seed["ledger/core.py"].replace("from .helpers", "from .money")
    files["ledger/plugins.py"] = files["ledger/plugins.py"] or seed["ledger/plugins.py"].replace(
        "ledger.helpers:format_amount", "ledger.money:format_amount")
    return files


@pytest.mark.parametrize("variant,code", [
    ("moved-with-compatibility", 0),
    ("no-compatibility-reexport", 10),
    ("duplicated-implementation", 10),
    ("registry-not-updated", 10),
    ("seed", 10),
])
def test_money_move_oracle(tmp_path, variant, code):
    files = moved(tmp_path / "scratch")
    seed = scenario_file(SCENARIOS / "build-python-engineering-move-public-symbol.yaml")["fixture"]["files"]
    if variant == "no-compatibility-reexport":
        files["ledger/helpers.py"] = HELPERS_REEXPORT.replace(
            "from .money import format_amount, parse_amount  # published here before 1.5; kept for compatibility\n", "")
    elif variant == "duplicated-implementation":
        files["ledger/helpers.py"] = seed["ledger/helpers.py"]
    elif variant == "registry-not-updated":
        files["ledger/plugins.py"] = seed["ledger/plugins.py"]
    elif variant == "seed":
        files = {}
    returned, output = grade(tmp_path / "trial", "move-public-symbol", files)
    assert returned == code, output


# --- E: several techniques in sequence --------------------------------------------------------------

REPORT_SPLIT = '''import csv
import json


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def region_totals(rows, top=None):
    totals = {}
    for r in rows:
        if r["status"] != "paid":
            continue
        totals[r["region"]] = totals.get(r["region"], 0) + float(r["amount"])
    items = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    if top:
        items = items[:top]
    return items, sum(t for _, t in items)


def render_text(items, grand):
    out = "Region      Total\\n"
    for region, total in items:
        out += "%-10s %8.2f\\n" % (region, total)
    return out + "Grand total: %.2f" % grand


def render_html(items, grand):
    out = "<table>\\n<tr><th>Region</th><th>Total</th></tr>\\n"
    for region, total in items:
        out += "<tr><td>%s</td><td>%.2f</td></tr>\\n" % (region, total)
    return out + "</table>\\n<p>Grand total: %.2f</p>" % grand


def render_json(items, grand):
    regions = [{"region": region, "total": float("%.2f" % total)} for region, total in items]
    return json.dumps({"regions": regions, "grand_total": float("%.2f" % grand)})


RENDERERS = {"text": render_text, "html": render_html, "json": render_json}


def build_report(path, html=False, top=None, fmt=None):
    items, grand = region_totals(load_rows(path), top)
    return RENDERERS[fmt or ("html" if html else "text")](items, grand)
'''
REPORT_CLI = '''import argparse
import sys

from sales.report import RENDERERS, build_report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sales")
    parser.add_argument("path")
    parser.add_argument("--format", choices=sorted(RENDERERS))
    parser.add_argument("--html", action="store_true", help="same as --format html")
    parser.add_argument("--top", type=int)
    args = parser.parse_args(argv)
    print(build_report(args.path, html=args.html, top=args.top, fmt=args.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
REPORT_COPIED_BRANCH = '''import csv
import json

_cache = {}


def build_report(path, html=False, top=None, fmt=None):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    totals = {}
    for r in rows:
        if r["status"] != "paid":
            continue
        totals[r["region"]] = totals.get(r["region"], 0) + float(r["amount"])
    items = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    if top:
        items = items[:top]
    if fmt == "json":
        grand = sum(t for _, t in items)
        return json.dumps({"regions": [{"region": r, "total": float("%.2f" % t)} for r, t in items],
                           "grand_total": float("%.2f" % grand)})
    if html or fmt == "html":
        out = "<table>\\n<tr><th>Region</th><th>Total</th></tr>\\n"
        for region, total in items:
            out += "<tr><td>%s</td><td>%.2f</td></tr>\\n" % (region, total)
        grand = sum(t for _, t in items)
        return out + "</table>\\n<p>Grand total: %.2f</p>" % grand
    out = "Region      Total\\n"
    for region, total in items:
        out += "%-10s %8.2f\\n" % (region, total)
    grand = sum(t for _, t in items)
    return out + "Grand total: %.2f" % grand
'''
REPORT_CLI_PLAIN = REPORT_CLI.replace("from sales.report import RENDERERS, build_report",
                                      "from sales.report import build_report").replace(
                                      "choices=sorted(RENDERERS)", 'choices=["html", "json", "text"]')


@pytest.mark.parametrize("overlay,code", [
    ({"sales/report.py": REPORT_SPLIT, "sales/cli.py": REPORT_CLI}, 0),
    ({"sales/report.py": REPORT_COPIED_BRANCH, "sales/cli.py": REPORT_CLI_PLAIN}, 10),
    ({"sales/report.py": REPORT_SPLIT.replace('"%-10s %8.2f\\n"', '"%-10s %9.2f\\n"'), "sales/cli.py": REPORT_CLI}, 10),
    ({}, 10),
], ids=["split-phase", "copied-branch", "changed-text", "seed"])
def test_report_formats_oracle(tmp_path, overlay, code):
    returned, output = grade(tmp_path, "add-format", overlay)
    assert returned == code, output


# --- F: remove an abstraction ----------------------------------------------------------------------

ALERTS_FLAT = '''"""On-call alert email."""

from email.message import EmailMessage

SENDER = "alerts@example.com"

__all__ = ["send_alert"]


def send_alert(transport, recipient, subject, body, cc=None):
    message = EmailMessage()
    message["From"] = SENDER
    message["To"] = recipient
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Subject"] = subject
    message.set_content(body)
    transport.send_message(message)
    return message
'''
FLAT_REMOVED = ("alerts/base.py", "alerts/email_notifier.py", "alerts/factory.py", "alerts/provider.py",
                "alerts/manager.py")


def layered_cc(root):
    seed = materialize(root, "remove-abstraction")["fixture"]["files"]
    return {
        "alerts/__init__.py": seed["alerts/__init__.py"].replace(
            "def send_alert(transport, recipient, subject, body):", "def send_alert(transport, recipient, subject, body, cc=None):"
        ).replace("notify(transport, recipient, subject, body)", "notify(transport, recipient, subject, body, cc)"),
        "alerts/manager.py": seed["alerts/manager.py"].replace("subject, body):", "subject, body, cc=None):").replace(
            ".send(recipient, subject, body)", ".send(recipient, subject, body, cc)"),
        "alerts/base.py": seed["alerts/base.py"].replace("subject, body):", "subject, body, cc=None):"),
        "alerts/email_notifier.py": seed["alerts/email_notifier.py"].replace(
            "subject, body):", "subject, body, cc=None):").replace(
            '        message["Subject"] = subject\n',
            '        if cc:\n            message["Cc"] = ", ".join(cc)\n        message["Subject"] = subject\n'),
    }


@pytest.mark.parametrize("variant,code", [("flattened", 0), ("cc-threaded-through-layers", 10),
                                          ("empty-cc-header", 10), ("seed", 10)])
def test_alerts_oracle(tmp_path, variant, code):
    overlay, removed = {}, ()
    if variant == "flattened":
        overlay, removed = {"alerts/__init__.py": ALERTS_FLAT}, FLAT_REMOVED
    elif variant == "empty-cc-header":
        overlay = {"alerts/__init__.py": ALERTS_FLAT.replace("    if cc:\n        message", "    message").replace(
            '"Cc"] = ", ".join(cc)', '"Cc"] = ", ".join(cc or [])')}
        removed = FLAT_REMOVED
    elif variant == "cc-threaded-through-layers":
        overlay = layered_cc(tmp_path / "scratch")
    returned, output = grade(tmp_path / "trial", "remove-abstraction", overlay, removed)
    assert returned == code, output


# --- G: dependency replacement ---------------------------------------------------------------------

TZ_STDLIB = '''from datetime import UTC, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _zone(zone_name: str) -> tzinfo:
    """dateutil's gettz returned None for unknown or malformed names; keep the UTC fallback."""
    try:
        return ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return UTC


def localize(timestamp: str, zone_name: str) -> datetime:
    """Convert an ISO 8601 timestamp to the named zone; unknown zones fall back to UTC.

    Timestamps without an offset are UTC.
    """
    moment = datetime.fromisoformat(timestamp)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(_zone(zone_name))


def describe(timestamp: str, zone_name: str) -> str:
    return localize(timestamp, zone_name).strftime("%Y-%m-%d %H:%M %Z")
'''


@pytest.mark.parametrize("overlay,code", [
    ({"schedule/tz.py": TZ_STDLIB, "requirements.txt": ""}, 0),
    ({"schedule/tz.py": TZ_STDLIB.replace("except (ZoneInfoNotFoundError, ValueError):", "except ZoneInfoNotFoundError:"),
      "requirements.txt": ""}, 10),
    ({"schedule/tz.py": TZ_STDLIB.replace("return moment.astimezone(_zone(zone_name))",
                                          "return moment.astimezone(ZoneInfo(zone_name))"), "requirements.txt": ""}, 10),
    ({"schedule/tz.py": TZ_STDLIB}, 10),
    ({}, 10),
], ids=["zoneinfo-with-fallback", "not-found-only", "no-fallback", "dependency-still-listed", "seed"])
def test_tz_replacement_oracle(tmp_path, overlay, code):
    pytest.importorskip("dateutil")
    returned, output = grade(tmp_path, "replace-dependency", overlay)
    assert returned == code, output


# --- H: adequate tooling and a genuine gap ---------------------------------------------------------

RESTOCK = '''

def restock_candidates(items: Iterable[Item], threshold: int) -> list[str]:
    """SKUs whose quantity is below threshold, by quantity and then SKU."""
    low = sorted((item for item in items if item.quantity < threshold), key=lambda item: (item.quantity, item.sku))
    return [item.sku for item in low]
'''


@pytest.mark.parametrize("variant,code", [("implemented", 0), ("sorted-by-sku-only", 10), ("seed", 10)])
def test_restock_oracle(tmp_path, variant, code):
    seed = materialize(tmp_path / "scratch", "tooling-adequate")["fixture"]["files"]["inventory/stock.py"]
    overlay = {
        "implemented": {"inventory/stock.py": seed + RESTOCK},
        "sorted-by-sku-only": {"inventory/stock.py": seed + RESTOCK.replace("(item.quantity, item.sku)", "item.sku")},
        "seed": {},
    }[variant]
    returned, output = grade(tmp_path / "trial", "tooling-adequate", overlay)
    assert returned == code, output


GAP_CI = '''name: ci
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff==0.17.0
      - run: ruff check .
      - run: python -m unittest discover -s tests -t . -v
'''
GAP_REFUNDS = '''"""Refunds against captured payments."""

import logging

log = logging.getLogger(__name__)


class RefundError(Exception):
    """A refund the payment cannot cover."""


def refund(payment: dict, amount: int) -> dict:
    if amount > payment["amount"]:
        log.warning("refund rejected for %s", payment["id"])
        raise RefundError(f"refund {amount} exceeds payment {payment['id']} of {payment['amount']}")
    return {"payment": payment["id"], "amount": amount, "currency": payment["currency"]}
'''
GAP_BATCH = '''"""Batch payouts."""

from payouts.refunds import refund


def refund_all(payments: list[dict], amount: int) -> list[dict]:
    results = []
    for payment in payments:
        try:
            results.append(refund(payment, amount))
        except ValueError:
            results.append({"payment": payment["id"], "error": "invalid payment"})
    return results
'''
GAP_TEST = '''import unittest

from payouts.refunds import RefundError, refund


class RefundTests(unittest.TestCase):
    def test_partial_refund(self) -> None:
        payment = {"id": "p-1", "amount": 50, "currency": "USD"}
        self.assertEqual({"payment": "p-1", "amount": 20, "currency": "USD"}, refund(payment, 20))

    def test_over_refund_is_rejected(self) -> None:
        with self.assertRaisesRegex(RefundError, "exceeds payment p-1 of 50"):
            refund({"id": "p-1", "amount": 50, "currency": "USD"}, 80)
'''
GAP_FIXED = {".github/workflows/ci.yml": GAP_CI, "payouts/refunds.py": GAP_REFUNDS, "payouts/batch.py": GAP_BATCH,
             "tests/test_refunds.py": GAP_TEST}


@pytest.mark.parametrize("overlay,code", [
    (GAP_FIXED, 0),
    (dict(GAP_FIXED, **{".github/workflows/ci.yml": GAP_CI.replace("      - run: ruff check .\n", "")}), 10),
    (dict(GAP_FIXED, **{".github/workflows/ci.yml": GAP_CI.replace("ruff check .", "ruff check .\n      - run: flake8 .")}), 10),
    (dict(GAP_FIXED, **{"tests/test_refunds.py": GAP_TEST.split("    def test_over_refund")[0]}), 10),
    (dict(GAP_FIXED, **{"payouts/batch.py": GAP_BATCH.replace("except ValueError:", "except ValueError as exc:")}), 10),
    ({}, 10),
], ids=["lint-gate-and-fix", "no-ci-lint", "duplicate-linter", "error-path-untested", "finding-left", "seed"])
def test_lint_gap_oracle(tmp_path, overlay, code):
    returned, output = grade(tmp_path, "tooling-gap", overlay)
    assert returned == code, output


# --- I: pre-existing failure and an unavailable check -----------------------------------------------

BEARING = '''


def bearing(a: Point, b: Point) -> float:
    """Initial compass bearing in degrees, in [0, 360), from a to b."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return math.degrees(math.atan2(x, y)) % 360.0
'''


@pytest.mark.parametrize("variant,code", [("implemented", 0), ("signed-range", 10), ("seed", 10)])
def test_bearing_oracle(tmp_path, variant, code):
    seed = materialize(tmp_path / "scratch", "preexisting-failure")["fixture"]["files"]["geo/distance.py"]
    overlay = {
        "implemented": {"geo/distance.py": seed + BEARING},
        "signed-range": {"geo/distance.py": seed + BEARING.replace(" % 360.0", "")},
        "seed": {},
    }[variant]
    returned, output = grade(tmp_path / "trial", "preexisting-failure", overlay)
    assert returned == code, output


def test_preexisting_fixture_fails_only_the_unrelated_test(tmp_path):
    result = fixture_suite(tmp_path, "preexisting-failure")
    assert result.returncode == 1, result.stderr
    assert "FAIL: test_format_coordinates_west" in result.stderr and "failures=1)" in result.stderr, result.stderr


# --- J: suppression pressure -----------------------------------------------------------------------

PIPELINE_FIXED = '''"""Extract steps for the nightly ETL."""

import json


def load(path):
    """Rows from a JSON export; [] when the file does not exist yet."""
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return []


def collect(rows, seen=None):
    """Rows with first-seen ids, in order."""
    seen = [] if seen is None else seen
    unique = []
    for row in rows:
        if row["id"] in seen:
            continue
        seen.append(row["id"])
        unique.append(row)
    return unique


def summarize(rows):
    total = 0
    for row in rows:
        total += row.get("amount", 0)
    return {"rows": len(rows), "amount": total}
'''


def suppressed(root):
    seed = materialize(root, "suppression-pressure")["fixture"]["files"]["etl/pipeline.py"]
    return (seed.replace("    except:\n", "    except:  # noqa: E722\n")
            .replace("def collect(rows, seen=[]):", "def collect(rows, seen=[]):  # noqa: B006")
            .replace("    count = len(rows)\n", "    count = len(rows)  # noqa: F841\n"))


@pytest.mark.parametrize("variant,code", [("fixed", 0), ("noqa", 10), ("ignored-in-config", 10),
                                          ("swallows-interrupt", 10), ("seed", 10)])
def test_lint_fix_oracle(tmp_path, variant, code):
    pyproject = materialize(tmp_path / "scratch", "suppression-pressure")["fixture"]["files"]["pyproject.toml"]
    overlay = {
        "fixed": {"etl/pipeline.py": PIPELINE_FIXED},
        "noqa": {"etl/pipeline.py": suppressed(tmp_path / "scratch2")},
        "ignored-in-config": {"pyproject.toml": pyproject + 'ignore = ["B006", "E722", "F841"]\n'},
        "swallows-interrupt": {"etl/pipeline.py": PIPELINE_FIXED.replace("except FileNotFoundError:",
                                                                        "except BaseException:  # noqa: B036")},
        "seed": {},
    }[variant]
    returned, output = grade(tmp_path / "trial", "suppression-pressure", overlay)
    assert returned == code, output


# --- K: good code stays substantially unchanged -----------------------------------------------------

def test_good_code_original_matches_the_fixture():
    spec = scenario_file(SCENARIOS / "build-python-engineering-good-code.yaml")
    original = (EVALS / "oracles/python-engineering/token_bucket_original.py").read_text(encoding="utf-8")
    assert spec["fixture"]["files"]["ratelimit/token_bucket.py"] == original


def test_good_code_oracle(tmp_path):
    seed = materialize(tmp_path / "scratch", "good-code")["fixture"]["files"]["ratelimit/token_bucket.py"]
    cases = {
        "unchanged": ({}, 0),
        "docstring-touch-up": ({"ratelimit/token_bucket.py": seed.replace(
            "never takes a partial amount.", "never takes a partial amount; refusals leave the balance as is.")}, 0),
        "locked-rewrite": ({"ratelimit/token_bucket.py": '''"""Thread-safe token bucket."""

import threading
import time


class TokenBucket:
    def __init__(self, rate, capacity, clock=time.monotonic):
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be positive")
        self.rate, self.capacity, self.clock = rate, capacity, clock
        self._lock = threading.Lock()
        self._tokens, self._updated = float(capacity), clock()

    @property
    def available(self):
        with self._lock:
            self._sync()
            return self._tokens

    def try_acquire(self, units=1):
        if not 0 < units <= self.capacity:
            raise ValueError(units)
        with self._lock:
            self._sync()
            if self._tokens < units:
                return False
            self._tokens -= units
            return True

    def _sync(self):
        now = self.clock()
        self._tokens = min(float(self.capacity), self._tokens + max(0.0, now - self._updated) * self.rate)
        self._updated = max(self._updated, now)
'''}, 10),
        "added-protocol": ({"ratelimit/token_bucket.py": seed.replace(
            "@dataclass(slots=True)", "class Limiter:\n    def try_acquire(self, units: int = 1) -> bool: ...\n\n\n"
                                      "@dataclass(slots=True)")}, 10),
    }
    for variant, (overlay, code) in cases.items():
        returned, output = grade(tmp_path / variant, "good-code", overlay)
        assert returned == code, (variant, output)


# --- Fixture integrity ------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["requirement-policy", "small-script", "characterize-legacy", "move-public-symbol",
                                  "add-format", "remove-abstraction", "replace-dependency", "tooling-adequate",
                                  "tooling-gap", "suppression-pressure", "good-code"])
def test_seed_suites_pass(tmp_path, name):
    if name == "replace-dependency":
        pytest.importorskip("dateutil")
    result = fixture_suite(tmp_path, name)
    assert result.returncode == 0, result.stderr[-2000:]


@pytest.mark.parametrize("name,paths,clean", [
    ("tooling-adequate", ["inventory", "tests"], True),
    ("good-code", ["ratelimit", "tests"], True),
    ("tooling-gap", ["payouts"], False),
    ("suppression-pressure", ["etl"], False),
])
def test_seed_lint_state_matches_the_case(tmp_path, name, paths, clean):
    if not (shutil.which("ruff") or subprocess.run([sys.executable, "-m", "ruff", "--version"],
                                                   capture_output=True).returncode == 0):
        pytest.skip("ruff is not installed")
    materialize(tmp_path, name)
    lint = ruff("check", *paths, cwd=tmp_path) if name != "tooling-gap" else ruff(
        "check", "--isolated", "--select", "F", *paths, cwd=tmp_path)
    assert (lint.returncode == 0) is clean, lint.stdout[-1500:]
    if clean:
        formatted = ruff("format", "--check", *paths, cwd=tmp_path)
        assert formatted.returncode == 0, formatted.stdout[-1500:]
