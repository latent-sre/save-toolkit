"""Independent acceptance of the report and upload entry points; not an agent test receipt."""

import csv
import importlib
import io
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))
render = candidate_call(importlib.import_module, "report").render
payload = candidate_call(importlib.import_module, "upload").payload
rows = [dict(symbol="ACME", qty=100, price=101.25)]
plain = candidate_call(render, rows)
assert candidate_call(payload, rows) == plain.encode("utf-8"), "default upload changed"

if sys.argv[1] == "csv":
    to_csv = candidate_call(importlib.import_module, "export").to_csv
    expected = [["symbol", "qty", "price"], ["ACME", "100", "101.25"]]
    for name, text in (("to_csv", candidate_call(to_csv, rows)),
                       ("render", candidate_call(render, rows, fmt="csv")),
                       ("payload", candidate_call(payload, rows, fmt="csv").decode("utf-8"))):
        assert list(csv.reader(io.StringIO(text))) == expected, (name, text)
elif sys.argv[1] == "title":
    assert candidate_call(render, rows, title="Daily") == "Daily\n" + plain, "render title"
    assert candidate_call(payload, rows, title="Daily") == ("Daily\n" + plain).encode("utf-8"), "payload title"
else:
    raise SystemExit(f"unknown mode {sys.argv[1]!r}")
print(f"independent {sys.argv[1]} acceptance passed")
