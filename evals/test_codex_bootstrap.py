#!/usr/bin/env python3
"""Contract tests for the isolated Codex evaluator bootstrap."""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


codex_bootstrap = importlib.import_module("codex_bootstrap")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _runtime(cwd: Path) -> object:
    cwd = cwd.resolve(strict=True)
    flags = SimpleNamespace(
        isolated=1,
        no_site=1,
        dont_write_bytecode=1,
        safe_path=True,
    )
    return codex_bootstrap.RuntimeContext(
        flags=flags,
        executable=str(Path(sys.executable).resolve()),
        cwd=cwd,
        sys_path=(str(Path(sysconfig.get_path("stdlib")).resolve()),),
    )


def _write_bundle(
    root: Path,
    files: dict[str, bytes] | None = None,
    *,
    manifest_transform: object | None = None,
) -> tuple[Path, Path, str]:
    root = root.resolve(strict=True)
    source = root / "source"
    source.mkdir()
    content = files or {
        "evals/run_codex_routing.py": b"raise SystemExit(23)\n",
    }
    rows: list[dict[str, object]] = []
    for relative, payload in content.items():
        target = source.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        rows.append(
            {"path": relative, "sha256": _sha256(payload), "size": len(payload)}
        )
    manifest: dict[str, object] = {"schema_version": 1, "files": rows}
    if manifest_transform is not None:
        manifest = manifest_transform(manifest)
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest_path = root / "bundle-manifest.json"
    manifest_path.write_bytes(raw)
    temp_parent = root / "stages"
    temp_parent.mkdir()
    return source, manifest_path, _sha256(raw)


def _run(
    root: Path,
    source: Path,
    manifest: Path,
    digest: str,
    **seams: object,
) -> int:
    root = root.resolve(strict=True)
    return codex_bootstrap.run_bootstrap(
        manifest,
        digest,
        source,
        (),
        runtime=_runtime(root),
        temp_parent=root / "stages",
        **seams,
    )


