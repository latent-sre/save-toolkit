"""Reusable problem, request-ID and API-document assertions for real-service tests."""
from __future__ import annotations

import re


def assert_problem(response, status: int) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert {"type", "title", "status", "request_id"} <= body.keys(), body
    assert body["status"] == status
    assert body["request_id"] and body["request_id"] == response.headers["x-request-id"]
    return body


def assert_document_rules(document: dict, *, auth_scheme: str | None, public_operations: set[str],
                          auth_error_statuses: set[int] | frozenset[int] = frozenset()) -> None:
    """Check the house contract using the service's actual named identity scheme.

    An explicit operation security list overrides a document-level requirement. Every protected
    alternative must require auth_scheme; empty alternatives allow anonymous access. For a wholly
    unauthenticated service use None and explicitly list its public operation IDs. Protected routes
    declare 401 plus the integration's other failures (for example 503 for a verifier outage).
    """
    assert document["openapi"] == "3.1.0", "emit 3.1.0, valid as 3.2"
    schemes = document.get("components", {}).get("securitySchemes", {})
    ids: set[str] = set()
    for path, operations in document["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "put", "post", "delete", "options", "head", "patch", "trace"}:
                continue  # path-level parameters and extensions are not operations
            where = f"{method.upper()} {path}"
            op_id = operation.get("operationId", "")
            assert op_id not in ids, f"{where}: operationId {op_id!r} is not unique; generated clients use it"
            ids.add(op_id)
            assert re.match(r"^/v[0-9]+/", path), f"{where}: API paths start with a version, /v1/"
            assert re.fullmatch(r"[a-z][A-Za-z0-9]*", op_id), (
                f"{where}: operationId {op_id!r} must be a lowerCamel name; generated clients use it"
            )
            security = operation.get("security", document.get("security", []))
            assert all(name in schemes for alternative in security for name in alternative), (
                f"{where}: security names an undeclared scheme"
            )
            if op_id in public_operations:
                assert not security, f"{where}: public operation must have empty effective security"
            else:
                assert auth_scheme is not None and security and all(auth_scheme in alt for alt in security), (
                    f"{where}: require {auth_scheme!r}, or list it in PUBLIC_OPERATIONS"
                )
                for status in {401} | auth_error_statuses:
                    assert str(status) in operation["responses"], f"{where}: declare authentication failure {status}"
            if "requestBody" in operation:
                assert "400" in operation["responses"], f"{where}: a body can be unparseable; declare 400"
            for status, response in operation["responses"].items():
                if status.isdigit() and int(status) >= 400:
                    assert list(response.get("content", {})) == ["application/problem+json"], (
                        f"{where}: {status} must be application/problem+json"
                    )
    assert ids, "document contains no HTTP operations"
