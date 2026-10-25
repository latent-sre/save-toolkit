"""Outcome checks for build-python-engineering-characterize-legacy.

1. Differential: the candidate's render_invoice equals the original byte for byte on seeded orders,
   and raises the same exception type on malformed ones.
2. Separation: the pricing literals (coupon codes, tax rates) no longer live in render_invoice.
3. Characterization: the candidate's own suite passes with the ORIGINAL render_invoice substituted,
   and fails for at least MIN_KILLED of the single-quirk mutants of the original.
"""

import ast
import inspect
import json
import random
import subprocess
import sys
from pathlib import Path

from oracle_protocol import candidate_call

ORIGINAL = '''
def render_invoice(order):
    lines = []
    subtotal = 0
    for item in order["items"]:
        qty = item.get("qty", 1)
        if qty < 0:
            qty = 0
        price = item["price"]
        if item.get("sku", "").startswith("GIFT-"):
            price = 0
        line_total = qty * price
        subtotal += line_total
        lines.append("%-20s %3d x %8.2f = %9.2f" % (item["name"][:20], qty, price, line_total))
    discount = 0
    code = order.get("coupon")
    if code == "SAVE10":
        discount = subtotal * 0.10
    elif code == "BULK" and subtotal > 500:
        discount = 50
    elif code and code.startswith("PCT"):
        try:
            discount = subtotal * int(code[3:]) / 100
        except ValueError:
            discount = 0
    if discount > subtotal:
        discount = subtotal
    taxable = subtotal - discount
    region = order.get("region", "US")
    if region == "US":
        tax = taxable * 0.07
    elif region == "EU":
        tax = taxable * 0.20
    else:
        tax = 0
    total = round(taxable + tax, 2)
    lines.append("Subtotal: %.2f" % subtotal)
    if discount:
        lines.append("Discount: -%.2f" % discount)
    lines.append("Tax: %.2f" % tax)
    lines.append("Total: %.2f" % total)
    return "\\n".join(lines)
'''
MUTATIONS = {
    "negative quantity kept": ("if qty < 0:", "if qty < -10**9:"),
    "gift items charged": ('startswith("GIFT-")', 'startswith("GIFT-X")'),
    "bulk threshold dropped": ('code == "BULK" and subtotal > 500', 'code == "BULK"'),
    "discount cap removed": ("if discount > subtotal:", "if discount > subtotal * 10:"),
    "bad percent coupon raises": ("except ValueError:\n            discount = 0", "except ValueError:\n            raise"),
    "EU tax rate changed": ("taxable * 0.20", "taxable * 0.21"),
    "name not truncated": ('item["name"][:20]', 'item["name"]'),
}
MIN_KILLED = 5
PRICING_LITERALS = {"SAVE10", "BULK", "PCT", 0.07, 0.2}


def compile_original(source):
    namespace = {}
    exec(compile(source, "<original>", "exec"), namespace)
    return namespace["render_invoice"]


def orders(seed=20261025, count=600):
    rng = random.Random(seed)
    names = ["Widget", "A very long product name indeed", "Bolt", "Gift card", "x"]
    prices = [0, 0.1, 1.005, 19.99, 333.33, 250, 1200]
    coupons = [None, "", "SAVE10", "BULK", "PCT15", "PCT", "PCTx", "PCT150", "save10"]
    regions = ["US", "EU", "CA", None]
    for _ in range(count):
        items = []
        for _ in range(rng.randint(0, 4)):
            item = {"name": rng.choice(names), "price": rng.choice(prices)}
            if rng.random() < 0.8:
                item["qty"] = rng.randint(-2, 5)
            if rng.random() < 0.3:
                item["sku"] = rng.choice(["GIFT-01", "SKU-7", "gift-02"])
            items.append(item)
        order = {"items": items}
        coupon = rng.choice(coupons)
        if coupon is not None:
            order["coupon"] = coupon
        region = rng.choice(regions)
        if region is not None:
            order["region"] = region
        yield order


sys.path.insert(0, str(Path.cwd()))
import billing.invoice as candidate

original = compile_original(ORIGINAL)
for order in orders():
    expected = original(order)
    actual = candidate_call(candidate.render_invoice, order)
    assert actual == expected, f"output changed for {json.dumps(order)}:\n{expected!r}\n!=\n{actual!r}"
for malformed in ({}, {"items": [{"name": "no price"}]}, {"items": [{"price": 3}]}):
    try:
        original(malformed)
    except Exception as exc:
        expected_type = type(exc)
    try:
        candidate_call(candidate.render_invoice, malformed)
    except expected_type:
        pass
    except Exception as exc:
        raise AssertionError(f"{malformed}: raised {type(exc).__name__}, original raised {expected_type.__name__}") from None
    else:
        raise AssertionError(f"{malformed}: no exception, original raised {expected_type.__name__}")

entry = inspect.unwrap(candidate.render_invoice)
source_file = Path(inspect.getsourcefile(entry)).resolve()
assert source_file.is_relative_to(Path.cwd() / "billing"), f"render_invoice is defined outside billing/: {source_file}"
module_tree = ast.parse(source_file.read_text(encoding="utf-8"))
definition = next(
    node for node in ast.walk(module_tree)
    if isinstance(node, ast.FunctionDef) and node.name == entry.__name__ and node.lineno == entry.__code__.co_firstlineno
)
inline = {node.value for node in ast.walk(definition) if isinstance(node, ast.Constant)} & PRICING_LITERALS
assert not inline, f"pricing rules still live inside render_invoice: {sorted(map(str, inline))}"

RUNNER = r'''
import io, sys, unittest
sys.path.insert(0, ".")
import billing.invoice
namespace = {}
exec(compile(sys.stdin.read(), "<substitute>", "exec"), namespace)
billing.invoice.render_invoice = namespace["render_invoice"]
try:
    import billing
    if hasattr(billing, "render_invoice"):
        billing.render_invoice = namespace["render_invoice"]
except ImportError:
    pass
suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
print(f"RAN {result.testsRun} FAILED {len(result.failures) + len(result.errors)}")
sys.exit(0 if result.wasSuccessful() and result.testsRun else 1)
'''


def suite_passes(source):
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", RUNNER], input=source,
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )
    return result.returncode == 0, (result.stdout + result.stderr).strip()[-300:]


passed, detail = suite_passes(ORIGINAL)
assert passed, f"the candidate's tests fail against the original render_invoice: {detail}"
survivors = []
for name, (old, new) in MUTATIONS.items():
    assert ORIGINAL.count(old) == 1, f"oracle mutation {name!r} no longer applies"
    passed, _ = suite_passes(ORIGINAL.replace(old, new))
    if passed:
        survivors.append(name)
killed = len(MUTATIONS) - len(survivors)
assert killed >= MIN_KILLED, f"tests detect {killed}/{len(MUTATIONS)} behavior changes; undetected: {survivors}"
print(f"invoice characterization: PASS ({killed}/{len(MUTATIONS)} mutants detected)")
