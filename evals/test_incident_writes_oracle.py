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
                return JSONResponse(json.loads(seen["body"]), status_code=201, headers=REPLAY_HEADERS)
            row = store.create_incident(conn, payload.title, payload.service)
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
    "REPLAY_HEADERS": '{"Idempotent-Replayed": "true"}',
}
# store.create_incident commits by itself; the reference defers that commit so the incident and its
# key commit together, which is what makes the lock above sufficient.
STORE_PATCH = ("    conn.commit()\n    return row", "    return row")
MUTANTS = {
    # check that must fail: the one house rule the mutant breaks
    "conflict": {"FINGERPRINT_CHECK": "False"},
    "missing_key": {"KEY_MISSING": "idempotency_key = 'anonymous-' + __import__('uuid').uuid4().hex"},
    "concurrent": {"LOCK": "pass"},
    "distinct_keys": {"LOOKUP": '"SELECT k.fingerprint, k.body FROM idempotency_keys k WHERE json_extract(k.body, \'$.title\') = ?"',
                      "LOOKUP_ARGS": "(payload.title,)", "FINGERPRINT_CHECK": "False"},
    "replay_header": {"REPLAY_HEADERS": "{}"},
}


def materialize(tmp_path: Path, overrides: dict[str, str], defer_store_commit: bool) -> Path:
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    code = REFERENCE
    for marker, value in {**HOUSE, **overrides}.items():
        code = code.replace(marker, value)
    (tmp_path / "app/main.py").write_text(code, encoding="utf-8")
    if defer_store_commit:
        store = tmp_path / "app/store.py"
        text = store.read_text(encoding="utf-8")
        assert STORE_PATCH[0] in text, "fixture store changed; update the reference"
        store.write_text(text.replace(*STORE_PATCH), encoding="utf-8")
    (tmp_path / "probe_checks.py").write_text(ORACLE.read_text(encoding="utf-8"), encoding="utf-8")
    return tmp_path


def run(workspace: Path, check: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", "probe_checks.py", check], cwd=workspace,
                          capture_output=True, text=True, timeout=120)


@pytest.mark.parametrize("check", CHECKS)
def test_house_reference_passes(tmp_path, check):
    result = run(materialize(tmp_path, {}, defer_store_commit=True), check)
    assert result.returncode == 0, result.stdout + result.stderr


# Each mutant must fail for the rule it breaks, not because the app crashed.
REASONS = {
    "conflict": "same key, different payload -> 201",
    "missing_key": "without Idempotency-Key -> 201",
    "concurrent": "left 2 rows",
    "distinct_keys": "were merged",
    "replay_header": "lacks Idempotent-Replayed",
}


@pytest.mark.parametrize("check", sorted(MUTANTS))
def test_mutant_fails_its_check(tmp_path, check):
    # The concurrency mutant keeps the store's own commit too: check-then-insert without a lock.
    result = run(materialize(tmp_path, MUTANTS[check], defer_store_commit=check != "concurrent"), check)
    assert result.returncode == 1, result.stdout + result.stderr
    assert REASONS[check] in result.stdout, result.stdout + result.stderr


def test_fixture_suite_passes_unchanged(tmp_path):
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    for rel, text in spec["fixture"]["files"].items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
