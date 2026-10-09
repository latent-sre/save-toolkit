"""No-model tests for identities (evals/probe/fingerprints.py): the runtime a batch records, the
evaluator implementation a scenario digest binds, and the plugin digest.

Run directly: python evals/test_probe_fingerprints.py
"""
from __future__ import annotations

import contextlib
import os
import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from probe import fingerprints as probe_fingerprints
from probe_testkit import run_python

ROOT = Path(__file__).resolve().parent.parent


class RuntimeIdentityTests(unittest.TestCase):
    def test_records_the_executables_version_line_and_the_host_platform(self) -> None:
        identity = probe_fingerprints.runtime_identity(sys.executable)
        self.assertEqual(f"Python {platform.python_version()}", identity["cli_version"])
        self.assertEqual({"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
                         identity["host_platform"])

    def test_a_cli_that_cannot_report_its_version_is_recorded_as_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            identity = probe_fingerprints.runtime_identity(str(Path(tmp) / "no-such-cli"))
        self.assertIsNone(identity["cli_version"])
        self.assertTrue(identity["host_platform"]["system"])

    def test_a_composite_executable_reports_the_version_of_the_command_trials_launch(self) -> None:
        """Copilot and Codex on PR #328: trials launch `"python" "stub.py"` split into argv, but the probe ran
        the whole string as one filename, recorded no version, and so refused a batch it could run."""
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "stub_cli.py"
            stub.write_text("import sys\nprint('9.9.9 (Claude Code)' if sys.argv[1:] == ['--version'] else sys.argv[1:])\n",
                            encoding="utf-8")
            identity = probe_fingerprints.runtime_identity(f'"{sys.executable}" "{stub}"')
            unsplittable = probe_fingerprints.runtime_identity(f'"{sys.executable}" "{stub}')
        self.assertEqual("9.9.9 (Claude Code)", identity["cli_version"])
        self.assertIsNone(unsplittable["cli_version"], "an unclosed quote stays unknown: refused, not a crash")

    def test_a_composite_whose_script_is_relative_is_probed_where_trials_run(self) -> None:
        # A trial runs in its own fresh workspace, where a script named relative to the runner's
        # directory does not exist; a probe that found it there would record a version no trial runs.
        with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp):
            Path("stub_cli.py").write_text("print('9.9.9 (Claude Code)')\n", encoding="utf-8")
            identity = probe_fingerprints.runtime_identity(f'"{sys.executable}" stub_cli.py')
        self.assertIsNone(identity["cli_version"])


class EvaluatorImplementationIdentityTests(unittest.TestCase):
    FILES = ("build_probe.py", *sorted(f"probe/{p.name}" for p in (ROOT / "evals" / "probe").glob("*.py")),
             "graders.py", "judge.py", "clean_room.py", "oracles/incident-closing-fields/probe_closing_fields.py")

    def test_new_process_identity_binds_every_local_evaluator_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "evals"
            folder.mkdir()
            for name in self.FILES:
                (folder / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "evals" / name, folder / name)
            script = "from probe import fingerprints as b; print(b.scenario_digest({'id':'x','prompt':'p','graders':[{'type':'contains_all','of':['x']}]}))"
            def digest():
                result = run_python(["-B", "-c", script], cwd=folder, check=True, timeout=120)
                return result.stdout.strip()
            before = digest()
            replacements = {
                "build_probe.py": ("raise SystemExit(cli.main())", "raise SystemExit(cli.main() or 0)"),
                "probe/checking.py": ("ok = ctx.git.commit_count == ctx.ws.baseline_commits", "ok = True"),
                "probe/outcomes.py": ('EVIDENCE_LIMIT: Final = 600', 'EVIDENCE_LIMIT: Final = 601'),
                "graders.py": ("return (not missing,", "return (False,"),
                "judge.py": ("Distinguish the assistant's own voice", "Ignore the assistant's own voice"),
                "clean_room.py": ("subscriber_only: bool = False", "subscriber_only: bool = True"),
                "oracles/incident-closing-fields/probe_closing_fields.py": (
                    '"board": {"impact"', '"board": {"changed"'),
            }
            for name, (old, new) in replacements.items():
                with self.subTest(module=name):
                    path = folder / name
                    source = path.read_text(encoding="utf-8")
                    self.assertIn(old, source)
                    path.write_text(source.replace(old, new), encoding="utf-8")
                    self.assertNotEqual(before, digest())
                    path.write_text(source, encoding="utf-8")

    def test_disk_edit_after_import_requires_a_new_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for name in self.FILES:
                (Path(tmp) / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / "evals" / name, Path(tmp) / name)
            script = """from probe import fingerprints as b
from pathlib import Path
spec = {'id': 'x', 'prompt': 'p'}
b.scenario_digest(spec)
path = Path('graders.py')
path.write_bytes(path.read_bytes() + b'\\n# edited after import\\n')
try:
    b.scenario_digest(spec)
except RuntimeError as exc:
    print(str(exc))
else:
    raise AssertionError('cached implementation was attributed to changed disk bytes')
"""
            result = run_python(["-B", "-c", script], cwd=tmp, timeout=120)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("new process", result.stdout)


