"""Contract tests for an operator command, run at the process boundary.

Copy with the command it tests. Adapt COMMAND, the flags, and FAKE_CLIENT (the effect seam the
command imports) to the task; keep every case. Signals are raised inside the fake client, so every
case, including SIGINT and SIGTERM, runs on Windows as well as POSIX.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

COMMAND = Path(__file__).with_name("cli_contract.py")
LOCK = "cancel_stale_orders.lock"

FAKE_CLIENT = '''
import json
import signal
from pathlib import Path

STORE = Path("store.json")


class OrderError(Exception):
    pass


def _load():
    return json.loads(STORE.read_text(encoding="utf-8"))


def _save(data):
    STORE.write_text(json.dumps(data), encoding="utf-8")


def list_stale(minutes):
    orders = _load()["orders"]
    return sorted(o for o, v in orders.items() if v["state"] == "open" and v["age"] >= minutes)


def status(order_id):
    return _load()["orders"][order_id]["state"]


def cancel(order_id):
    data = _load()
    order = data["orders"][order_id]
    data["calls"].append(order_id)
    if order.get("fault") == "reject":
        _save(data)
        raise OrderError("rejected by the venue")
    order["state"] = "cancelled"
    _save(data)
    if order.get("fault") == "timeout":
        raise TimeoutError(order_id)
    if order.get("fault") in ("SIGINT", "SIGTERM"):
        signal.raise_signal(getattr(signal, order["fault"]))
'''


class OperatorContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        shutil.copy(COMMAND, self.work / "command.py")
        (self.work / "orders_client.py").write_text(FAKE_CLIENT, encoding="utf-8")

    def store(self, faults: dict[str, str] | None = None, count: int = 3) -> None:
        orders = {f"o{n}": {"state": "open", "age": 45} for n in range(1, count + 1)}
        orders["fresh"] = {"state": "open", "age": 5}
        for order_id, fault in (faults or {}).items():
            orders[order_id]["fault"] = fault
        (self.work / "store.json").write_text(json.dumps({"orders": orders, "calls": []}), encoding="utf-8")

    def run_command(self, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
        env = {**os.environ, "PYTHONPATH": str(self.work), "PYTHONIOENCODING": "utf-8"}
        return subprocess.run([sys.executable, "command.py", *args], cwd=self.work, env=env, input=stdin or "",
                              capture_output=True, text=True, timeout=30)

    def calls(self) -> list[str]:
        return json.loads((self.work / "store.json").read_text(encoding="utf-8"))["calls"]

    def outcomes(self, result: subprocess.CompletedProcess) -> dict[str, str]:
        return {item["id"]: item["status"] for item in json.loads(result.stdout)["items"]}

    def test_help_documents_exit_codes(self) -> None:
        result = self.run_command("--help")
        self.assertEqual(0, result.returncode)
        self.assertIn("Exit codes", result.stdout)

    def test_dry_run_makes_no_effect_calls(self) -> None:
        self.store()
        result = self.run_command("--dry-run", "--json")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["o1", "o2", "o3"], json.loads(result.stdout)["plan"])
        self.assertEqual([], self.calls())

    def test_piped_input_never_confirms(self) -> None:
        self.store()
        result = self.run_command("--json", stdin="y\n")
        self.assertEqual(2, result.returncode)
        self.assertEqual([], self.calls())

    def test_partial_failure_reports_each_item_and_exits_1(self) -> None:
        self.store({"o2": "reject"})
        result = self.run_command("--yes", "--json")
        self.assertEqual(1, result.returncode)
        self.assertEqual({"o1": "succeeded", "o2": "failed", "o3": "succeeded"}, self.outcomes(result))

    def test_timeout_is_read_back_not_replayed(self) -> None:
        self.store({"o2": "timeout"})
        result = self.run_command("--yes", "--json")
        self.assertEqual("succeeded", self.outcomes(result)["o2"])
        self.assertEqual(["o1", "o2", "o3"], self.calls())

    def test_signals_stop_work_release_the_lock_and_report(self) -> None:
        for signame, code in (("SIGINT", 130), ("SIGTERM", 143)):
            with self.subTest(signal=signame):
                self.store({"o2": signame})
                result = self.run_command("--yes", "--json")
                self.assertEqual(code, result.returncode, result.stderr)
                self.assertEqual(["o1", "o2"], self.calls())
                self.assertFalse((self.work / LOCK).exists())
                self.assertEqual({"o1": "succeeded", "o2": "unknown", "o3": "skipped"}, self.outcomes(result))

    def test_closed_stdout_ends_without_traceback(self) -> None:
        self.store(count=20000)
        env = {**os.environ, "PYTHONPATH": str(self.work)}
        with subprocess.Popen([sys.executable, "command.py", "--dry-run"], cwd=self.work, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            proc.stdout.readline()
            proc.stdout.close()
            stderr = proc.stderr.read()
            proc.wait(timeout=30)
        self.assertNotIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
