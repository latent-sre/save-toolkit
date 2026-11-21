"""Offline proofs of the shell contracts in agents/reviewer.md.

The uncommitted-work snapshot recipe is extracted from the agent file and run under bash against a
throwaway repository, with `G` and `S` defined as the agent defines them. A second class proves the
agent's `G` prefix keeps working-tree reads from rewriting the source index. No network, no model.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agents" / "reviewer.md"
TIMEOUT = 120
DIGEST = re.compile(r"[0-9a-f]{64}")


def _recipe_and_git_alias() -> tuple[str, str]:
    text = AGENT.read_text(encoding="utf-8")
    blocks = [
        textwrap.dedent(body)
        for body in re.findall(r"^[ \t]*```bash\n(.*?)^[ \t]*```", text, re.S | re.M)
        if "ls-files -z --cached --others" in body
    ]
    assert len(blocks) == 1, f"expected one snapshot block in {AGENT}, found {len(blocks)}"
    alias = re.search(r'`G="(git [^"]+)"`', text)
    assert alias, "the agent no longer defines G"
    return blocks[0], alias.group(1)


def _find_bash() -> str | None:
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    if not git:
        return None
    for parent in Path(git).resolve().parents:
        for relative in ("usr/bin/bash.exe", "bin/bash.exe"):
            candidate = parent / relative
            if candidate.is_file():
                return str(candidate)
    return None


def _posix(path: Path) -> str:
    if os.name != "nt":
        return str(path)
    resolved = path.resolve()
    return f"/{resolved.drive[0].lower()}{resolved.as_posix()[2:]}"


BASH = _find_bash()
RECIPE, G_ALIAS = _recipe_and_git_alias()


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t",
         "-c", "commit.gpgsign=false", *args],
        cwd=repo, capture_output=True, text=True, timeout=TIMEOUT, check=True,
    )
    return done.stdout


@unittest.skipUnless(BASH, "no usable bash (Git's own bash on Windows)")
class SnapshotRecipe(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.has_exec = os.name != "nt"
        self.has_symlink = False
        self._build_repo()

    def _build_repo(self) -> None:
        r = self.repo
        _git(r, "init", "-q")
        _write(r / ".gitignore", b"cache/\n*.log\n")
        _write(r / "edit.txt", b"one\n")
        _write(r / "deleted.txt", b"gone\n")
        _write(r / "becomes_dir", b"was a file\n")
        _write(r / "sp ace.txt", b"space\n")
        _write(r / "-dash.txt", b"dash\n")
        _write(r / "run.sh", b"#!/bin/sh\n")
        _write(r / "sub" / "deep" / "f.txt", b"deep\n")
        if self.has_exec:
            (r / "run.sh").chmod(0o755)
        _git(r, "add", "-A")
        _git(r, "commit", "-qm", "init")
        _write(r / "edit.txt", b"two\n")
        (r / "deleted.txt").unlink()
        (r / "becomes_dir").unlink()
        _write(r / "becomes_dir" / "cache" / "ignored.txt", b"secret\n")
        _write(r / "becomes_dir" / "child.txt", b"child\n")
        _write(r / "root.log", b"ignored\n")
        _write(r / "new" / "nested" / "u.txt", b"nested\n")
        try:
            os.symlink("edit.txt", r / "link")
            self.has_symlink = True
        except (OSError, NotImplementedError):
            pass

    def expected(self) -> set[str]:
        names = {
            ".gitignore", "edit.txt", "sp ace.txt", "-dash.txt", "run.sh", "sub/deep/f.txt",
            "becomes_dir/child.txt", "new/nested/u.txt",
        }
        return names | ({"link"} if self.has_symlink else set())

    def run_recipe(
        self, cwd: Path, scratch: Path, shim: str = ""
    ) -> subprocess.CompletedProcess[str]:
        """Run the recipe; `shim` is sh text wrapped around tar (`$REAL_TAR` is the real one)."""
        script = self.tmp / "recipe.sh"
        script.write_bytes(f'G="{G_ALIAS}"\nS="{_posix(scratch)}"\n{RECIPE}'.encode())
        env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(self.tmp))
        env["MSYS"] = "winsymlinks:nativestrict"
        env["PATH"] = str(Path(BASH).parent) + os.pathsep + env["PATH"]
        if shim:
            real = shutil.which("tar", path=env["PATH"])
            bindir = self.tmp / "shim"
            bindir.mkdir(exist_ok=True)
            (bindir / "tar").write_bytes(f"#!/bin/sh\n{shim}\nexec \"$REAL_TAR\" \"$@\"\n".encode())
            (bindir / "tar").chmod(0o755)
            env.update(REAL_TAR=_posix(Path(real)), COUNT=_posix(self.tmp / "count"))
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
        return subprocess.run(
            [BASH, _posix(script)], cwd=cwd, env=env, capture_output=True, text=True,
            timeout=TIMEOUT,
        )

    def snapshot(self, name: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        scratch = self.tmp / name
        return self.run_recipe(self.repo, scratch), scratch

    @staticmethod
    def entries(scratch: Path) -> set[str]:
        found = set()
        for dirpath, dirs, files in os.walk(scratch):
            for name in dirs + files:
                full = Path(dirpath) / name
                if full.is_symlink() or full.is_file():
                    found.add(full.relative_to(scratch).as_posix())
        return found

    def test_snapshot_holds_exactly_the_eligible_entries(self) -> None:
        before = _git(self.repo, "status", "--porcelain")
        done, scratch = self.snapshot("snap")
        self.assertEqual(0, done.returncode, done.stderr)
        self.assertTrue(DIGEST.fullmatch(done.stdout.splitlines()[-1]), done.stdout)
        self.assertEqual(self.expected(), self.entries(scratch))
        for name in self.expected() - {"link"}:
            self.assertEqual((self.repo / name).read_bytes(), (scratch / name).read_bytes(), name)
        self.assertEqual(b"two\n", (scratch / "edit.txt").read_bytes())
        self.assertFalse((scratch / "deleted.txt").exists())
        self.assertFalse((scratch / "root.log").exists())
        self.assertFalse((scratch / "becomes_dir" / "cache").exists())
        if self.has_exec:
            self.assertTrue(os.access(scratch / "run.sh", os.X_OK))
        if self.has_symlink:
            self.assertTrue((scratch / "link").is_symlink())
            self.assertEqual("edit.txt", os.readlink(scratch / "link"))
        self.assertEqual(before, _git(self.repo, "status", "--porcelain"))

    def test_digest_is_stable_and_tracks_content(self) -> None:
        first, _ = self.snapshot("one")
        second, _ = self.snapshot("two")
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout.splitlines()[-1], second.stdout.splitlines()[-1])
        _write(self.repo / "edit.txt", b"twp\n")
        third, _ = self.snapshot("three")
        self.assertEqual(0, third.returncode, third.stderr)
        self.assertNotEqual(first.stdout.splitlines()[-1], third.stdout.splitlines()[-1])

    def test_passthrough_shim_control(self) -> None:
        done = self.run_recipe(self.repo, self.tmp / "snap", ":")
        self.assertEqual(0, done.returncode, done.stderr)

    def test_failing_source_read_is_not_masked_by_the_pipe(self) -> None:
        shim = 'case "$*" in *-cf*) n=$(($(cat "$COUNT" 2>/dev/null || echo 0)+1))\n' \
               'echo $n > "$COUNT"; [ "$n" = 2 ] && { head -c 1024 /dev/zero; exit 1; };; esac'
        scratch = self.tmp / "snap"
        done = self.run_recipe(self.repo, scratch, shim)
        self.assertNotEqual(0, done.returncode)
        self.assertIsNone(DIGEST.search(done.stdout))

    def test_a_path_added_after_enumeration_fails_closed(self) -> None:
        shim = 'case "$*" in *-cf*) n=$(($(cat "$COUNT" 2>/dev/null || echo 0)+1))\n' \
               'echo $n > "$COUNT"; [ "$n" = 1 ] && echo late > added_later.txt;; esac'
        done = self.run_recipe(self.repo, self.tmp / "snap", shim)
        self.assertTrue((self.repo / "added_later.txt").exists(), "shim never fired")
        self.assertNotEqual(0, done.returncode)
        self.assertIsNone(DIGEST.search(done.stdout))

    def test_a_copy_that_differs_from_the_source_fails_closed(self) -> None:
        scratch = self.tmp / "snap"
        shim = f'case "$*" in *-xpf*) "$REAL_TAR" "$@" || exit; ' \
               f'echo X >> "{_posix(scratch / "edit.txt")}"; exit 0;; esac'
        done = self.run_recipe(self.repo, scratch, shim)
        self.assertNotEqual(0, done.returncode)
        self.assertIsNone(DIGEST.search(done.stdout))

    def test_outside_a_repository_fails_closed(self) -> None:
        plain = self.tmp / "plain"
        plain.mkdir()
        done = self.run_recipe(plain, self.tmp / "snap")
        self.assertNotEqual(0, done.returncode)
        self.assertIsNone(DIGEST.search(done.stdout))

    def test_nothing_to_copy_fails_closed(self) -> None:
        empty = self.tmp / "empty"
        empty.mkdir()
        _git(empty, "init", "-q")
        done = self.run_recipe(empty, self.tmp / "snap")
        self.assertNotEqual(0, done.returncode)
        self.assertIsNone(DIGEST.search(done.stdout))


@unittest.skipUnless(BASH, "no usable bash (Git's own bash on Windows)")
class GitPrefixKeepsIndex(unittest.TestCase):
    """The agent's `$G` must not let a working-tree read rewrite the source index."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name).resolve() / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _write(self.repo / "a.txt", b"one\n")
        _write(self.repo / "b.txt", b"two\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        self.ticks = 0

    def redirty(self) -> None:
        """New mtime, same bytes: the index entry is now stat-dirty."""
        self.ticks += 100
        stamp = 1_700_000_000 + self.ticks
        os.utime(self.repo / "a.txt", (stamp, stamp))

    def index(self) -> bytes:
        return (self.repo / ".git" / "index").read_bytes()

    def bash(self, command: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(self.repo.parent))
        env["PATH"] = str(Path(BASH).parent) + os.pathsep + env["PATH"]
        return subprocess.run(
            [BASH, "-c", f'G="{G_ALIAS}"; {command}'], cwd=self.repo, env=env,
            capture_output=True, text=True, timeout=TIMEOUT,
        )

    def test_reads_leave_the_index_untouched(self) -> None:
        self.redirty()
        before = self.index()
        control = self.bash("git diff")
        self.assertEqual(0, control.returncode, control.stderr)
        if self.index() == before:
            self.skipTest("bare `git diff` does not rewrite the index on this platform")
        for command in (
            "$G status --short",
            "$G diff --no-ext-diff --no-textconv HEAD",
            "$G diff --stat HEAD",
        ):
            with self.subTest(command=command):
                self.redirty()
                before = self.index()
                done = self.bash(command)
                self.assertEqual(0, done.returncode, done.stderr)
                self.assertEqual(before, self.index())


def _export_and_confirm() -> tuple[str, str, str]:
    text = AGENT.read_text(encoding="utf-8")
    spans = re.findall(r"`([^`\n]+)`", text)
    exports = [s for s in spans if "read-tree <sha>" in s and "checkout-index -a --prefix=" in s]
    confirms = [s for s in spans if "diff --quiet <sha>" in s]
    flags = re.search(r"add\s+`([^`]+)`\s+to\s+diffs", text)
    assert len(exports) == 1, f"expected one export command in {AGENT}, found {len(exports)}"
    assert len(confirms) == 1, f"expected one confirm command in {AGENT}, found {len(confirms)}"
    assert flags, f"the diff-flags sentence (add `...` to diffs) is missing from {AGENT}"
    return exports[0], confirms[0], flags.group(1)


EXPORT, CONFIRM, DIFF_FLAGS = _export_and_confirm()


@unittest.skipUnless(BASH, "no usable bash (Git's own bash on Windows)")
class ExportConfirm(unittest.TestCase):
    """The agent's export confirm must hold under the diff flags the agent itself requires."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q")
        _write(self.repo / "a.txt", b"one\n")
        _write(self.repo / "sub" / "b.txt", b"two\n")
        _write(self.repo / "bin.dat", b"\x00\x01\x02binary\x00")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-qm", "init")
        self.sha = _git(self.repo, "rev-parse", "HEAD").strip()

    def bash(self, command: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(self.tmp))
        env["PATH"] = str(Path(BASH).parent) + os.pathsep + env["PATH"]
        script = f'G="{G_ALIAS}"; S="{_posix(self.tmp / "scratch")}"; '
        script += command.replace("<sha>", self.sha)
        return subprocess.run(
            [BASH, "-c", script], cwd=self.repo, env=env, capture_output=True, text=True,
            timeout=TIMEOUT,
        )

    def forms(self) -> dict[str, str]:
        return {
            "as printed": CONFIRM,
            "with the agent's diff flags": CONFIRM.replace(" diff ", f" diff {DIFF_FLAGS} ", 1),
        }

    def test_confirm_accepts_a_faithful_export(self) -> None:
        index = (self.repo / ".git" / "index").read_bytes()
        done = self.bash(EXPORT)
        self.assertEqual(0, done.returncode, done.stderr)
        for name, command in self.forms().items():
            with self.subTest(form=name):
                done = self.bash(command)
                self.assertEqual(0, done.returncode, done.stderr)
        self.assertEqual(index, (self.repo / ".git" / "index").read_bytes())

    def test_confirm_rejects_a_changed_export(self) -> None:
        done = self.bash(EXPORT)
        self.assertEqual(0, done.returncode, done.stderr)
        with (self.tmp / "scratch" / "a.txt").open("ab") as handle:
            handle.write(b"x")
        for name, command in self.forms().items():
            with self.subTest(form=name):
                done = self.bash(command)
                self.assertEqual(1, done.returncode, done.stderr)


if __name__ == "__main__":
    unittest.main()
