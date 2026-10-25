"""Frozen SWT selection, public input, patch admission and separate assessments."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from swebench_adapter.artifacts import store_json

UPSTREAM_REVISION = "330a649a764fab2fadaea632776eeae87272f74b"
DATASET = "SWE-bench/SWE-bench_Verified"
DATASET_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"
VARIANTS = ("pred_pre", "pred_post", "gold_pre", "gold_post", "base_pre", "base_post")
MAX_PATCH = 1024 * 1024


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def select(manifest: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], excluded: set[str]) -> list[dict[str, Any]]:
    if (
        manifest.get("schema_version") != 1
        or manifest.get("upstream_revision") != UPSTREAM_REVISION
        or manifest.get("dataset") != DATASET
        or manifest.get("dataset_revision") != DATASET_REVISION
    ):
        raise ValueError("unsupported SWT source identity")
    by_id = {r["instance_id"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("duplicate dataset identity")
    cases = manifest.get("cases", [])
    if not cases or len({c["instance_id"] for c in cases}) != len(cases):
        raise ValueError("missing or duplicate selected case")
    result = []
    for case in cases:
        identity = case["instance_id"]
        if identity in excluded:
            raise ValueError("selected instance is upstream-excluded")
        row = by_id.get(identity)
        if row is None or digest(row) != case["row_sha256"]:
            raise ValueError("selected row identity mismatch")
        if row.get("difficulty") not in {"1-4 hours", ">4 hours"}:
            raise ValueError("complex pilot requires upstream difficulty of at least one hour")
        if re.fullmatch(r"[0-9a-f]{40}", row.get("base_commit", "")) is None:
            raise ValueError("invalid immutable base commit")
        for field in ("patch", "test_patch"):
            if not isinstance(row.get(field), str) or not row[field].startswith("diff --git "):
                raise ValueError("original SWE patch roles required")
        result.append(dict(row))
    return result


def transform(row: Mapping[str, Any]) -> dict[str, Any]:
    """Equivalent to upstream swe_to_swt_instance, preserving the input object."""
    value = dict(row)
    value["golden_code_patch"] = value.pop("patch")
    value["golden_test_patch"] = value.pop("test_patch")
    return value


def author_input(row: Mapping[str, Any]) -> dict[str, Any]:
    return {k: row[k] for k in ("instance_id", "repo", "base_commit", "problem_statement")}


def stage(
    manifest: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], excluded: set[str], output: Path
) -> dict[str, str]:
    selected = select(manifest, rows, excluded)
    if output.exists():
        raise ValueError("staging destination already exists")
    output.mkdir(parents=True, mode=0o700)
    # These are different directories and must never be jointly mounted to the author.
    private = store_json(output / "verifier-only", "dataset.json", selected)
    public = store_json(output / "author-only", "tasks.json", [author_input(r) for r in selected])
    store_json(
        output,
        "staging-receipt.json",
        {
            "manifest_sha256": digest(manifest),
            "rows": [digest(r) for r in selected],
            "dataset_sha256": hashlib.sha256(private.read_bytes()).hexdigest(),
            "author_sha256": hashlib.sha256(public.read_bytes()).hexdigest(),
            "upstream_revision": UPSTREAM_REVISION,
            "upstream_is_swt": False,
            "filter_applied_locally": True,
            "live_execution": False,
        },
    )
    return {"dataset": str(private), "author": str(public)}


def admit_patch(patch: str, roots: Sequence[str]) -> dict[str, Any]:
    """Conservative structural checks; a pass never establishes semantic relevance."""
    result = {
        "state": "FAIL",
        "reason": "invalid or empty test patch",
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
    }
    if not patch.strip() or len(patch.encode()) > MAX_PATCH:
        return result
    if not roots or any(not r.endswith("/") or r.startswith("/") or ".." in PurePosixPath(r).parts for r in roots):
        return result
    headers = re.findall(r"^diff --git a/(\S+) b/(\S+)$", patch, re.MULTILINE)
    if not headers or len(headers) != patch.count("diff --git ") or not re.search(r"^@@ ", patch, re.MULTILINE):
        return result
    forbidden = (
        "GIT binary patch",
        "Binary files ",
        "new mode ",
        "old mode ",
        "deleted file mode ",
        "rename from ",
        "rename to ",
    )
    if any(token in patch for token in forbidden) or re.search(
        r"^(?:new file mode|index .* )120000", patch, re.MULTILINE
    ):
        return result
    paths = []
    for old, new in headers:
        path = PurePosixPath(new)
        if (
            old != new
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in new
            or not any(new.startswith(root) for root in roots)
            or any(p.startswith(".") for p in path.parts)
        ):
            result["reason"] = "patch modifies a non-test or unsafe path"
            return result
        paths.append(new)
    file_headers = re.findall(r"^(---|\+\+\+) (.*)$", patch, re.MULTILINE)
    if len(file_headers) != 2 * len(headers):
        return result
    for index, (old, new) in enumerate(headers):
        if file_headers[2 * index] not in [("---", "a/" + old), ("---", "/dev/null")] or file_headers[
            2 * index + 1
        ] != ("+++", "b/" + new):
            return result
    added = "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
    suspicious = (
        r"golden_(?:code|test)_patch|inspect\.getsource|subprocess|os\.system|\.git\b|__file__|[\"\'][^\"\']*\.py[\"\']"
    )
    if re.search(suspicious, added):
        result["reason"] = "source-text/process access requires rejection or a separately reviewed profile"
        return result
    return {**result, "state": "PASS", "reason": "test paths admitted; semantic review pending", "paths": paths}


def prediction(instance_id: str, patch: str, roots: Sequence[str]) -> dict[str, str]:
    admission = admit_patch(patch, roots)
    if admission["state"] != "PASS":
        raise ValueError(admission["reason"])
    return {"instance_id": instance_id, "model_name_or_path": "wp09-static-tests", "model_patch": patch}


def assess(
    instance_id: str, report: Any, variants: Any, admission: Mapping[str, Any], *, relevance: Any = None
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "mechanical": "INCONCLUSIVE",
        "admission": admission["state"],
        "relevance": "UNVERIFIED",
        "verdict": "INCONCLUSIVE",
        "upstream_report": report,
        "reason": "incomplete verifier evidence",
    }
    if admission["state"] != "PASS":
        return {**result, "verdict": "FAIL", "reason": admission["reason"]}
    if (
        not isinstance(report, dict)
        or set(report) != {instance_id}
        or not isinstance(variants, dict)
        or set(variants) != set(VARIANTS)
    ):
        return result
    original = report[instance_id]
    flags = ("patch_is_None", "patch_exists", "patch_successfully_applied", "resolved")
    if not isinstance(original, dict) or any(type(original.get(f)) is not bool for f in flags):
        return result
    for name, evidence in variants.items():
        if (
            not isinstance(evidence, dict)
            or evidence.get("completed") is not True
            or evidence.get("patch_applied") is not True
        ):
            return result
        tests = evidence.get("tests")
        if not isinstance(tests, dict) or (not tests and not name.startswith("base_")):
            return result
        if any(not isinstance(t, str) or s not in ("PASSED", "FAILED", "ERROR", "SKIPPED") for t, s in tests.items()):
            return result
    gold_pre, gold_post = variants["gold_pre"]["tests"], variants["gold_post"]["tests"]
    if not any(s == "FAILED" and gold_post.get(t) == "PASSED" for t, s in gold_pre.items()) or any(
        s in {"FAILED", "ERROR"} for s in gold_post.values()
    ):
        return {**result, "reason": "gold control did not establish the expected environment"}
    pre, post = variants["pred_pre"]["tests"], variants["pred_post"]["tests"]
    base_pre, base_post = variants["base_pre"]["tests"], variants["base_post"]["tests"]
    new_f2p = [
        t
        for t in pre
        if pre[t] == "FAILED"
        and post.get(t) == "PASSED"
        and not (base_pre.get(t) == "FAILED" and base_post.get(t) == "PASSED")
    ]
    # Upstream treats missing/error-before as F2P. AC-13 deliberately requires an observed assertion failure.
    failures = any(s in {"FAILED", "ERROR"} for s in post.values())
    mechanical = (
        "PASS"
        if new_f2p
        and not failures
        and original["resolved"]
        and original["patch_exists"]
        and original["patch_successfully_applied"]
        and not original["patch_is_None"]
        else "FAIL"
    )
    result.update(
        mechanical=mechanical,
        verdict="FAIL" if mechanical == "FAIL" else "INCONCLUSIVE",
        reason="semantic relevance pending"
        if mechanical == "PASS"
        else "no valid new fail-before/pass-after reproduction",
    )
    if (
        isinstance(relevance, dict)
        and relevance.get("state") in {"PASS", "FAIL"}
        and relevance.get("reviewer")
        and relevance.get("reason")
        and relevance.get("patch_sha256") == admission["patch_sha256"]
    ):
        result["relevance"] = relevance["state"]
        result["verdict"] = "PASS" if mechanical == relevance["state"] == "PASS" else "FAIL"
        result["reason"] = relevance["reason"]
    return result
