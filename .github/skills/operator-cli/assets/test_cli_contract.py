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
import time
import unittest

COMMAND = Path(__file__).with_name("cli_contract.py")
LOCK = "cancel_stale_orders.lock"

FAKE_CLIENT = '''
import json
import os
import signal
import time
from pathlib import Path

STORE = Path("store.json")


class OrderError(Exception):
    pass


def _load():
    return json.loads(STORE.read_text(encoding="utf-8"))


def _save(data):
    STORE.write_text(json.dumps(data), encoding="utf-8")


def list_stale(minutes):
    data = _load()
    checks = data.setdefault("selection_locks", [])
    checks.append(Path("cancel_stale_orders.lock").exists())
    _save(data)
    plan = sorted(o for o, v in data["orders"].items() if v["state"] == "open" and v["age"] >= minutes)
    if len(checks) > 1 and os.environ.get("SECOND_PLAN") == "changed":
        return plan + ["new-order"]
    if len(checks) > 1 and os.environ.get("SECOND_PLAN") == "reversed":
        return plan[::-1]
    return plan


def status(order_id):
    if _load()["orders"][order_id].get("fault") == "unknown":
        raise TimeoutError("read-back unavailable")
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
    if order.get("fault") in ("timeout", "unknown"):
        raise TimeoutError(order_id)
    if order.get("fault") == "hold":
        Path("ready").touch()
        deadline = time.monotonic() + 20
        while not Path("release").exists():
            if time.monotonic() >= deadline:
                raise TimeoutError("test release did not arrive")
            time.sleep(0.01)
    if order.get("fault") in ("replace-lock", "overwrite-lock", "replace-lock-SIGINT"):
        lock = Path("cancel_stale_orders.lock")
        if order["fault"] != "overwrite-lock":
            lock.unlink()
        lock.write_text("another owner", encoding="utf-8")
        if order["fault"] == "replace-lock-SIGINT":
            signal.raise_signal(signal.SIGINT)
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

    def environment(self, **extra: str) -> dict[str, str]:
        return {**os.environ, "PYTHONPATH": str(self.work), "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1", **extra}

    def run_command(self, *args: str, stdin: str | None = None, tty: bool = False,
                    **extra: str) -> subprocess.CompletedProcess:
        command = [sys.executable, "-B", "command.py", *args]
        if tty:
            command = [sys.executable, "-B", "-c",
                       "import runpy,sys; sys.stdin.isatty=lambda: True; "
                       "sys.argv[0]='command.py'; runpy.run_path('command.py',run_name='__main__')", *args]
        return subprocess.run(command, cwd=self.work, env=self.environment(**extra), input=stdin or "",
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
        self.assertEqual({"o1": "skipped", "o2": "skipped", "o3": "skipped"}, self.outcomes(result))
        self.assertEqual([], self.calls())
        self.assertFalse((self.work / LOCK).exists())

    def test_piped_input_never_confirms(self) -> None:
        self.store()
        result = self.run_command("--json", stdin="y\n")
        self.assertEqual(2, result.returncode)
        self.assertEqual([], self.calls())

    def test_partial_failure_reports_each_item_and_exits_1(self) -> None:
        self.store({"o2": "reject"})
        result = self.run_command("--yes", "--json")
        self.assertEqual(1, result.returncode)
        self.assertEqual({"o1": "succeeded", "o2": "failed", "o3": "skipped"}, self.outcomes(result))
        self.assertEqual(["o1", "o2"], self.calls())

    def test_nonpositive_limits_are_usage_errors_without_client_calls(self) -> None:
        for flag in ("--older-than", "--max-items"):
            for value in ("0", "-1"):
                with self.subTest(flag=flag, value=value):
                    self.store()
                    result = self.run_command(flag, value, "--yes", "--json")
                    self.assertEqual(2, result.returncode, result.stderr)
                    self.assertEqual([], self.calls())
                    self.assertNotIn("selection_locks", json.loads((self.work / "store.json").read_text()))

    def test_default_cap_refuses_the_whole_plan_before_effects(self) -> None:
        self.store(count=101)
        result = self.run_command("--yes", "--json")
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertEqual([], self.calls())
        self.assertEqual(101, len(self.outcomes(result)))
        self.assertEqual({"skipped"}, set(self.outcomes(result).values()))
        self.assertFalse((self.work / LOCK).exists())

    def test_explicit_cap_accepts_the_boundary_and_refuses_above_it(self) -> None:
        self.store()
        refused = self.run_command("--max-items", "2", "--yes", "--json")
        self.assertEqual(1, refused.returncode, refused.stderr)
        self.assertEqual([], self.calls())
        accepted = self.run_command("--max-items", "3", "--yes", "--json")
        self.assertEqual(0, accepted.returncode, accepted.stderr)
        self.assertEqual(["o1", "o2", "o3"], self.calls())

    def test_unknown_stops_scheduling_and_exits_1(self) -> None:
        self.store({"o2": "unknown"})
        result = self.run_command("--yes", "--json")
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertEqual(["o1", "o2"], self.calls())
        self.assertEqual({"o1": "succeeded", "o2": "unknown", "o3": "skipped"}, self.outcomes(result))

    def test_existing_lock_is_preserved_and_no_effect_is_attempted(self) -> None:
        self.store()
        (self.work / LOCK).write_text("another owner", encoding="utf-8")
        result = self.run_command("--yes", "--json")
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertEqual([], self.calls())
        self.assertEqual("another owner", (self.work / LOCK).read_text())

    def test_replaced_lock_is_not_deleted_by_cleanup(self) -> None:
        for fault in ("replace-lock", "overwrite-lock"):
            for item in ("o1", "o3"):
                with self.subTest(fault=fault, item=item):
                    (self.work / LOCK).unlink(missing_ok=True)
                    self.store({item: fault})
                    result = self.run_command("--yes", "--json")
                    self.assertEqual(1, result.returncode, result.stderr)
                    self.assertEqual("another owner", (self.work / LOCK).read_text())
                    self.assertEqual(["o1"] if item == "o1" else ["o1", "o2", "o3"], self.calls())

    def test_interactive_json_has_no_prompt_on_stdout(self) -> None:
        self.store()
        result = self.run_command("--json", tty=True, stdin="y\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"o1": "succeeded", "o2": "succeeded", "o3": "succeeded"}, self.outcomes(result))
        self.assertIn("Cancel these 3 orders?", result.stderr)
        self.assertEqual([False, True], json.loads((self.work / "store.json").read_text())["selection_locks"])

    def test_cleanup_cannot_mask_an_interrupt_or_delete_a_replaced_lock(self) -> None:
        self.store({"o1": "replace-lock-SIGINT"})
        result = self.run_command("--yes", "--json")
        self.assertEqual(130, result.returncode, result.stderr)
        self.assertEqual(["o1"], self.calls())
        self.assertEqual("another owner", (self.work / LOCK).read_text())
        self.assertEqual({"o1": "unknown", "o2": "skipped", "o3": "skipped"}, self.outcomes(result))
        self.assertIn("ownership changed", result.stderr)

    def test_changed_plan_is_refused_under_lock_for_both_confirmation_modes(self) -> None:
        for tty in (False, True):
            with self.subTest(tty=tty):
                self.store()
                args = ["--json"] if tty else ["--yes", "--json"]
                result = self.run_command(*args, tty=tty, stdin="y\n", SECOND_PLAN="changed")
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual([], self.calls())
                self.assertIn("changed", result.stderr)
                self.assertEqual([False, True], json.loads((self.work / "store.json").read_text())["selection_locks"])
                self.assertFalse((self.work / LOCK).exists())

    def test_same_targets_in_another_order_are_accepted(self) -> None:
        self.store()
        result = self.run_command("--yes", "--json", SECOND_PLAN="reversed")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["o1", "o2", "o3"], self.calls())

    def test_concurrent_invocation_cannot_take_the_owned_lock(self) -> None:
        self.store({"o1": "hold"})
        with subprocess.Popen([sys.executable, "-B", "command.py", "--yes", "--json"],
                              cwd=self.work, env=self.environment(), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True) as first:
            try:
                deadline = time.monotonic() + 10
                while not (self.work / "ready").exists() and first.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue((self.work / "ready").exists(), "first command never reached its effect")
                owner = (self.work / LOCK).read_text()
                second = self.run_command("--yes", "--json")
                self.assertEqual(1, second.returncode, second.stderr)
                self.assertEqual(["o1"], self.calls())
                self.assertEqual(owner, (self.work / LOCK).read_text())
            finally:
                (self.work / "release").touch()
                stdout, stderr = first.communicate(timeout=30)
        self.assertEqual(0, first.returncode, stderr)
        self.assertEqual(["o1", "o2", "o3"], self.calls())
        self.assertFalse((self.work / LOCK).exists())

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

    def test_signals_during_lock_transitions_do_not_strand_owned_resources(self) -> None:
        # Inject a real signal after exclusive creation, and after unlink. These are the narrow
        # transitions where ordinary try/finally can lose ownership or the interrupt status.
        for signame, code in (("SIGINT", 130), ("SIGTERM", 143)):
            for phase in ("acquire", "release"):
                with self.subTest(signal=signame, phase=phase):
                    self.store()
                    wrapper = '''
