"""Outcome checks for build-operator-cli-safe-requeue; no third-party dependencies.

Copies the candidate requeue_failed.py beside a probe-owned jobs_api.py that records every requeue
call and injects faults: a rejected job, a timeout after the effect, and SIGINT or SIGTERM raised
in-process after the effect (so the signal cases also run on Windows).
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

FAULTY_API = '''
import json
import os
import signal
from pathlib import Path


class JobServiceError(Exception):
    """The service rejected the request."""


def _store():
    return Path(os.environ["JOBS_STORE"])


def _load():
    return json.loads(_store().read_text(encoding="utf-8"))


def _save(data):
    _store().write_text(json.dumps(data), encoding="utf-8")


def list_failed():
    return sorted(job_id for job_id, job in _load()["jobs"].items() if job["status"] == "failed")


def get_status(job_id):
    if _load()["jobs"][job_id].get("fault") == "unknown":
        raise TimeoutError("read-back unavailable")
    return _load()["jobs"][job_id]["status"]


def requeue(job_id):
    data = _load()
    job = data["jobs"][job_id]
    data["calls"].append(job_id)
    if job.get("fault") == "locked":
        _save(data)
        raise JobServiceError(job_id + " is locked by another settlement run")
    job["status"] = "queued"
    _save(data)
    if job.get("fault") in ("timeout", "unknown"):
        raise TimeoutError("no response for " + job_id)
    if job.get("fault") in ("SIGINT", "SIGTERM"):
        signal.raise_signal(getattr(signal, job["fault"]))
'''


class ContractFailure(AssertionError):
    pass


def expect(condition, message):
    if not condition:
        raise ContractFailure(message)


def run_case(candidate, faults, args, stdin=""):
    work = Path(tempfile.mkdtemp())
    try:
        shutil.copy(candidate, work / "requeue_failed.py")
        (work / "jobs_api.py").write_text(FAULTY_API, encoding="utf-8")
        jobs = {job_id: {"status": "failed"} for job_id in ("j1", "j2", "j3")}
        jobs["j4"] = {"status": "queued"}
        for job_id, fault in faults.items():
            jobs[job_id]["fault"] = fault
        store = work / "store.json"
        store.write_text(json.dumps({"jobs": jobs, "calls": []}), encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
        env.update({"JOBS_STORE": str(store), "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"})
        try:
            result = subprocess.run([sys.executable, "requeue_failed.py", *args], cwd=work, env=env, input=stdin,
                                    capture_output=True, text=True, timeout=20)
        except subprocess.TimeoutExpired:
            raise ContractFailure(f"{' '.join(args) or 'no flags'}: still running after 20 s") from None
        calls = json.loads(store.read_text(encoding="utf-8"))["calls"]
        return result, calls, (work / "requeue.lock").exists()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def outcomes(result, case):
    try:
        document = json.loads(result.stdout)
        if not isinstance(document, dict) or not isinstance(document.get("items"), list):
            raise ValueError("expected an object with an items array")
        seen = {}
        for item in document["items"]:
            if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                    or item.get("status") not in ("succeeded", "failed", "unknown", "skipped")):
                raise ValueError("each item needs a string id and a documented status")
            if item["id"] in seen:
                raise ValueError("duplicate item id")
            seen[item["id"]] = item["status"]
        return seen
    except (ValueError, KeyError, TypeError) as exc:
        raise ContractFailure(f"{case}: stdout is not the README's --json object ({exc}): {result.stdout[:300]!r}") from None


def check(candidate):
    result, calls, _ = run_case(candidate, {}, ["--dry-run", "--json"])
    expect(result.returncode == 0, f"dry run: exit {result.returncode}, expected 0; stderr {result.stderr[-300:]!r}")
    expect(calls == [], f"dry run: requeued {calls}")
    seen = outcomes(result, "dry run")
    expect(seen == {"j1": "skipped", "j2": "skipped", "j3": "skipped"},
           f"dry run: expected exactly the planned jobs as skipped, got {seen}")

    result, calls, _ = run_case(candidate, {}, [], stdin="y\n")
    expect(result.returncode == 2, f"piped confirmation: exit {result.returncode}, expected 2 (usage)")
    expect(calls == [], f"piped confirmation: a pipe confirmed and requeued {calls}")

    result, calls, _ = run_case(candidate, {"j2": "locked"}, ["--yes", "--json"])
    expect(result.returncode == 1, f"partial failure: exit {result.returncode}, expected 1")
    seen = outcomes(result, "partial failure")
    expect(seen == {"j1": "succeeded", "j2": "failed", "j3": "skipped"},
           f"partial failure: outcomes {seen}")
    expect(calls == ["j1", "j2"], f"partial failure: expected work to stop at the first failure, got {calls}")

    for fault in ("timeout", "unknown"):
        result, calls, _ = run_case(candidate, {"j2": fault}, ["--yes", "--json"])
        expect(calls.count("j2") == 1, f"{fault}: j2 requeued {calls.count('j2')} times; an effect of unknown outcome was replayed")
        seen = outcomes(result, fault)
        allowed = ("unknown",) if fault == "unknown" else ("succeeded", "unknown")
        expect(seen.get("j2") in allowed, f"{fault}: j2 reported {seen.get('j2')!r}; the effect may have happened")
        if seen.get("j2") == "unknown":
            expect(result.returncode == 1, f"{fault}: an UNKNOWN item exited {result.returncode}, expected 1")
            expect(seen == {"j1": "succeeded", "j2": "unknown", "j3": "skipped"}, f"{fault}: outcomes {seen}")
            expect(calls == ["j1", "j2"], f"{fault}: work did not stop at the UNKNOWN item: {calls}")
        else:
            expect(result.returncode == 0, f"{fault}: reconciled success exited {result.returncode}, expected 0")
            expect(seen == {"j1": "succeeded", "j2": "succeeded", "j3": "succeeded"}, f"{fault}: outcomes {seen}")
            expect(calls == ["j1", "j2", "j3"], f"{fault}: unexpected effect calls {calls}")

    for signame, code in (("SIGINT", 130), ("SIGTERM", 143)):
        result, calls, locked = run_case(candidate, {"j2": signame}, ["--yes", "--json"])
        expect(result.returncode == code, f"{signame}: exit {result.returncode}, expected {code}; stderr {result.stderr[-300:]!r}")
        expect(calls == ["j1", "j2"], f"{signame}: requeue calls {calls}; work continued after the signal")
        expect(not locked, f"{signame}: requeue.lock was left behind")
        seen = outcomes(result, signame)
        expect(set(seen) == {"j1", "j2", "j3"}, f"{signame}: expected exactly the planned jobs, got {sorted(seen)}")
        expect(seen.get("j1") == "succeeded", f"{signame}: j1 reported {seen.get('j1')!r}")
        expect(seen.get("j2") in ("succeeded", "unknown"), f"{signame}: j2 reported {seen.get('j2')!r}")
        expect(seen.get("j3") == "skipped", f"{signame}: j3 reported {seen.get('j3')!r}")


if __name__ == "__main__":
    try:
        check(Path(sys.argv[1] if len(sys.argv) > 1 else "requeue_failed.py").resolve())
    except ContractFailure as failure:
        print(f"contract failed: {failure}", file=sys.stderr)
        sys.exit(1)
    print("contract passed: operator requeue")
