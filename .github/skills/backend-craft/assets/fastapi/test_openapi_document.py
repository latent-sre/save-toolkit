"""The committed OpenAPI document is the contract. test_document_matches_the_code fails when the
code and openapi.json disagree; after an intended API change, regenerate it and review the diff:

    UPDATE_OPENAPI=1 python -m pytest test_openapi_document.py

test_house_rules fails when an operation breaks a house rule the generator cannot know."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from main import Settings, ThingStore, create_app

DOCUMENT = Path(__file__).with_name("openapi.json")  # the service root's committed document
PUBLIC_OPERATIONS: set[str] = set()  # operation IDs that deliberately need no authentication
# In an existing service: the operation IDs that predate the house rules, so the rules apply to
# what changes add without rewriting a contract clients already use. Never add a new operation.
PREDATING_OPERATIONS: set[str] = set()


async def _refuse(token: str) -> None:
    return None


def generated_document() -> dict:
    app = create_app(Settings("127.0.0.1", 8000, None), _refuse, ThingStore())
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
    document = generated_document()
    assert document["openapi"] == "3.1.0", "emit 3.1.0, valid as 3.2"
    ids: set[str] = set()
    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            where = f"{method.upper()} {path}"
            if operation.get("operationId") in PREDATING_OPERATIONS:
                continue
            assert re.match(r"^/v[0-9]+/", path), f"{where}: API paths start with a version, /v1/"
            op_id = operation.get("operationId", "")
            assert re.fullmatch(r"[a-z][A-Za-z0-9]*", op_id) and op_id not in ids, (
                f"{where}: operationId {op_id!r} must be a unique lowerCamel name; generated clients use it"
            )
            ids.add(op_id)
            assert operation.get("security") or op_id in PUBLIC_OPERATIONS, (
                f"{where}: depend on authenticated, or list it in PUBLIC_OPERATIONS"
            )
            if "requestBody" in operation:
                assert "400" in operation["responses"], f"{where}: a body can be unparseable; declare 400"
            for status, response in operation["responses"].items():
                if status.isdigit() and int(status) >= 400:
                    assert list(response.get("content", {})) == ["application/problem+json"], (
                        f"{where}: {status} must be application/problem+json"
                    )