import command, io, signal, sys
from pathlib import Path
phase, signame = sys.argv[1:]
real_open, real_unlink = io.open, Path.unlink
def opened(path, mode="r", *args, **kwargs):
    stream = real_open(path, mode, *args, **kwargs)
    if phase == "acquire" and Path(path) == command.LOCK and mode == "x":
        signal.raise_signal(getattr(signal, signame))
    return stream
def unlinked(path, *args, **kwargs):
    result = real_unlink(path, *args, **kwargs)
    if phase == "release" and path == command.LOCK:
        signal.raise_signal(getattr(signal, signame))
    return result
io.open, Path.unlink = opened, unlinked
raise SystemExit(command.main(["--yes", "--json"]))
'''
                    result = subprocess.run([sys.executable, "-B", "-c", wrapper, phase, signame],
                                            cwd=self.work, env=self.environment(), capture_output=True,
                                            text=True, timeout=30)
                    self.assertEqual(code, result.returncode, result.stderr)
                    self.assertFalse((self.work / LOCK).exists())
                    self.assertEqual([] if phase == "acquire" else ["o1", "o2", "o3"], self.calls())
                    self.assertEqual({"skipped"} if phase == "acquire" else {"succeeded"},
                                     set(self.outcomes(result).values()))

    def test_closed_stdout_ends_without_traceback(self) -> None:
        self.store(count=20000)
        env = {**os.environ, "PYTHONPATH": str(self.work)}
        with subprocess.Popen([sys.executable, "command.py", "--dry-run", "--max-items", "20000"], cwd=self.work, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
            proc.stdout.readline()
            proc.stdout.close()
            stderr = proc.stderr.read()
            proc.wait(timeout=30)
        self.assertNotIn("Traceback", stderr)


if __name__ == "__main__":
    unittest.main()