class BootstrapApiTests(unittest.TestCase):
    def test_isolated_bootstrap_api_exists(self) -> None:
        module = importlib.import_module("codex_bootstrap")

        self.assertTrue(callable(module.run_bootstrap))
        self.assertTrue(callable(module.main))
        self.assertTrue(callable(module.RuntimeContext))

    def test_canary_bundle_requires_the_exact_evaluator_closure(self) -> None:
        complete = tuple(
            codex_bootstrap.BundleEntry(path, "a" * 64, 1)
            for path in sorted(codex_bootstrap.CANARY_BUNDLE_FILES)
        )
        codex_bootstrap._validate_canary_bundle_entries(complete)

        for label, entries in (
            ("missing", complete[:-1]),
            (
                "extra",
                (*complete, codex_bootstrap.BundleEntry("evals/extra.py", "b" * 64, 1)),
            ),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(
                codex_bootstrap.BootstrapError, "exact evaluator closure"
            ):
                codex_bootstrap._validate_canary_bundle_entries(entries)

        repository_root = Path(__file__).resolve().parents[1]
        manifest_path = (
            repository_root / "evals" / "conformance" / "codex-terra-evaluator-v1.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest["files"]
        self.assertEqual(
            codex_bootstrap.CANARY_BUNDLE_FILES,
            frozenset(row["path"] for row in rows),
        )
        for row in rows:
            source = repository_root.joinpath(*row["path"].split("/"))
            content = source.read_bytes()
            self.assertEqual(row["size"], len(content), row["path"])
            self.assertEqual(row["sha256"], _sha256(content), row["path"])

    def test_authoritative_canary_binds_stage_and_trial_to_one_private_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / "source"
            repository = root / "repository"
            stage = root / "stage"
            private_root = root / "private"
            for directory in (source, repository, stage, private_root):
                directory.mkdir()
            codex_bin = root / "codex.exe"
            auth_file = root / "auth.json"
            codex_bin.write_bytes(b"codex")
            auth_file.write_bytes(b"{}")
            staged_manifest = stage / "evals/conformance/codex-terra-routing-v1.json"
            staged_manifest.parent.mkdir(parents=True)
            staged_manifest.write_bytes(b"{}")
            with mock.patch("codex_bootstrap.run_bootstrap", return_value=23) as run:
                exit_code = codex_bootstrap.run_canary_bootstrap(
                    root / "bundle.json",
                    "a" * 64,
                    source,
                    repo_root=repository,
                    codex_bin=codex_bin,
                    auth_file=auth_file,
                    private_root=private_root,
                )

            self.assertEqual(23, exit_code)
            self.assertEqual(private_root, run.call_args.kwargs["temp_parent"])
            built = tuple(run.call_args.kwargs["argument_builder"](stage))
            self.assertEqual(("--private-root", str(private_root)), built[-2:])

    def test_authoritative_preflight_omits_auth_and_synthesizes_fixed_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / "source"
            repository = root / "repository"
            stage = root / "stage"
            private_root = root / "private"
            for directory in (source, repository, stage, private_root):
                directory.mkdir()
            codex_bin = root / "codex.exe"
            codex_bin.write_bytes(b"codex")
            staged_manifest = stage / "evals/conformance/codex-terra-routing-v1.json"
            staged_manifest.parent.mkdir(parents=True)
            staged_manifest.write_bytes(b"{}")

            with mock.patch("codex_bootstrap.run_bootstrap", return_value=23) as run:
                exit_code = codex_bootstrap.run_preflight_bootstrap(
                    root / "bundle.json",
                    "a" * 64,
                    source,
                    repo_root=repository,
                    codex_bin=codex_bin,
                    private_root=private_root,
                )

            self.assertEqual(23, exit_code)
            built = tuple(run.call_args.kwargs["argument_builder"](stage))
            self.assertEqual("--preflight", built[0])
            self.assertNotIn("--auth-file", built)
            self.assertEqual(("--private-root", str(private_root)), built[-2:])


class WindowsPrivateRootLocalityTests(unittest.TestCase):
    @staticmethod
    def _facts(
        *,
        drive_type: int = 3,
        filesystem: str = "NTFS",
        dos_device: str = r"\Device\HarddiskVolume3",
    ) -> object:
        return SimpleNamespace(
            drive_type=drive_type,
            filesystem=filesystem,
            dos_device=dos_device,
            volume_root="C:\\",
        )

    def test_windows_local_fixed_ntfs_volume_is_accepted(self) -> None:
        probe = mock.Mock(return_value=self._facts())

        codex_bootstrap._validate_windows_private_root_locality(
            r"C:\private", volume_probe=probe
        )

        probe.assert_called_once_with(r"C:\private", "C:")

    def test_windows_unc_is_rejected_before_volume_queries(self) -> None:
        probe = mock.Mock(side_effect=AssertionError("UNC must fail before Win32 probing"))

        with self.assertRaisesRegex(codex_bootstrap.BootstrapError, "local fixed drive"):
            codex_bootstrap._validate_windows_private_root_locality(
                r"\\server\share\private", volume_probe=probe
            )

        probe.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows ACL ownership is host-specific")
    def test_private_directory_setter_assigns_the_current_owner_and_exact_dacl(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            target = root / "private"
            target.mkdir()

            codex_bootstrap._set_windows_private_directory(target)

            actual = codex_bootstrap._windows_directory_sddl(target)
            expected = codex_bootstrap._windows_private_directory_sddl()
            self.assertIn(actual, {expected, expected.replace("D:P(", "D:PAI(", 1)})

    def test_windows_remote_removable_subst_mapped_and_non_ntfs_are_rejected(self) -> None:
        cases = {
            "remote": (self._facts(drive_type=4), "local fixed storage"),
            "removable": (self._facts(drive_type=2), "local fixed storage"),
            "subst": (
                self._facts(dos_device=r"\??\C:\operator\private"),
                "substituted or mapped",
            ),
            "mapped": (
                self._facts(dos_device=r"\Device\LanmanRedirector\server\share"),
                "substituted or mapped",
            ),
            "non-ntfs": (self._facts(filesystem="ReFS"), "must use NTFS"),
        }
        for label, (facts, message) in cases.items():
            with self.subTest(label=label), self.assertRaisesRegex(
                codex_bootstrap.BootstrapError, message
            ):
                codex_bootstrap._validate_windows_private_root_locality(
                    r"C:\private", volume_probe=lambda *_args, value=facts: value
                )

    def test_bootstrap_validates_the_authoritative_parent_before_staging(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            private_root = (root / "stages").resolve()
            with mock.patch.object(
                codex_bootstrap,
                "_validate_private_root_locality",
                side_effect=codex_bootstrap.BootstrapError("not local fixed storage"),
                create=True,
            ) as validate:
                exit_code = _run(root, source, manifest, digest)

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)
        validate.assert_called_once_with(private_root)

    @unittest.skipUnless(os.name == "nt", "Windows volume APIs are host-specific")
    def test_current_windows_host_temp_root_is_local_fixed_ntfs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            codex_bootstrap._validate_private_root_locality(Path(raw).resolve())


class ManifestContractTests(unittest.TestCase):
    def test_exact_digest_bound_manifest_executes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)

            exit_code = _run(root, source, manifest, digest)

        self.assertEqual(23, exit_code)

    def test_manifest_digest_mismatch_and_read_drift_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            self.assertEqual(
                codex_bootstrap.CONTRACT_FAILURE_EXIT,
                _run(root, source, manifest, "0" * 64),
            )

            def mutate_manifest(_path: Path) -> None:
                manifest.write_bytes(manifest.read_bytes() + b" ")

            self.assertEqual(
                codex_bootstrap.CONTRACT_FAILURE_EXIT,
                _run(
                    root,
                    source,
                    manifest,
                    digest,
                    after_manifest_read=mutate_manifest,
                ),
            )

    def test_manifest_is_strict_utf8_json_without_duplicates_or_nan(self) -> None:
        invalid_documents = (
            b'{"schema_version":1,"schema_version":1,"files":[]}',
            b'{"schema_version":1,"files":[],"value":NaN}',
            b"\xff",
        )
        for raw_manifest in invalid_documents:
            with self.subTest(raw_manifest=raw_manifest[:1]), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, _digest = _write_bundle(root)
                manifest.write_bytes(raw_manifest)

                exit_code = _run(root, source, manifest, _sha256(raw_manifest))

                self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_schema_rejects_empty_duplicate_and_unknown_logical_entries(self) -> None:
        def empty(data: dict[str, object]) -> dict[str, object]:
            data["files"] = []
            return data

        def duplicate(data: dict[str, object]) -> dict[str, object]:
            data["files"] = [*data["files"], data["files"][0]]
            return data

        def top_extra(data: dict[str, object]) -> dict[str, object]:
            data["unexpected"] = True
            return data

        def row_extra(data: dict[str, object]) -> dict[str, object]:
            data["files"][0]["unexpected"] = True
            return data

        for label, transform in {
            "empty": empty,
            "duplicate": duplicate,
            "top-extra": top_extra,
            "row-extra": row_extra,
        }.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(
                    root, manifest_transform=transform
                )

                self.assertEqual(
                    codex_bootstrap.CONTRACT_FAILURE_EXIT,
                    _run(root, source, manifest, digest),
                )

    def test_paths_reject_absolute_traversal_backslash_control_and_reserved_names(self) -> None:
        malicious_paths = (
            "/outside.py",
            "C:/outside.py",
            "evals/../outside.py",
            r"evals\outside.py",
            "evals/bad\x07name.py",
            "evals/CON.py",
        )
        for relative in malicious_paths:
            def transform(data: dict[str, object], path: str = relative) -> dict[str, object]:
                data["files"][0]["path"] = path
                return data

            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(
                    root, manifest_transform=transform
                )

                self.assertEqual(
                    codex_bootstrap.CONTRACT_FAILURE_EXIT,
                    _run(root, source, manifest, digest),
                )

    def test_casefold_colliding_paths_are_rejected(self) -> None:
        files = {
            "evals/run_codex_routing.py": b"raise SystemExit(23)\n",
            "evals/Helper.py": b"VALUE = 1\n",
            "evals/helper.py": b"VALUE = 2\n",
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root, files)

            exit_code = _run(root, source, manifest, digest)

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)


class SourceAndStageBoundaryTests(unittest.TestCase):
    def test_manifest_and_source_root_reject_link_indirection(self) -> None:
        for target_name in ("manifest", "source"):
            with self.subTest(target_name=target_name), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(root)
                if target_name == "manifest":
                    real = root / "real-manifest.json"
                    manifest.rename(real)
                    try:
                        manifest.symlink_to(real)
                    except OSError as exc:
                        self.skipTest(f"file symlinks unavailable: {exc}")
                else:
                    real = root / "real-source"
                    source.rename(real)
                    try:
                        source.symlink_to(real, target_is_directory=True)
                    except OSError as exc:
                        self.skipTest(f"directory symlinks unavailable: {exc}")

                self.assertEqual(
                    codex_bootstrap.CONTRACT_FAILURE_EXIT,
                    _run(root, source, manifest, digest),
                )

    def test_reparse_signal_on_source_component_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            indirect = (source / "evals").resolve()
            original = codex_bootstrap._is_link_or_reparse

            def is_indirect(path: Path) -> bool:
                return path.resolve() == indirect or original(path)

            with mock.patch.object(
                codex_bootstrap, "_is_link_or_reparse", side_effect=is_indirect
            ):
                exit_code = _run(root, source, manifest, digest)

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_reparse_signal_on_manifest_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            original = codex_bootstrap._is_link_or_reparse

            def is_indirect(path: Path) -> bool:
                return path == manifest or original(path)

            with mock.patch.object(
                codex_bootstrap, "_is_link_or_reparse", side_effect=is_indirect
            ):
                exit_code = _run(root, source, manifest, digest)

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_source_hardlink_special_missing_and_oversized_files_are_rejected(self) -> None:
        for label in ("hardlink", "special", "missing", "oversized"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(root)
                entrypoint = source / "evals/run_codex_routing.py"
                limit = codex_bootstrap.MAX_FILE_BYTES
                if label == "hardlink":
                    os.link(entrypoint, root / "hardlink-peer.py")
                elif label == "special":
                    entrypoint.unlink()
                    entrypoint.mkdir()
                elif label == "missing":
                    entrypoint.unlink()
                else:
                    limit = entrypoint.stat().st_size - 1

                with mock.patch.object(codex_bootstrap, "MAX_FILE_BYTES", limit):
                    exit_code = _run(root, source, manifest, digest)

                self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_source_change_after_copy_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)

            def mutate_source(_relative: str, path: Path) -> None:
                path.write_bytes(b"raise SystemExit(24)\n")

            exit_code = _run(
                root,
                source,
                manifest,
                digest,
                after_source_read=mutate_source,
            )

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_staged_change_and_unexpected_extra_are_detected_before_execution(self) -> None:
        for label in ("drift", "extra"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(root)

                def mutate_stage(stage: Path) -> None:
                    if label == "drift":
                        (stage / "evals/run_codex_routing.py").write_bytes(
                            b"raise SystemExit(24)\n"
                        )
                    else:
                        (stage / "evals/unexpected.py").write_bytes(b"pass\n")

                exit_code = _run(
                    root,
                    source,
                    manifest,
                    digest,
                    before_stage_verify=mutate_stage,
                )

                self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_post_execution_stage_drift_overrides_tentative_success(self) -> None:
        entrypoint = b"""\
from pathlib import Path
Path(__file__).with_name('runtime-extra.py').write_text('pass\\n', encoding='utf-8')
raise SystemExit(23)
"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(
                root, {"evals/run_codex_routing.py": entrypoint}
            )

            exit_code = _run(root, source, manifest, digest)

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_successful_run_removes_the_random_stage(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)

            self.assertEqual(23, _run(root, source, manifest, digest))

            self.assertEqual([], list((root / "stages").iterdir()))

    def test_misdirected_fresh_stage_is_removed_before_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            misdirected = source / "unexpected-stage"

            def create_under_source(*_args: object, **_kwargs: object) -> str:
                misdirected.mkdir()
                return str(misdirected)

            with mock.patch.object(
                codex_bootstrap.tempfile, "mkdtemp", side_effect=create_under_source
            ):
                exit_code = codex_bootstrap.run_bootstrap(
                    manifest,
                    digest,
                    source,
                    (),
                    runtime=_runtime(root),
                )

            self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)
            self.assertFalse(misdirected.exists())


class RuntimeAndExecutionTests(unittest.TestCase):
    def test_exact_stdlib_zip_path_is_trusted_but_unexpected_sibling_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            prefix = root / "runtime"
            stdlib = prefix / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}"
            source = root / "source"
            stdlib.mkdir(parents=True)
            source.mkdir()
            zip_name = f"python{sys.version_info.major}{sys.version_info.minor}.zip"
            expected_zip = stdlib.parent / zip_name
            unexpected_zip = stdlib.parent / "python999.zip"

            def runtime_path(name: str) -> str:
                if name in {"stdlib", "platstdlib"}:
                    return str(stdlib)
                raise AssertionError(f"unexpected sysconfig path: {name}")

            with (
                mock.patch.object(codex_bootstrap.sys, "base_prefix", str(prefix)),
                mock.patch.object(codex_bootstrap.sys, "exec_prefix", str(prefix)),
                mock.patch.object(
                    codex_bootstrap.sysconfig, "get_path", side_effect=runtime_path
                ),
            ):
                self.assertEqual(
                    (str(expected_zip),),
                    codex_bootstrap._trusted_runtime_paths(
                        (str(expected_zip),), source
                    ),
                )
                with self.assertRaisesRegex(
                    codex_bootstrap.BootstrapError,
                    "outside the standard library",
                ):
                    codex_bootstrap._trusted_runtime_paths(
                        (str(unexpected_zip),), source
                    )

    def test_private_parent_must_start_empty_before_any_stage_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            private_parent = root / "stages"
            (private_parent / "preexisting.txt").write_text("unexpected", encoding="utf-8")

            exit_code = codex_bootstrap.run_bootstrap(
                manifest,
                digest,
                source,
                (),
                runtime=_runtime(root),
                temp_parent=private_parent,
            )

            self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)
            self.assertEqual(["preexisting.txt"], [item.name for item in private_parent.iterdir()])

    def test_all_isolation_flags_are_mandatory_through_runtime_seam(self) -> None:
        for field, value in {
            "isolated": 0,
            "no_site": 0,
            "dont_write_bytecode": 0,
            "safe_path": False,
        }.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(root)
                flags = SimpleNamespace(
                    isolated=1,
                    no_site=1,
                    dont_write_bytecode=1,
                    safe_path=True,
                )
                setattr(flags, field, value)
                runtime = codex_bootstrap.RuntimeContext(
                    flags=flags,
                    executable=str(Path(sys.executable).resolve()),
                    cwd=root,
                    sys_path=(str(Path(sysconfig.get_path("stdlib")).resolve()),),
                )

                exit_code = codex_bootstrap.run_bootstrap(
                    manifest,
                    digest,
                    source,
                    (),
                    runtime=runtime,
                    temp_parent=root / "stages",
                )

                self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_python_executable_cwd_stage_and_stdlib_path_must_be_safe(self) -> None:
        labels = (
            "relative-python",
            "cwd-under-source",
            "stage-under-source",
            "source-sys-path",
        )
        for label in labels:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(root)
                runtime = _runtime(root)
                temp_parent = root / "stages"
                if label == "relative-python":
                    runtime = codex_bootstrap.RuntimeContext(
                        runtime.flags, "python", runtime.cwd, runtime.sys_path
                    )
                elif label == "cwd-under-source":
                    runtime = codex_bootstrap.RuntimeContext(
                        runtime.flags, runtime.executable, source, runtime.sys_path
                    )
                elif label == "stage-under-source":
                    temp_parent = source / "temporary"
                    temp_parent.mkdir()
                else:
                    runtime = codex_bootstrap.RuntimeContext(
                        runtime.flags,
                        runtime.executable,
                        runtime.cwd,
                        (str(source / "evals"),),
                    )

                exit_code = codex_bootstrap.run_bootstrap(
                    manifest,
                    digest,
                    source,
                    (),
                    runtime=runtime,
                    temp_parent=temp_parent,
                )

                self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)

    def test_staged_evals_is_appended_after_stdlib_and_cannot_shadow_json(self) -> None:
        entrypoint = b"""\
import json
import pathlib
import sys
if sys.path[-1] != str(pathlib.Path(__file__).resolve().parent):
    raise SystemExit(91)
if getattr(json, 'STAGED_SENTINEL', False):
    raise SystemExit(92)
raise SystemExit(31)
"""
        files = {
            "evals/run_codex_routing.py": entrypoint,
            "evals/json.py": b"STAGED_SENTINEL = True\n",
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root, files)

            exit_code = _run(root, source, manifest, digest)

        self.assertEqual(31, exit_code)

    def test_forwarded_arguments_exit_code_and_python_environment_are_controlled(self) -> None:
        entrypoint = b"""\
import os
import pathlib
import sys
if pathlib.Path(sys.argv[0]).name != 'run_codex_routing.py':
    raise SystemExit(91)
if any(key.upper().startswith('PYTHON') for key in os.environ):
    raise SystemExit(92)
raise SystemExit(int(sys.argv[1]))
"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(
                root, {"evals/run_codex_routing.py": entrypoint}
            )
            with mock.patch.dict(os.environ, {"PYTHON_PRIVATE_VALUE": "must-disappear"}):
                exit_code = codex_bootstrap.run_bootstrap(
                    manifest,
                    digest,
                    source,
                    ("37",),
                    runtime=_runtime(root),
                    temp_parent=root / "stages",
                )

        self.assertEqual(37, exit_code)

    def test_cleanup_failure_overrides_success_without_printing_a_path(self) -> None:
        for label in ("raises", "silently-leaves-stage"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                source, manifest, digest = _write_bundle(root)
                residual: list[Path] = []
                warning = io.StringIO()

                def fail_cleanup(path: Path) -> None:
                    residual.append(path)
                    if label == "raises":
                        raise RuntimeError("locked")

                with contextlib.redirect_stderr(warning):
                    exit_code = _run(
                        root,
                        source,
                        manifest,
                        digest,
                        cleanup=fail_cleanup,
                    )

                self.assertEqual(codex_bootstrap.CLEANUP_FAILURE_EXIT, exit_code)
                self.assertEqual(1, len(residual))
                self.assertIn("manual cleanup required", warning.getvalue())
                self.assertNotIn(str(root), warning.getvalue())
                shutil.rmtree(residual[0])

    def test_rejection_diagnostic_never_echoes_manifest_or_source_values(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source, manifest, digest = _write_bundle(root)
            unique_identifier = "private-identifier-7119"
            manifest.write_text(unique_identifier, encoding="utf-8")
            stderr = io.StringIO()

            with contextlib.redirect_stderr(stderr):
                exit_code = _run(root, source, manifest, digest)

            self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)
            self.assertNotIn(unique_identifier, stderr.getvalue())
            self.assertNotIn(str(source), stderr.getvalue())
            self.assertNotIn(str(manifest), stderr.getvalue())

    def test_real_cli_requires_isolation_and_synthesizes_only_fixed_canary_args(self) -> None:
        entrypoint = b"""\
import pathlib
import sys
args = sys.argv[1:]
if len(args) != 11:
    raise SystemExit(91)
if args[0:2] != ['--canary', '--manifest']:
    raise SystemExit(92)
if pathlib.Path(args[2]).name != 'codex-terra-routing-v1.json':
    raise SystemExit(93)
if args[3] != '--repo-root' or not pathlib.Path(args[4]).is_dir():
    raise SystemExit(94)
if args[5] != '--codex-bin' or not pathlib.Path(args[6]).is_file():
    raise SystemExit(95)
if args[7] != '--auth-file' or not pathlib.Path(args[8]).is_file():
    raise SystemExit(96)
if args[9] != '--private-root' or not pathlib.Path(args[10]).is_dir():
    raise SystemExit(97)
raise SystemExit(23)
"""
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            files = {path: b"# test bundle member\n" for path in codex_bootstrap.CANARY_BUNDLE_FILES}
            files["evals/run_codex_routing.py"] = entrypoint
            files["evals/conformance/codex-terra-routing-v1.json"] = b"{}\n"
            source, manifest, digest = _write_bundle(root, files)
            repository = root / "repository"
            repository.mkdir()
            codex_bin = root / "codex.exe"
            codex_bin.write_bytes(b"test executable")
            auth_file = root / "auth.json"
            auth_file.write_bytes(b"{}\n")
            private_root = root / "private"
            private_root.mkdir()
            command = (
                str(Path(sys.executable).resolve()),
                "-I",
                "-S",
                "-B",
                str(Path(codex_bootstrap.__file__).resolve()),
                "--bundle-manifest",
                str(manifest.resolve()),
                "--expected-manifest-sha256",
                digest,
                "--source-root",
                str(source.resolve()),
                "--repo-root",
                str(repository.resolve()),
                "--codex-bin",
                str(codex_bin.resolve()),
                "--auth-file",
                str(auth_file.resolve()),
                "--private-root",
                str(private_root.resolve()),
            )

            result = subprocess.run(
                command,
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )

        self.assertEqual(23, result.returncode, result.stderr.decode("utf-8", "replace"))
        self.assertEqual(b"", result.stdout)

    def test_cli_rejects_caller_supplied_evaluator_overrides(self) -> None:
        with mock.patch("codex_bootstrap.run_canary_bootstrap") as run_canary:
            exit_code = codex_bootstrap.main(
                [
                    "--bundle-manifest",
                    "C:/manifest.json",
                    "--expected-manifest-sha256",
                    "a" * 64,
                    "--source-root",
                    "C:/source",
                    "--repo-root",
                    "C:/repo",
                    "--codex-bin",
                    "C:/codex.exe",
                    "--auth-file",
                    "C:/auth.json",
                    "--private-root",
                    "C:/private",
                    "--",
                    "--plan",
                ]
            )

        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)
        run_canary.assert_not_called()

    def test_cli_dispatches_preflight_without_accepting_auth(self) -> None:
        arguments = [
            "--bundle-manifest",
            "C:/manifest.json",
            "--expected-manifest-sha256",
            "a" * 64,
            "--source-root",
            "C:/source",
            "--repo-root",
            "C:/repo",
            "--codex-bin",
            "C:/codex.exe",
            "--private-root",
            "C:/private",
            "--preflight",
        ]
        with mock.patch(
            "codex_bootstrap.run_preflight_bootstrap", return_value=23
        ) as preflight:
            self.assertEqual(23, codex_bootstrap.main(arguments))
        preflight.assert_called_once()

        with mock.patch("codex_bootstrap.run_preflight_bootstrap") as preflight:
            exit_code = codex_bootstrap.main(
                [*arguments, "--auth-file", "C:/auth.json"]
            )
        self.assertEqual(codex_bootstrap.CONTRACT_FAILURE_EXIT, exit_code)
        preflight.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
