"""Document checks: supply the actual app and identity scheme in contract_app.py.
Public means deliberately unauthenticated, not merely internet-facing.
The committed OpenAPI document is the contract. test_document_matches_the_code fails when the
code and openapi.json disagree; after an intended API change, regenerate it and review the diff:

    UPDATE_OPENAPI=1 python -m pytest test_openapi_document.py

test_house_rules fails when an operation breaks a house rule the generator cannot know."""
from __future__ import annotations

import json
import os
from pathlib import Path

from contract_app import AUTH_ERROR_STATUSES, AUTH_SCHEME, PUBLIC_OPERATIONS, make_app
from contract_checks import assert_document_rules
from fastapi.testclient import TestClient


def _service_root() -> Path:
    here = Path(__file__).resolve().parent
    markers = ("pyproject.toml", ".git")
    return next((p for p in (here, *here.parents) if any((p / m).exists() for m in markers)), here)


DOCUMENT = _service_root() / "openapi.json"  # beside the service's pyproject.toml; CI uses the same directory


def generated_document() -> dict:
    app = make_app()
    with TestClient(app):
        return app.openapi()


def test_document_matches_the_code():
    text = json.dumps(generated_document(), indent=2, sort_keys=True) + "\n"
    if os.environ.get("UPDATE_OPENAPI") == "1":
        DOCUMENT.write_text(text, encoding="utf-8", newline="\n")
        return
    assert DOCUMENT.exists(), "generate it: UPDATE_OPENAPI=1 python -m pytest test_openapi_document.py"
    committed = DOCUMENT.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert committed == text, (
        "openapi.json differs from the code: regenerate with UPDATE_OPENAPI=1, "
        "then review the document diff as the API change it is"
    )


def test_house_rules():
    assert_document_rules(generated_document(), auth_scheme=AUTH_SCHEME, public_operations=PUBLIC_OPERATIONS,
                          auth_error_statuses=AUTH_ERROR_STATUSES)