def _directory_link(target: Path, link: Path) -> None:
    """A real directory link: a symlink where the host allows one, else a Windows junction."""
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError:
        if sys.platform != "win32":
            raise
        import _winapi  # noqa: PLC0415 -- Windows only
        _winapi.CreateJunction(str(target), str(link))


class PluginDigestTests(unittest.TestCase):
    """The digest names the committed bytes, not the checkout's line endings."""

    def test_a_linked_optional_input_is_refused_not_read_as_absent(self) -> None:
        """Codex on PR #328: a link at an optional input read as absent, so candidates whose guard script
        is a link to other code shared one digest; a link whose target is gone read as absent too."""
        with tempfile.TemporaryDirectory() as tmp:
            root, elsewhere = self._root(tmp, b"\n"), Path(tmp) / "elsewhere"
            elsewhere.mkdir()
            try:
                _directory_link(elsewhere, root / "scripts" / "guard-session-preflight.py")
            except OSError as exc:
                self.skipTest(f"this host cannot create a directory link: {exc}")
            with self.assertRaisesRegex(RuntimeError, "refusing linked/reparse measured input"):
                probe_fingerprints.plugin_digest(root)
            elsewhere.rmdir()  # the link now dangles
            with self.assertRaisesRegex(RuntimeError, "refusing linked/reparse measured input"):
                probe_fingerprints.plugin_digest(root)

    def test_a_linked_optional_file_is_refused(self) -> None:
        # A file symlink as the digest sees one: creating a real one on Windows needs a privilege a test
        # cannot assume.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp, b"\n")
            hook = root / "scripts" / "readonly-guard-hook.ps1"
            hook.write_bytes(b"Write-Output linked")
            real = probe_fingerprints._is_reparse_point
            with mock.patch.object(probe_fingerprints, "_is_reparse_point", side_effect=lambda path: path == hook or real(path)), \
                    self.assertRaisesRegex(RuntimeError, "refusing linked/reparse measured input"):
                probe_fingerprints.plugin_digest(root)

    def _root(self, tmp: str, newline: bytes) -> Path:
        root = Path(tmp)
        for relative in probe_fingerprints.PLUGIN_INPUT_PATHS:  # every required input must exist
            path = root / relative
            if "." in path.name:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x" + newline)
            else:
                path.mkdir(parents=True, exist_ok=True)
        (root / "agents" / "a.md").write_bytes(b"---" + newline + b"name: a" + newline + b"---" + newline + b"body" + newline)
        return root

    def test_crlf_and_lf_checkouts_of_the_same_source_hash_alike(self) -> None:
        with tempfile.TemporaryDirectory() as lf, tempfile.TemporaryDirectory() as crlf:
            self.assertEqual(probe_fingerprints.plugin_digest(self._root(lf, b"\n")),
                             probe_fingerprints.plugin_digest(self._root(crlf, b"\r\n")))

    def test_a_content_change_still_changes_the_digest(self) -> None:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            ra, rb = self._root(a, b"\n"), self._root(b, b"\n")
            (rb / "agents" / "a.md").write_bytes(b"---\nname: a\n---\nbody changed\n")
            self.assertNotEqual(probe_fingerprints.plugin_digest(ra), probe_fingerprints.plugin_digest(rb))

    def test_stage_plugin_serves_exactly_the_measured_inputs(self) -> None:
        """EVAL-014: a trial served the checkout could read its evals, docs and history. The image it is
        served holds the measured inputs, present optional ones included, and nothing else, and hashes
        as the candidate does."""
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            root = self._root(src, b"\n")
            (root / "evals").mkdir()
            (root / "evals" / "scenario.yaml").write_bytes(b"id: x\n")
            (root / "AGENTS.md").write_bytes(b"# fleet guide\n")
            (root / "scripts" / "readonly-guard-hook.ps1").write_bytes(b"Write-Output guard\n")
            image = probe_fingerprints.stage_plugin(root, Path(dst) / "plugin")
            self.assertEqual(Path(dst) / "plugin", image)
            self.assertEqual(probe_fingerprints.plugin_digest(root), probe_fingerprints.plugin_digest(image))
            served = sorted(p.relative_to(image).as_posix() for p in image.rglob("*") if p.is_file())
            self.assertIn("agents/a.md", served)
            self.assertIn("scripts/readonly-guard-hook.ps1", served)
            self.assertNotIn("evals/scenario.yaml", served)
            self.assertNotIn("AGENTS.md", served)
            self.assertFalse((image / "evals").exists())
            # A copy that does not hash as its source is no image of the candidate.
            with mock.patch.object(probe_fingerprints, "plugin_digest", side_effect=["source", "copy"]), \
                    self.assertRaisesRegex(RuntimeError, "does not match the measured inputs"):
                probe_fingerprints.stage_plugin(root, Path(dst) / "other")


if __name__ == "__main__":
    unittest.main()
