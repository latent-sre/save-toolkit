"""No-model regressions for the incident-writes oracle: a house-rule reference passes, mutants fail."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-incident-writes.yaml"
ORACLE = ROOT / "evals/oracles/incident-writes/probe_checks.py"
CHECKS = ["create", "replay", "replay_header", "conflict", "missing_key", "concurrent", "distinct_keys"]

REFERENCE = '''
"""opsapi application factory."""
from __future__ import annotations

import hashlib
import json
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import store
from app.db import connect, init_schema
from app.errors import install_problem_handlers
from app.schemas import IncidentOut

KEYS = "CREATE TABLE IF NOT EXISTS idempotency_keys (key TEXT PRIMARY KEY, fingerprint TEXT, body TEXT)"


def _own_insert(conn, title: str, service: str) -> dict:
    """Writes with its own SQL, bypassing store.create_incident (and its 300 ms delay)."""
    import time, uuid
    from datetime import datetime, timezone
    row = {"id": f"inc-{uuid.uuid4().hex[:12]}", "title": title, "service": service, "status": "open",
           "created_at": datetime.now(timezone.utc).isoformat()}
    time.sleep(0.3)
    conn.execute("INSERT INTO incidents (id, title, service, status, created_at)"
                 " VALUES (:id, :title, :service, :status, :created_at)", row)
    return row


class IncidentIn(BaseModel):
    title: str
    service: str


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_schema()
        with connect() as conn:
            conn.execute(KEYS)
        yield

    app = FastAPI(title="opsapi", lifespan=lifespan)
    install_problem_handlers(app)

    @app.get("/v1/incidents/{incident_id}", response_model=IncidentOut)
    def get_incident(incident_id: str) -> IncidentOut:
        with connect() as conn:
            row = store.get_incident(conn, incident_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown incident")
        return IncidentOut(**row)

    @app.post("/v1/incidents", status_code=201)
    def create(payload: IncidentIn, idempotency_key: Annotated[str | None, Header()] = None):
        if not idempotency_key:
            KEY_MISSING
        fingerprint = hashlib.sha256(json.dumps(payload.model_dump(), sort_keys=True).encode()).hexdigest()
        with connect() as conn:
            LOCK
            seen = conn.execute(LOOKUP, LOOKUP_ARGS).fetchone()
            if seen is not None:
                conn.rollback()
                if FINGERPRINT_CHECK:
                    raise HTTPException(422, "Idempotency-Key reused with a different payload")
                return JSONResponse(REPLAY_BODY, status_code=201, headers=REPLAY_HEADERS)
            row = CREATE_CALL
            body = IncidentOut(**row).model_dump()
            conn.execute("INSERT OR IGNORE INTO idempotency_keys VALUES (?, ?, ?)",
                         (idempotency_key, fingerprint, json.dumps(body)))
            conn.commit()
        return JSONResponse(body, status_code=201)

    return app
'''
HOUSE = {
    "KEY_MISSING": 'raise HTTPException(400, "Idempotency-Key is required")',
    "LOCK": 'conn.execute("BEGIN IMMEDIATE")',
    "LOOKUP_ARGS": "(idempotency_key,)",
    "LOOKUP": '"SELECT fingerprint, body FROM idempotency_keys WHERE key = ?"',
    "FINGERPRINT_CHECK": 'seen["fingerprint"] != fingerprint',
    "REPLAY_BODY": 'json.loads(seen["body"])',
    "REPLAY_HEADERS": '{"Idempotent-Replayed": "true"}',
    "CREATE_CALL": "store.create_incident(conn, payload.title, payload.service)",
}
# store.create_incident commits by itself; the reference defers that commit so the incident and its
# key commit together, which is what makes the lock above sufficient.
STORE_COMMIT = ("    conn.commit()\n    return row", "    return row")
STORE_OPEN = '"status": "open"'
# name: (check that must fail, overrides, expected failure text, store options)
MUTANTS = {
    "conflict": ("conflict", {"FINGERPRINT_CHECK": "False"}, "same key, different payload -> 201", {}),
    "missing_key": ("missing_key", {"KEY_MISSING": "idempotency_key = 'anonymous-' + __import__('uuid').uuid4().hex"},
                    "without Idempotency-Key -> 201", {}),
    # Check-then-insert without a lock, with the store's own commit: a real race.
    "concurrent": ("concurrent", {"LOCK": "pass"}, "left 2 rows", {"defer_commit": False}),
    "distinct_keys": ("distinct_keys",
                      {"LOOKUP": '"SELECT k.fingerprint, k.body FROM idempotency_keys k WHERE json_extract(k.body, \'$.title\') = ?"',
                       "LOOKUP_ARGS": "(payload.title,)", "FINGERPRINT_CHECK": "False"},
                      "were merged", {}),
    "replay_header": ("replay_header", {"REPLAY_HEADERS": "{}"}, "lacks Idempotent-Replayed", {}),
    "replay_partial": ("replay", {"REPLAY_BODY": '{"id": json.loads(seen["body"])["id"]}'},
                       "expected the first result exactly", {}),
    "status_closed": ("create", {}, "must start open", {"status": "closed"}),
    # Own SQL, no lock: the gate cannot hold it, so the barrier fallback must still catch the race.
    "own_sql_unlocked": ("concurrent",
                         {"CREATE_CALL": "_own_insert(conn, payload.title, payload.service); conn.commit()",
                          "LOCK": "pass"},
                         "left 2 rows (client-side barrier fallback", {}),
}


def materialize(tmp_path: Path, overrides: dict[str, str], defer_commit: bool = True, status: str = "open") -> Path:
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    code = REFERENCE
    for marker, value in {**HOUSE, **overrides}.items():
        code = code.replace(marker, value)
    (tmp_path / "app/main.py").write_text(code, encoding="utf-8")
    store = tmp_path / "app/store.py"
    text = store.read_text(encoding="utf-8")
    assert STORE_COMMIT[0] in text and STORE_OPEN in text, "fixture store changed; update the reference"
    if defer_commit:
        text = text.replace(*STORE_COMMIT)
    store.write_text(text.replace(STORE_OPEN, f'"status": "{status}"'), encoding="utf-8")
    (tmp_path / "probe_checks.py").write_text(ORACLE.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def run(workspace: Path, check: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", "probe_checks.py", check], cwd=workspace,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("check", CHECKS)
def test_house_reference_passes(tmp_path, check):
    result = run(materialize(tmp_path, {}), check)
    assert result.returncode == 0, result.stdout + result.stderr


def test_concurrency_overlap_is_observed_server_side(tmp_path):
    """The oracle sends the second request only once the first is inside the write path."""
    result = run(materialize(tmp_path, {}), "concurrent")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "second request sent while the first was held inside store.create_incident" in result.stdout


def test_own_sql_locked_design_passes_through_the_fallback(tmp_path):
    """A correct app that bypasses store.create_incident is raced from a barrier, not failed."""
    overrides = {"CREATE_CALL": "_own_insert(conn, payload.title, payload.service)"}
    result = run(materialize(tmp_path, overrides), "concurrent")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "client-side barrier fallback" in result.stdout


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_mutant_fails_its_check(tmp_path, name):
    check, overrides, reason, store = MUTANTS[name]
    result = run(materialize(tmp_path, overrides, store.get("defer_commit", True), store.get("status", "open")), check)
    assert result.returncode == 1, result.stdout + result.stderr
    assert reason in result.stdout, result.stdout + result.stderr


def test_fixture_suite_passes_unchanged(tmp_path):
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
