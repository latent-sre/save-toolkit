#!/usr/bin/env python3
"""Contract tests for exact-SHA immutable release requests."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import release_contract


NOW = datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc)
CANDIDATE = "a" * 40
RUN_ID = "17762861431"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PRE_ONE_VERSION = "0.1.0"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _fixture(root: Path, *, version: str = "1.0.0") -> None:
    identity = {
        "name": "save-toolkit",
        "version": version,
    }
    _write_json(root / ".claude-plugin" / "plugin.json", identity)
    _write_json(
        root / ".claude-plugin" / "marketplace.json",
        {
            "name": "latent-sre",
            "plugins": [
                {
                    "name": "save-toolkit",
                    "source": "./",
                    "version": version,
                }
            ],
        },
    )
    _write_json(root / "plugin.json", identity)
    _write_json(root / "plugins" / "save-toolkit" / ".codex-plugin" / "plugin.json", identity)
    root.joinpath("CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.0.0] - 2026-08-11\n\n"
        "### Added\n\n"
        "- Initial immutable multi-host release.\n\n"
        "## [0.9.0] - 2026-07-31\n\n"
        "- Private preview.\n",
        encoding="utf-8",
    )


def _build(root: Path, **overrides: object) -> dict[str, object]:
    arguments: dict[str, object] = {
        "root": root,
        "candidate_sha": CANDIDATE,
        "version": "1.0.0",
        "run_id": RUN_ID,
        "actor": "release-owner",
        "triggering_actor": "release-owner",
        "review_evidence": "https://github.com/latent-sre/save-toolkit/pull/103",
        "workflow_ref": "latent-sre/save-toolkit/.github/workflows/release.yml@refs/heads/main",
        "workflow_sha": CANDIDATE,
        "issued_at": NOW,
        "expires_at": NOW + timedelta(hours=2),
        "recovery_tag": "uninstall",
        "recovery_sha": "",
        "head_sha": CANDIDATE,
        "main_sha": CANDIDATE,
        "clean": True,
        "now": NOW,
    }
    arguments.update(overrides)
    return release_contract.build_release_packet(**arguments)  # type: ignore[arg-type]


class ReleasePacketTests(unittest.TestCase):
    def test_repository_release_candidate_remains_pre_one_until_v1_is_authorized(self) -> None:
        versions = release_contract._manifest_versions(REPOSITORY_ROOT)

        self.assertEqual({PRE_ONE_VERSION}, set(versions.values()))
        self.assertIn(
            f"## [{PRE_ONE_VERSION}] - 2026-08-11",
            REPOSITORY_ROOT.joinpath("CHANGELOG.md").read_text(encoding="utf-8"),
        )

    def test_same_run_issued_at_makes_the_packet_byte_stable_across_reruns(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            first = _build(root, issued_at=NOW, now=NOW)
            rerun = _build(
                root,
                issued_at=NOW,
                now=NOW + timedelta(minutes=15),
            )

        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(rerun, sort_keys=True, separators=(",", ":")),
        )
        self.assertEqual("2026-08-11T18:00:00Z", first["approval"]["issued_at"])

    def test_timestamps_are_exact_whole_second_utc_values(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            release_contract._parse_timestamp("2026-08-11T20:00:00.123Z")

        mutations = (
            {"issued_at": NOW.replace(microsecond=1)},
            {"expires_at": (NOW + timedelta(hours=2)).replace(microsecond=1)},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    _fixture(root)
                    with self.assertRaisesRegex(
                        release_contract.ReleaseContractError,
                        "whole-second|fraction",
                    ):
                        _build(root, **mutation)

    def test_stable_issuance_does_not_make_an_expired_rerun_fresh(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            with self.assertRaisesRegex(release_contract.ReleaseContractError, "future|expired"):
                _build(
                    root,
                    issued_at=NOW,
                    now=NOW + timedelta(hours=3),
                    expires_at=NOW + timedelta(hours=2),
                )

    def test_valid_request_binds_effect_and_extracts_only_this_versions_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            packet = _build(root)

        self.assertEqual(1, packet["schema_version"])
        self.assertEqual("latent-sre/save-toolkit", packet["repository"])
        self.assertEqual("publish-immutable-release", packet["effect"]["action"])
        self.assertEqual("save-toolkit--v1.0.0", packet["effect"]["tag"])
        self.assertEqual(CANDIDATE, packet["effect"]["candidate_sha"])
        self.assertEqual(RUN_ID, packet["approval"]["run_id"])
        self.assertEqual(
            "https://github.com/latent-sre/save-toolkit/pull/103",
            packet["approval"]["review_evidence"],
        )
        self.assertEqual(CANDIDATE, packet["approval"]["workflow_sha"])
        self.assertEqual("uninstall", packet["rollback"]["mode"])
        self.assertIn("Initial immutable multi-host release", packet["release_notes"])
        self.assertNotIn("Private preview", packet["release_notes"])
        self.assertEqual(
            "latent-sre/save-toolkit@save-toolkit--v1.0.0",
            packet["distribution"]["marketplace_source"],
        )

    def test_every_version_bearing_manifest_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            manifest = root / "plugins" / "save-toolkit" / ".codex-plugin" / "plugin.json"
            value = json.loads(manifest.read_text(encoding="utf-8"))
            value["version"] = "1.0.1"
            _write_json(manifest, value)
            with self.assertRaisesRegex(release_contract.ReleaseContractError, "version parity"):
                _build(root)

    def test_exact_version_heading_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            root.joinpath("CHANGELOG.md").write_text(
                "# Changelog\n\n## [Unreleased]\n\n- No release section.\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(release_contract.ReleaseContractError, "changelog"):
                _build(root)

    def test_version_heading_must_be_unique_and_nonempty(self) -> None:
        mutations = {
            "duplicate": (
                "# Changelog\n\n"
                "## [1.0.0] - 2026-08-11\n\n- First copy.\n\n"
                "## [1.0.0] - 2026-08-11\n\n- Second copy.\n"
            ),
            "empty": "# Changelog\n\n## [1.0.0] - 2026-08-11\n\n",
        }
        for name, changelog in mutations.items():
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    _fixture(root)
                    root.joinpath("CHANGELOG.md").write_text(changelog, encoding="utf-8")
                    with self.assertRaisesRegex(
                        release_contract.ReleaseContractError,
                        "changelog|release notes|exactly one",
                    ):
                        _build(root)

    def test_candidate_must_be_clean_exact_main_and_workflow_revision(self) -> None:
        mutations = {
            "head_sha": "b" * 40,
            "main_sha": "b" * 40,
            "workflow_sha": "b" * 40,
            "clean": False,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    _fixture(root)
                    with self.assertRaisesRegex(
                        release_contract.ReleaseContractError,
                        "candidate|clean|workflow",
                    ):
                        _build(root, **{field: value})

    def test_request_identity_and_expiry_fail_closed(self) -> None:
        mutations = (
            ("candidate_sha", "abc"),
            ("candidate_sha", "A" * 40),
            ("run_id", "run-7"),
            ("actor", ""),
            ("triggering_actor", "someone-else"),
            ("review_evidence", "https://example.com/assertion"),
            ("expires_at", NOW),
            ("expires_at", NOW + timedelta(hours=25)),
            ("expires_at", datetime(2026, 8, 11, 15, 0, tzinfo=timezone(timedelta(hours=-5)))),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    _fixture(root)
                    with self.assertRaises(release_contract.ReleaseContractError):
                        _build(root, **{field: value})

    def test_recovery_is_uninstall_or_a_different_version_tag(self) -> None:
        for recovery in (
            "main",
            "save-toolkit--v1.0.0",
            "save-toolkit--v1.0.1",
            "v0.9.0",
        ):
            with self.subTest(recovery=recovery):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    _fixture(root)
                    with self.assertRaisesRegex(release_contract.ReleaseContractError, "recovery"):
                        _build(root, recovery_tag=recovery, recovery_sha="b" * 40)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            with self.assertRaisesRegex(release_contract.ReleaseContractError, "recovery"):
                _build(root, recovery_tag="uninstall", recovery_sha="b" * 40)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            with self.assertRaisesRegex(release_contract.ReleaseContractError, "recovery"):
                _build(root, recovery_tag="save-toolkit--v0.9.0", recovery_sha="")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _fixture(root)
            packet = _build(
                root,
                recovery_tag="save-toolkit--v0.9.0",
                recovery_sha="b" * 40,
            )
        self.assertEqual("prior_release", packet["rollback"]["mode"])
        self.assertEqual("save-toolkit--v0.9.0", packet["rollback"]["tag"])
        self.assertEqual("b" * 40, packet["rollback"]["candidate_sha"])


if __name__ == "__main__":
    unittest.main()
