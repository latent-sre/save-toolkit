"""No-model regressions for the pager-webhook oracle: a house-rule reference passes, mutants fail."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-pager-webhook.yaml"
ORACLE = ROOT / "evals/oracles/pager-webhook/probe_checks.py"
CHECKS = ["signature", "fast_ack", "accepted", "completes", "redelivery", "durable"]

REFERENCE = '''
"""opsapi application factory."""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app import store
from app.config import get_settings
from app.db import connect, init_schema
from app.errors import install_problem_handlers
from app.runbooks import runbook_url

INBOX = INBOX_SQL
INSERT_INCIDENT = ("INSERT INTO incidents (id, title, service, status, runbook_url, created_at)"
                   " VALUES (?, ?, ?, 'open', ?, ?)")


def _incident_args(event: dict, url: str) -> tuple:
    return (f"inc-{uuid.uuid4().hex[:12]}", event["summary"], event["service"], url,
            datetime.now(timezone.utc).isoformat())


def _enrich_later(event: dict) -> None:
    url = runbook_url(event["service"])
    with connect() as conn:
        conn.execute("UPDATE incidents SET runbook_url = ? WHERE title = ?", (url, event["summary"]))
        conn.commit()


def _process_one(event: dict) -> None:
    url = runbook_url(event["service"])
    with connect() as conn:
        conn.execute(INSERT_INCIDENT, _incident_args(event, url))
        conn.commit()


def _worker(stop: threading.Event) -> None:
    while not stop.is_set():
        with connect() as conn:
            row = conn.execute("SELECT rowid AS rid, event_id, service, summary FROM pager_events"
                               " WHERE status = 'pending' ORDER BY rowid LIMIT 1").fetchone()
        if row is None:
            stop.wait(0.2)
            continue
        url = runbook_url(row["service"])
        with connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute("SELECT status FROM pager_events WHERE rowid = ?", (row["rid"],)).fetchone()
            if current["status"] == "pending":
                conn.execute(INSERT_INCIDENT, _incident_args(dict(row), url))
                conn.execute("UPDATE pager_events SET status = 'done' WHERE rowid = ?", (row["rid"],))
            conn.commit()


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_schema()
        with connect() as conn:
            conn.execute(INBOX)
        stop = threading.Event()
        if WORKER_ENABLED:
            threading.Thread(target=_worker, args=(stop,), daemon=True).start()
        yield
        stop.set()

    app = FastAPI(title="opsapi", lifespan=lifespan)
    install_problem_handlers(app)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.post("/v1/webhooks/pager")
    async def pager(request: Request):
        raw = await request.body()
        expected = "sha256=" + hmac.new(get_settings().pager_webhook_secret.encode(), raw,
                                        hashlib.sha256).hexdigest()
        if SIGNATURE_REJECTS:
            raise HTTPException(401, "invalid or missing X-Pager-Signature")
        event = json.loads(raw)
        ACCEPT
        return JSONResponse({"accepted": event["event_id"]}, status_code=ACK_STATUS)

    return app
'''
HOUSE = {
    "INBOX_SQL": ('"CREATE TABLE IF NOT EXISTS pager_events (event_id TEXT PRIMARY KEY, service TEXT,'
                  ' summary TEXT, status TEXT NOT NULL DEFAULT \'pending\')"'),
    "WORKER_ENABLED": "True",
    "SIGNATURE_REJECTS": 'not hmac.compare_digest(request.headers.get("x-pager-signature", ""), expected)',
    "ACCEPT": ('with connect() as conn:\n'
               '            conn.execute("INSERT OR IGNORE INTO pager_events (event_id, service, summary)"\n'
               '                         " VALUES (?, ?, ?)", (event["event_id"], event["service"], event["summary"]))\n'
               '            conn.commit()'),
    "ACK_STATUS": "202",
}
MUTANTS = {
    # check that must fail: the one house rule the mutant breaks
    "signature": {"SIGNATURE_REJECTS": "False"},
    "fast_ack": {"ACCEPT": "_process_one(event)", "WORKER_ENABLED": "False"},
    "accepted": {"ACK_STATUS": "200"},
    "completes": {"WORKER_ENABLED": "False"},
    "redelivery": {"INBOX_SQL": ('"CREATE TABLE IF NOT EXISTS pager_events (n INTEGER PRIMARY KEY AUTOINCREMENT,'
                                 ' event_id TEXT, service TEXT, summary TEXT, status TEXT NOT NULL DEFAULT \'pending\')"'),
                   "ACCEPT": HOUSE["ACCEPT"].replace("INSERT OR IGNORE", "INSERT")},
    "durable": {"ACCEPT": "threading.Thread(target=_process_one, args=(event,), daemon=True).start()",
                "WORKER_ENABLED": "False"},
}


def materialize(tmp_path: Path, overrides: dict[str, str]) -> Path:
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    code = REFERENCE
    for marker, value in {**HOUSE, **overrides}.items():
        code = code.replace(marker, value)
    (tmp_path / "app/main.py").write_text(code, encoding="utf-8")
    (tmp_path / "probe_checks.py").write_text(ORACLE.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def run(workspace: Path, check: str) -> subprocess.CompletedProcess:
    # A 4 s runbook lookup still outlasts the vendor's 3 s window, so the timing checks discriminate.
    env = dict(os.environ, PROBE_RUNBOOK_DELAY="4", PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-B", "probe_checks.py", check], cwd=workspace, env=env,
                          capture_output=True, text=True, timeout=180)


@pytest.mark.parametrize("check", CHECKS)
def test_house_reference_passes(tmp_path, check):
    result = run(materialize(tmp_path, {}), check)
    assert result.returncode == 0, result.stdout + result.stderr


# Each mutant must fail for the rule it breaks, not because the app crashed.
REASONS = {
    "signature": "signature ->",
    "fast_ack": "needs a 2xx within",
    "accepted": "answers 202 Accepted",
    "completes": "no incident titled",
    "redelivery": "three deliveries of one event made",
    "durable": "had not stored it",
}


@pytest.mark.parametrize("check", sorted(MUTANTS))
def test_mutant_fails_its_check(tmp_path, check):
    result = run(materialize(tmp_path, MUTANTS[check]), check)
    assert result.returncode == 1, result.stdout + result.stderr
    assert REASONS[check] in result.stdout, result.stdout + result.stderr


ENRICH_LATER = {
    "ACCEPT": ('with connect() as conn:\n'
               '            conn.execute(INSERT_INCIDENT, _incident_args(event, None))\n'
               '            conn.commit()\n'
               '        threading.Thread(target=_enrich_later, args=(event,), daemon=True).start()'),
    "WORKER_ENABLED": "False",
}


def test_enrich_later_design_completes(tmp_path):
    """Creating the incident first and attaching the runbook link afterwards is a valid design."""
    result = run(materialize(tmp_path, ENRICH_LATER), "completes")
    assert result.returncode == 0, result.stdout + result.stderr


def test_fixture_suite_passes_unchanged(tmp_path):
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
