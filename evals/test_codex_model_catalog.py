#!/usr/bin/env python3
"""Contract tests for the no-filesystem-tools Terra catalog transform."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_model_catalog  # noqa: E402


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _entry(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "slug": "gpt-5.6-terra",
        "display_name": "GPT-5.6 Terra",
        "tool_mode": "code_mode_only",
        "apply_patch_tool_type": "freeform",
        "shell_type": "shell_command",
        "supports_search_tool": True,
        "experimental_supported_tools": ["unsafe-demo"],
        "context_window": 1_050_000,
        "base_instructions": "public model instructions",
    }
    value.update(updates)
    return value


def _expected(entry: dict[str, object]) -> tuple[bytes, str, str, str]:
    transformed = dict(entry)
    transformed.update(
        {
            "apply_patch_tool_type": None,
            "tool_mode": None,
            "supports_search_tool": False,
            "experimental_supported_tools": [],
        }
    )
    source_sha = hashlib.sha256(_canonical(entry)).hexdigest()
    transformed_sha = hashlib.sha256(_canonical(transformed)).hexdigest()
    catalog = _canonical({"models": [transformed]})
    return catalog, source_sha, transformed_sha, hashlib.sha256(catalog).hexdigest()


class SafeCatalogTests(unittest.TestCase):
    def test_changes_only_the_four_tool_fields_and_returns_hash_facts(self) -> None:
        entry = _entry()
        expected, source_sha, transformed_sha, catalog_sha = _expected(entry)
        raw = _canonical({"models": [_entry(slug="other"), entry]})
        with mock.patch.multiple(
            codex_model_catalog,
            EXPECTED_SOURCE_ENTRY_SHA256=source_sha,
            EXPECTED_TRANSFORMED_ENTRY_SHA256=transformed_sha,
            EXPECTED_SAFE_CATALOG_SHA256=catalog_sha,
        ):
            encoded, receipt = codex_model_catalog.build_safe_catalog(raw)

        self.assertEqual(expected, encoded)
        self.assertEqual("gpt-5.6-terra", receipt.model)
        self.assertEqual(source_sha, receipt.source_entry_sha256)
        self.assertEqual(transformed_sha, receipt.transformed_entry_sha256)
        self.assertEqual(catalog_sha, receipt.safe_catalog_sha256)
        self.assertEqual(
            (
                "apply_patch_tool_type",
                "experimental_supported_tools",
                "supports_search_tool",
                "tool_mode",
            ),
            receipt.changed_fields,
        )
        self.assertNotIn("public model instructions", repr(receipt))

    def test_any_unreviewed_source_field_drift_fails_closed(self) -> None:
        entry = _entry()
        _expected_bytes, source_sha, transformed_sha, catalog_sha = _expected(entry)
        drifted = dict(entry, context_window=999)
        with mock.patch.multiple(
            codex_model_catalog,
            EXPECTED_SOURCE_ENTRY_SHA256=source_sha,
            EXPECTED_TRANSFORMED_ENTRY_SHA256=transformed_sha,
            EXPECTED_SAFE_CATALOG_SHA256=catalog_sha,
        ):
            with self.assertRaises(codex_model_catalog.CatalogError):
                codex_model_catalog.build_safe_catalog(
                    _canonical({"models": [drifted]})
                )

    def test_duplicate_model_or_json_key_and_wrong_tool_metadata_fail_closed(self) -> None:
        cases = (
            _canonical({"models": [_entry(), _entry()]}),
            b'{"models":[],"models":[]}',
            _canonical({"models": [_entry(tool_mode="default")]}),
        )
        for raw in cases:
            with self.subTest(raw_length=len(raw)):
                with self.assertRaises(codex_model_catalog.CatalogError):
                    codex_model_catalog.build_safe_catalog(raw)

    def test_write_is_create_only_and_private(self) -> None:
        entry = _entry()
        expected, source_sha, transformed_sha, catalog_sha = _expected(entry)
        with tempfile.TemporaryDirectory() as raw_dir:
            destination = Path(raw_dir) / "route-models.json"
            with mock.patch.multiple(
                codex_model_catalog,
                EXPECTED_SOURCE_ENTRY_SHA256=source_sha,
                EXPECTED_TRANSFORMED_ENTRY_SHA256=transformed_sha,
                EXPECTED_SAFE_CATALOG_SHA256=catalog_sha,
            ):
                receipt = codex_model_catalog.write_safe_catalog(
                    _canonical({"models": [entry]}), destination
                )
                with self.assertRaises(FileExistsError):
                    codex_model_catalog.write_safe_catalog(
                        _canonical({"models": [entry]}), destination
                    )
            self.assertEqual(expected, destination.read_bytes())
            self.assertEqual(catalog_sha, receipt.safe_catalog_sha256)
            if os.name != "nt":
                self.assertEqual(0o600, destination.stat().st_mode & 0o777)

    def test_production_digests_are_pinned_to_installed_0147_bytes(self) -> None:
        self.assertEqual(
            "dd06f2ae3786e852ca884d6c189a364da38f7b7492fd960b05cdd2e3e232e443",
            codex_model_catalog.EXPECTED_SOURCE_ENTRY_SHA256,
        )
        self.assertEqual(
            "ac89f9a13959269da2f67c095f10d4da76890c04eda12c01c58d3c40e64faf71",
            codex_model_catalog.EXPECTED_TRANSFORMED_ENTRY_SHA256,
        )
        self.assertEqual(
            "2d23cea7bd13463424eca49df927a38f8480501820eec853e3789015c6a321b6",
            codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
