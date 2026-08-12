#!/usr/bin/env python3
"""Contract tests for the create-only Codex hook receipt recorder."""
from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_harness  # noqa: E402
import codex_hook_recorder  # noqa: E402


def _payload(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "session_id": "session-private",
        "transcript_path": "C:/private/session.jsonl",
        "cwd": "C:/neutral",
        "hook_event_name": "SessionStart",
        "model": "gpt-5.6-terra",
        "permission_mode": "read-only",
        "source": "exec",
    }
    value.update(updates)
    return value


class RecorderTests(unittest.TestCase):
    def test_record_is_create_only_private_and_bound_to_nonce(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            nonce = "a" * 32
            receipt = codex_hook_recorder.record_receipt(
                json.dumps(_payload()).encode("utf-8"),
                root,
                nonce,
                receipt_id="b" * 32,
            )

            self.assertEqual(receipt.parent, root.resolve())
            self.assertEqual(receipt.name, f"receipt-{nonce}-{'b' * 32}.json")
            envelope = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(envelope["schema_version"], 1)
            self.assertEqual(envelope["nonce"], nonce)
            self.assertEqual(envelope["payload"], _payload())
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(receipt.stat().st_mode), 0o600)

            with self.assertRaises(FileExistsError):
                codex_hook_recorder.record_receipt(
                    json.dumps(_payload()).encode("utf-8"),
                    root,
                    nonce,
                    receipt_id="b" * 32,
                )

    def test_invalid_or_oversized_input_creates_no_receipt(self) -> None:
        invalid = (b"not-json", b"[]", b"{" + b"x" * codex_hook_recorder.MAX_STDIN_BYTES)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            for index, value in enumerate(invalid):
                with self.subTest(index=index):
                    with self.assertRaises(ValueError):
                        codex_hook_recorder.record_receipt(
                            value,
                            root,
                            "a" * 32,
                            receipt_id=f"{index:032x}",
                        )
            self.assertEqual([], list(root.iterdir()))

    def test_credential_shaped_payload_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            payload = _payload(source="Authorization: Bearer abcdefghijklmnopqrstuvwxyz")
            with self.assertRaises(codex_harness.CredentialExposureError):
                codex_hook_recorder.record_receipt(
                    json.dumps(payload).encode("utf-8"),
                    root,
                    "a" * 32,
                    receipt_id="c" * 32,
                )
            self.assertEqual([], list(root.iterdir()))

    def test_receipt_directory_must_be_existing_ordinary_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            missing = root / "missing"
            ordinary_file = root / "file"
            ordinary_file.write_text("not a directory", encoding="utf-8")
            for candidate in (missing, ordinary_file):
                with self.subTest(candidate=candidate.name):
                    with self.assertRaises(ValueError):
                        codex_hook_recorder.record_receipt(
                            json.dumps(_payload()).encode("utf-8"),
                            candidate,
                            "a" * 32,
                            receipt_id="d" * 32,
                        )

    def test_record_rejects_count_and_aggregate_capacity_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            nonce = "a" * 32
            first = codex_hook_recorder.record_receipt(
                json.dumps(_payload()).encode("utf-8"),
                root,
                nonce,
                receipt_id="1" * 32,
            )
            with mock.patch.object(codex_hook_recorder, "MAX_RECEIPTS", 1):
                with self.assertRaisesRegex(ValueError, "bounded capacity"):
                    codex_hook_recorder.record_receipt(
                        json.dumps(_payload()).encode("utf-8"),
                        root,
                        nonce,
                        receipt_id="2" * 32,
                    )
            with mock.patch.object(
                codex_hook_recorder,
                "MAX_TOTAL_RECEIPT_BYTES",
                first.stat().st_size + 1,
            ):
                with self.assertRaisesRegex(ValueError, "bounded capacity"):
                    codex_hook_recorder.record_receipt(
                        json.dumps(_payload()).encode("utf-8"),
                        root,
                        nonce,
                        receipt_id="3" * 32,
                    )


class ReceiptLoaderTests(unittest.TestCase):
    def test_loads_create_only_envelopes_and_orders_session_before_children(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            nonce = "a" * 32
            child = _payload(
                hook_event_name="SubagentStart",
                turn_id="turn-private",
                agent_id="agent-private",
                agent_type="save-toolkit-sre",
            )
            codex_hook_recorder.record_receipt(
                json.dumps(child).encode("utf-8"), root, nonce, receipt_id="0" * 32
            )
            codex_hook_recorder.record_receipt(
                json.dumps(_payload()).encode("utf-8"), root, nonce, receipt_id="f" * 32
            )

            parsed = codex_hook_recorder.load_receipts(root, nonce)

            self.assertEqual(2, parsed.receipt_count)
            self.assertEqual({"save-toolkit-sre": 1}, parsed.agent_type_counts)
            self.assertNotIn("session-private", repr(parsed))
            self.assertNotIn("agent-private", repr(parsed))

    def test_loader_applies_the_transient_exact_auth_validator_before_reduction(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            nonce = "a" * 32
            codex_hook_recorder.record_receipt(
                json.dumps(_payload()).encode("utf-8"),
                root,
                nonce,
                receipt_id="1" * 32,
            )
            validator = mock.Mock(
                side_effect=RuntimeError("exact auth value was present")
            )

            with self.assertRaisesRegex(RuntimeError, "exact auth value"):
                codex_hook_recorder.load_receipts(
                    root, nonce, payload_validator=validator
                )

            validator.assert_called_once()

    def test_rejects_wrong_nonce_unexpected_files_and_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            nonce = "a" * 32
            receipt = codex_hook_recorder.record_receipt(
                json.dumps(_payload()).encode("utf-8"),
                root,
                nonce,
                receipt_id="b" * 32,
            )
            with self.assertRaises(ValueError):
                codex_hook_recorder.load_receipts(root, "c" * 32)

            receipt.write_text(
                '{"schema_version":1,"schema_version":1,"nonce":"'
                + nonce
                + '","payload":{}}\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                codex_hook_recorder.load_receipts(root, nonce)

            receipt.unlink()
            (root / "unexpected.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                codex_hook_recorder.load_receipts(root, nonce)

    def test_loader_rejects_count_and_aggregate_capacity_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            nonce = "a" * 32
            receipts = [
                codex_hook_recorder.record_receipt(
                    json.dumps(_payload()).encode("utf-8"),
                    root,
                    nonce,
                    receipt_id=f"{index:032x}",
                )
                for index in (1, 2)
            ]
            with mock.patch.object(codex_hook_recorder, "MAX_RECEIPTS", 1):
                with self.assertRaisesRegex(ValueError, "bounded capacity"):
                    codex_hook_recorder.load_receipts(root, nonce)
            total = sum(item.stat().st_size for item in receipts)
            with mock.patch.object(
                codex_hook_recorder, "MAX_TOTAL_RECEIPT_BYTES", total - 1
            ):
                with self.assertRaisesRegex(ValueError, "bounded capacity"):
                    codex_hook_recorder.load_receipts(root, nonce)


if __name__ == "__main__":
    unittest.main(verbosity=2)
