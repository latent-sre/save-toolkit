#!/usr/bin/env python3
"""Create one private, fail-closed receipt for a trusted Codex command hook.

Codex supplies the hook payload on stdin.  The recorder never prints that payload and validates it
before creating a file, so credential-shaped content cannot become retained routing evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Callable, Mapping, Sequence

import codex_harness


MAX_STDIN_BYTES = 2_000_000
TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
MAX_RECEIPT_FILE_BYTES = MAX_STDIN_BYTES + 4096
MAX_RECEIPTS = 64
MAX_TOTAL_RECEIPT_BYTES = 8 * 1024 * 1024
_WRITE_LOCK_NAME = ".receipt-write.lock"


def _ordinary_directory(path: Path) -> Path:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ValueError("receipt directory must already exist") from exc
    if path.is_symlink() or not path.is_dir():
        raise ValueError("receipt directory must be an ordinary directory")
    if getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError("receipt directory must not be a reparse point")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise ValueError("receipt directory could not be resolved") from exc
    if resolved != path.absolute():
        raise ValueError("receipt directory must not traverse a link")
    return resolved


def _decode_payload(raw: bytes) -> dict[str, object]:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_STDIN_BYTES:
        raise ValueError("hook stdin must be non-empty and within the byte limit")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("hook stdin must be one UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise ValueError("hook stdin must be one JSON object")
    codex_harness.reject_credentials(value, location="hook_payload")
    return value


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("receipt envelope contains a duplicate JSON key")
        value[key] = child
    return value


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _bounded_directory_entries(
    root: Path,
    *,
    prospective_bytes: int = 0,
    excluded_name: str | None = None,
) -> list[Path]:
    """Enumerate no more receipt metadata than the fixed trial budget allows."""

    if prospective_bytes < 0 or prospective_bytes > MAX_TOTAL_RECEIPT_BYTES:
        raise ValueError("receipt directory exceeds bounded capacity")
    entries: list[Path] = []
    total_bytes = prospective_bytes
    prospective_count = 1 if prospective_bytes else 0
    try:
        with os.scandir(root) as scanner:
            for raw_entry in scanner:
                if excluded_name is not None and raw_entry.name == excluded_name:
                    continue
                entries.append(Path(raw_entry.path))
                if len(entries) + prospective_count > MAX_RECEIPTS:
                    raise ValueError("receipt directory exceeds bounded capacity")
                total_bytes += raw_entry.stat(follow_symlinks=False).st_size
                if total_bytes > MAX_TOTAL_RECEIPT_BYTES:
                    raise ValueError("receipt directory exceeds bounded capacity")
    except OSError as exc:
        raise ValueError("receipt directory could not be enumerated") from exc
    return entries


def load_receipts(
    receipt_directory: Path,
    nonce: str,
    *,
    payload_validator: Callable[[object], None] | None = None,
) -> codex_harness.ParsedHookReceipts:
    """Load one trial's create-only envelopes and immediately reduce their raw payloads."""

    if not isinstance(nonce, str) or not TOKEN_RE.fullmatch(nonce):
        raise ValueError("nonce must be exactly 32 lowercase hex characters")
    root = _ordinary_directory(Path(receipt_directory))
    filename_re = re.compile(rf"^receipt-{re.escape(nonce)}-[0-9a-f]{{32}}\.json$")
    payloads: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    entries = _bounded_directory_entries(root)
    if not entries:
        raise ValueError("receipt directory contains no hook receipts")
    for entry in entries:
        match = filename_re.fullmatch(entry.name)
        try:
            metadata = entry.lstat()
        except OSError as exc:
            raise ValueError("receipt metadata could not be read") from exc
        if (
            match is None
            or entry.is_symlink()
            or not entry.is_file()
            or getattr(metadata, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
            or getattr(metadata, "st_nlink", 1) != 1
            or metadata.st_size <= 0
            or metadata.st_size > MAX_RECEIPT_FILE_BYTES
        ):
            raise ValueError("receipt directory contains an invalid entry")
        receipt_id = entry.stem.rsplit("-", 1)[-1]
        if receipt_id in seen_ids:
            raise ValueError("receipt directory contains a duplicate receipt identity")
        seen_ids.add(receipt_id)
        try:
            raw = entry.read_bytes()
            envelope = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("receipt envelope is not canonical JSON") from exc
        if not isinstance(envelope, dict) or set(envelope) != {
            "schema_version",
            "nonce",
            "payload",
        }:
            raise ValueError("receipt envelope has the wrong shape")
        if envelope["schema_version"] != 1 or envelope["nonce"] != nonce:
            raise ValueError("receipt envelope is not bound to this trial")
        payload = envelope["payload"]
        if not isinstance(payload, dict):
            raise ValueError("receipt envelope payload must be an object")
        if payload_validator is not None:
            payload_validator(payload)
        codex_harness.reject_credentials(payload, location="hook_receipt")
        payloads.append(payload)

    session = [item for item in payloads if item.get("hook_event_name") == "SessionStart"]
    children = [item for item in payloads if item.get("hook_event_name") == "SubagentStart"]
    tools = [item for item in payloads if item.get("hook_event_name") == "PostToolUse"]
    if len(session) != 1 or len(session) + len(children) + len(tools) != len(payloads):
        raise ValueError("receipt directory has an invalid hook event set")
    ordered = [*session, *children, *tools]
    receipt_jsonl = "\n".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in ordered
    )
    return codex_harness.parse_hook_receipts(receipt_jsonl)


def record_receipt(
    raw: bytes,
    receipt_directory: Path,
    nonce: str,
    *,
    receipt_id: str | None = None,
) -> Path:
    """Validate stdin fully, then create exactly one private receipt file."""

    if not isinstance(nonce, str) or not TOKEN_RE.fullmatch(nonce):
        raise ValueError("nonce must be exactly 32 lowercase hex characters")
    chosen_id = receipt_id or uuid.uuid4().hex
    if not isinstance(chosen_id, str) or not TOKEN_RE.fullmatch(chosen_id):
        raise ValueError("receipt id must be exactly 32 lowercase hex characters")
    payload = _decode_payload(raw)
    root = _ordinary_directory(Path(receipt_directory))
    target = root / f"receipt-{nonce}-{chosen_id}.json"
    envelope: Mapping[str, object] = {
        "schema_version": 1,
        "nonce": nonce,
        "payload": payload,
    }
    encoded = (json.dumps(envelope, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    if len(encoded) > MAX_RECEIPT_FILE_BYTES:
        raise ValueError("receipt envelope exceeds the per-file byte limit")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    lock = root / _WRITE_LOCK_NAME
    lock_descriptor = os.open(lock, flags, 0o600)
    try:
        os.close(lock_descriptor)
        lock_descriptor = -1
        _bounded_directory_entries(
            root,
            prospective_bytes=len(encoded),
            excluded_name=_WRITE_LOCK_NAME,
        )
        descriptor = os.open(target, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
            raise
    finally:
        if lock_descriptor >= 0:
            os.close(lock_descriptor)
        try:
            lock.unlink(missing_ok=True)
        except OSError:
            pass
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt-directory", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args(argv)
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES + 1)
    try:
        record_receipt(raw, args.receipt_directory, args.nonce)
    except (OSError, ValueError, codex_harness.TraceError):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
