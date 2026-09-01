#!/usr/bin/env python3
"""Check one named module for a contract mutation its focused tests fail to notice.

WHY THIS EXISTS
---------------
A green suite is a claim about the *instrument*, not the code. This repository has now shipped two
tests that passed while asserting nothing about the contract they were written for: one matched a
string a refactor had moved, and one asserted the opposite of the sentence in its own comment —
mutating the gate it named so it failed every clean run left all sixteen tests green.

No static check finds that. Both tests had real assertions on real output; what they lacked was any
assertion that *changed answer* when the contract changed. The only detector for a detector is to
break the code on purpose and require someone to notice.

WHAT IT DOES
------------
For one module supplied with `--module`, it derives the test file(s) that exercise that module,
rewrites one small piece of its logic, and runs those tests. A mutant that **survives** — the suite
still passes after the change — is a diagnostic lead, not a defect or backlog item. Turn at most one
named survivor into a focused red-first regression, prove that regression kills it, then stop. The
CLI stops executing mutants as soon as it finds that first survivor; it does not finish an inventory
and hide the extra results afterward.

The CLI deliberately refuses an omitted `--module`. Fleet-wide sweeps and survivor inventories cost
time without establishing a contract; this helper exists only for a bounded question about one file.

SUBJECTS ARE DERIVED, NEVER HAND-KEPT
-------------------------------------
`discover` reads each `scripts/test_*.py` for the `.py` paths it names and the sibling `X.py` it
implies, so a new test file enrols its own subject with no edit here. That is deliberate: this
repository has already shipped a test file that was wired into nothing because a hand-kept roster
forgot it.

HONEST LIMITS
-------------
**Your working tree is never modified.** Every run uses a throwaway `git worktree` at HEAD
(`isolated_checkout`), so the mutated bytes only ever exist in a temporary directory that is deleted
afterwards and reclaimed by `git worktree prune` if a run is killed outright.

That is stronger than the earlier in-place-plus-`finally` design, which protected the person running
the sweep and nobody else: for the duration of a run the real tree flipped between correct and
deliberately broken many times a second, and any observer sampling that window saw corruption. A
stop hook advising "you have uncommitted changes, please commit" is the obvious case, and it has
already happened here -- see `_restore_on_termination` -- but a watch-mode runner, an editor
autosave, or a second agent on the same checkout are the same hazard. Isolation removes the class;
the in-mutant `finally` and the SIGTERM handler remain as cheap belt-and-braces inside the sandbox.

It still refuses to start on a dirty working tree, now for honesty rather than recovery: a worktree
is pinned at HEAD, so with uncommitted changes present the run would report on code that is not the
code in front of you. It is a deliberate single-module diagnostic, never a CI or per-push gate.

`--limit` makes it a sampling tool rather than a proof. A clean bounded report means "no survivor
among the mutants tried"; it never means "the suite is complete", and it never establishes that any
particular mutant was among those tried. The default walks the complete generated population only
when every mutant is killed. Any survivor stops the run immediately, and the CLI never infers from
survivors that a test probably does not exercise its subject.

Pure standard library.

    python scripts/mutation_guard.py --module scripts/validate_fleet.py
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]
TEST_GLOBS = ("scripts/test_*.py", "evals/test_*.py")
# Small and high-signal. Each operator changes behaviour that a contract-pinning test must notice.
COMPARISON_SWAPS = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}
# Unbounded by default: this is a deliberate command, not a gate step, so completeness beats
# speed. --limit takes an evenly spaced sample when a bounded run is wanted.
DEFAULT_LIMIT = 0
RUN_TIMEOUT = 900
# Characters that turn a basename into a pattern. `Path.glob` treats these as wildcards, so a
# `.py` literal containing one must never reach the bundle search in `discover`.
_GLOB_METACHARACTERS = frozenset("*?[]")
# Distinct codes: a collapsed exit status cannot tell "refused to run" from "ran and proved
# nothing", which is the same disarmed-gate shape this repo forbids for the readonly guard.
EXIT_SURVIVORS = 1
EXIT_REFUSED = 2
EXIT_INCONCLUSIVE = 3
# argparse exits 2 for every usage error, which is EXIT_REFUSED's value. Left alone, a rejected
# flag is indistinguishable from a refusal to run over a dirty tree -- the same collapse.
EXIT_USAGE = 4


@dataclass(frozen=True)
class Mutant:
    lineno: int
    description: str
    mutated_source: str


@dataclass(frozen=True)
class Subject:
    """A module a test exercises, and how that link was established.

    Provenance is retained for discovery diagnostics: a `sibling` subject follows the repository's
    `test_x.py` -> `x.py` convention, while a `literal` subject comes from a `.py` string in the
    test's source and may only be a fixture path. The CLI reports one observed survivor and makes no
    inference from aggregate survival about whether either kind of subject was exercised.
    """

    path: Path
    origin: str  # "sibling" | "literal"


def _render(tree: ast.AST) -> str:
    return ast.unparse(tree) + "\n"


def _mutation_sites(tree: ast.Module) -> Iterator[tuple[ast.AST, str, object]]:
    """Yield (node, description, replacement) for every supported single-point change."""

    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp) and len(node.values) > 1:
            # Dropping an operand is the mutation that exposed the real bug: a gate written as
            # `findings and opted_in` still reads as a gate after it becomes just `opted_in`.
            for index in range(len(node.values)):
                kept = [value for position, value in enumerate(node.values) if position != index]
                replacement = kept[0] if len(kept) == 1 else ast.BoolOp(op=node.op, values=kept)
                yield node, f"drop operand {index} of {type(node.op).__name__}", replacement
        elif isinstance(node, ast.Compare) and len(node.ops) == 1:
            swap = COMPARISON_SWAPS.get(type(node.ops[0]))
            if swap is not None:
                yield node, f"{type(node.ops[0]).__name__} -> {swap.__name__}", swap()
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            yield node, "drop not", node.operand
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            yield node, f"{node.value} -> {not node.value}", ast.Constant(value=not node.value)


def mutants(source: str, limit: int = 0) -> list[Mutant]:
    """Every single-point mutant of *source*, deterministic and deduplicated.

    A non-zero *limit* takes an evenly spaced sample across the whole walk, never a prefix.
    Prefix truncation only ever mutates the shallowest sites and can silently exclude a named
    contract farther down the file. Even spacing closes that bias without making a bounded run
    complete. An evenly spaced sample can still miss any given mutant: it guarantees only that the
    sample *spans* the file, not that it *contains* anything in particular. Only an unbounded
    selection contains every generated mutant; the CLI still stops executing as soon as one
    survives.
    """

    original = ast.parse(source)
    seen: set[str] = set()
    produced: list[Mutant] = []
    for index in range(len(list(_mutation_sites(original)))):
        tree = ast.parse(source)
        sites = list(_mutation_sites(tree))
        node, description, replacement = sites[index]
        lineno = getattr(node, "lineno", 0)
        if isinstance(node, ast.Compare):
            node.ops = [replacement]  # type: ignore[list-item]
            rendered = _render(tree)
        else:
            rendered = _render(_replace_node(tree, node, replacement))
        if rendered in seen or rendered == _render(ast.parse(source)):
            continue
        seen.add(rendered)
        produced.append(Mutant(lineno=lineno, description=description, mutated_source=rendered))
    if not limit or limit >= len(produced):
        return produced
    # Evenly spaced indices, always including the last site.
    step = (len(produced) - 1) / (limit - 1) if limit > 1 else len(produced) - 1
    chosen = sorted({round(position * step) for position in range(limit)})
    return [produced[index] for index in chosen]


def _replace_node(tree: ast.Module, target: ast.AST, replacement: object) -> ast.Module:
    class Swap(ast.NodeTransformer):
        def generic_visit(self, node: ast.AST) -> ast.AST:
            if node is target:
                return ast.copy_location(copy.deepcopy(replacement), node)  # type: ignore[arg-type]
            return super().generic_visit(node)

    return ast.fix_missing_locations(Swap().visit(tree))


def discover(root: Path) -> list[tuple[Path, list[Path]]]:
    """Map each test file to the module(s) it exercises, derived from the test's own source.

    A test file is never itself a subject: mutating a test proves nothing about the code. Files
    that resolve to no subject are still returned, with an empty list, so `unresolved` can report
    them — silently dropping them is how this repository once shipped a test that ran nowhere.
    """

    pairs: list[tuple[Path, list[Subject]]] = []
    for pattern in TEST_GLOBS:
        for test in sorted(root.glob(pattern)):
            subjects: list[Subject] = []
            seen: set[Path] = set()
            stem = test.name[len("test_") :]
            # Try the hyphenated spelling too: scripts/readonly-guard.py is a real module whose
            # test is test_readonly_guard.py, and the underscore-only convention missed it.
            for candidate in (
                test.with_name(stem),
                test.with_name(stem.replace("_", "-")),
            ):
                if candidate.is_file() and candidate not in seen:
                    subjects.append(Subject(path=candidate, origin="sibling"))
                    seen.add(candidate)
            try:
                tree = ast.parse(test.read_text(encoding="utf-8"))
            except (OSError, SyntaxError):
                tree = ast.parse("")
            # What the test IMPORTS is the strongest available statement of what it exercises, and
            # it was the one signal this function ignored. The cost was concrete:
            # generate_platform_adapters.py -- 735 lines, the single generator behind every host
            # projection -- had NO mutation coverage at all behind a 429-line test file, because
            # `import generate_platform_adapters as adapters` contains no `.py` literal and the
            # sibling name does not match. A sibling-name mismatch of the same shape (a test file
            # whose stem does not match its subject's) missed for the same reason. Import-following
            # fixes both without renaming any file, which matters because a rename would break the
            # references those names already have.
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module] if node.module and node.level == 0 else []
                else:
                    continue
                for name in names:
                    # Top-level package component only: `scripts.foo` and `foo` both resolve
                    # against the same tree, and a dotted stdlib name simply matches no file.
                    base = name.split(".")[0]
                    # A skill can ship its own scripts, and its test reaches them by inserting the
                    # bundle directory on sys.path rather than by any path literal this function
                    # could see (test_confluence_import.py -> confluence_to_runbook.py). Those are
                    # first-class subjects; sorted() keeps the search deterministic.
                    for candidate in [root / "scripts" / f"{base}.py"] + sorted(
                        root.glob(f"skills/*/scripts/{base}.py")
                    ):
                        candidate = candidate.resolve()
                        if (
                            candidate.is_file()
                            and candidate not in seen
                            and not candidate.name.startswith("test_")
                        ):
                            subjects.append(Subject(path=candidate, origin="import"))
                            seen.add(candidate)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if not node.value.endswith(".py"):
                    continue
                options = [root / node.value]
                # A bare basename only, and never one carrying glob metacharacters. `"*.py"` is a
                # perfectly ordinary literal in a test — `test_platform_adapters.py` has two — and
                # interpolating it into the glob below enrolled every skill-bundled script as a
                # subject of that test: bundled modules it makes no claim about. Those bogus pairs
                # then fail their own normalized baseline and the diagnostic reports unverifiable
                # pairs instead of testing the real module.
                if (
                    "/" not in node.value
                    and "\\" not in node.value
                    and not _GLOB_METACHARACTERS.intersection(node.value)
                ):
                    # A BARE basename, which is what a path-joined subject looks like to the AST:
                    # `ROOT / "skills" / "runbook" / "scripts" / "confluence_to_runbook.py"` offers
                    # no single literal holding the whole path, only its last component. Resolving
                    # that against root alone finds nothing, which is why a 500-line converter with
                    # a dedicated test file scored as having no subject. Searching the two places
                    # this repository keeps runnable modules is bounded and deterministic.
                    options += [root / "scripts" / node.value] + sorted(
                        root.glob(f"skills/*/scripts/{node.value}")
                    )
                for option in options:
                    candidate = option.resolve()
                    if (
                        candidate.is_file()
                        and candidate not in seen
                        and not candidate.name.startswith("test_")
                    ):
                        subjects.append(Subject(path=candidate, origin="literal"))
                        seen.add(candidate)
            pairs.append((test, subjects))
    return pairs


def unresolved(root: Path) -> list[Path]:
    """Test files this guard cannot mutate anything for — reported, never silently skipped."""

    return [test for test, subjects in discover(root) if not subjects]


class UnverifiablePair(RuntimeError):
    """The test does not pass against unmutated code, so no mutant result means anything.

    Without this the tool has the very defect it exists to find: a suite failing for a reason
    unrelated to any mutation — a missing dependency, the wrong working directory, an import
    error — scores every mutant as killed and reports PASS while proving nothing.
    """


def normalized_source(source: str) -> str:
    """The unparse round-trip of *source*, which is what every mutant is compared against."""

    return _render(ast.parse(source))


def run_test(test: Path) -> bool:
    """True when the test file passes. Run from the root of the tree the test BELONGS to.

    The working directory is derived from the test's own path (`<root>/scripts/test_x.py` and
    `<root>/evals/test_x.py` both put the root two levels up) rather than from the module-level
    ROOT constant. That distinction became load-bearing with worktree isolation: ROOT is the
    caller's real checkout, so a mutated test inside the throwaway worktree was being launched with
    the LIVE repository as its working directory. Any test resolving a repository file relative to
    cwd would then read unmutated bytes, and the pair gets scored against the wrong tree.

    Deriving it from `test` also cannot go stale the way a threaded-through parameter can: there is
    no second value to keep in sync, and no default that is silently wrong.

    `-B` is load-bearing: CPython validates a cached `.pyc` on `(int(mtime), size)`, and an `==`
    to `!=` swap leaves the file the same size, so two mutants written in the same second could
    otherwise be scored against the first one's bytecode.
    """

    completed = subprocess.run(
        [sys.executable, "-B", str(test)],
        cwd=str(test.resolve().parents[1]),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=RUN_TIMEOUT,
        check=False,
    )
    return completed.returncode == 0


def _execute_mutants(
    module: Path,
    test: Path,
    limit: int = 0,
    *,
    stop_after_first: bool = False,
) -> tuple[list[Mutant], int]:
    """Execute selected mutants and return survivors plus the number actually attempted.

    Raises `UnverifiablePair` when the test does not pass against the normalized-but-unmutated
    source, because every mutant verdict downstream of that would be meaningless.
    """

    original = module.read_bytes()
    survivors: list[Mutant] = []
    attempted = 0
    try:
        # Baseline: unparse normalization strips comments and rewrites formatting, so the honest
        # baseline is the normalized source rather than the file as committed.
        module.write_text(
            normalized_source(original.decode("utf-8")), encoding="utf-8", newline="\n"
        )
        if not run_test(test):
            raise UnverifiablePair(
                f"{test.name} does not pass against unmutated {module.name}; "
                "no mutant result from this pair can be trusted"
            )
        for mutant in mutants(original.decode("utf-8"), limit=limit):
            attempted += 1
            # newline="\n" matters: without it Windows translates to CRLF, so the subject differs
            # from the committed bytes in a way unrelated to the mutation.
            module.write_text(mutant.mutated_source, encoding="utf-8", newline="\n")
            if run_test(test):
                survivors.append(mutant)
                if stop_after_first:
                    break
    finally:
        module.write_bytes(original)
        if module.read_bytes() != original:  # pragma: no cover - filesystem failure
            raise RuntimeError(
                f"FAILED TO RESTORE {module}. This path is inside the throwaway worktree, not your "
                "checkout, so nothing of yours is damaged; discard it with `git worktree prune`"
            )
    return survivors, attempted


def surviving_mutants(module: Path, test: Path, limit: int = 0) -> list[Mutant]:
    """All selected mutants of *module* that *test* fails to notice.

    The CLI uses `_execute_mutants(..., stop_after_first=True)` instead; this complete result remains
    useful for focused unit assertions about the detector itself.
    """

    survivors, _attempted = _execute_mutants(module, test, limit=limit)
    return survivors


@contextlib.contextmanager
def isolated_checkout(root: Path) -> Iterator[Path]:
    """Yield a throwaway `git worktree` at HEAD; mutate THAT, never the caller's tree.

    Why this exists, and why in-place mutation was not good enough.

    Restoring in a `finally` protects the person running the sweep. It does nothing for anything
    ELSE looking at the repository while it runs: for the whole sweep the working tree flips
    between correct and deliberately broken many times a second, and any observer sampling that
    window sees corruption. A stop hook that says "you have uncommitted changes, please commit"
    is the obvious one -- that pairing already produced a committed-adjacent
    `if __name__ != '__main__':` in `gate_a.py`, which made the gate exit 0 having run nothing --
    but a watch-mode test runner, an editor autosave, a second agent, or a CI job on the same
    checkout are all the same hazard.

    Isolation removes the whole class instead of narrowing the window. It also subsumes two
    mitigations that were only ever partial: SIGKILL is no longer unrecoverable (the worktree is
    disposable, and `git worktree prune` reclaims a leaked one), and a concurrent reader of the
    real tree can no longer observe a mutant at all.

    The clean-tree requirement STAYS, and is now about honesty rather than recovery: a worktree is
    pinned at HEAD, so with uncommitted changes present the sweep would silently report on code
    that is not the code in front of you. Refusing keeps "what you see is what was tested" true.

    Layout inside the worktree matches the original exactly, so every `relative_to(root)` in the
    caller still renders ordinary repo-relative paths and the report is unchanged.
    """
    parent = tempfile.mkdtemp(prefix="mutation-guard-")
    target = Path(parent) / "tree"
    created = subprocess.run(
        ["git", "-C", str(root), "worktree", "add", "--detach", str(target), "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if created.returncode != 0:
        shutil.rmtree(parent, ignore_errors=True)
        # Fail closed. Falling back to in-place mutation here would reintroduce the exact hazard
        # this function exists to remove, at the moment we have just learned the environment is
        # not behaving as expected -- the worst possible time to start writing to the real tree.
        raise RuntimeError(
            "cannot create an isolated git worktree "
            f"({(created.stderr or created.stdout).strip() or 'no output'}); refusing to mutate "
            "the working tree directly"
        )
    try:
        # RESOLVED, not as constructed. `discover` resolves every candidate it returns, so a caller
        # that later computes `module.relative_to(root)` needs the two sides canonicalized the same
        # way. `tempfile.mkdtemp` hands back `/var/...` on macOS (a symlink to `/private/var/...`)
        # and 8.3 short paths on Windows, so an unresolved yield raised
        # "is not in the subpath of" on both while passing on Linux. Same failure mode as the
        # containment check in check_links; canonicalize at the boundary, once.
        yield target.resolve()
    finally:
        subprocess.run(
            ["git", "-C", str(root), "worktree", "remove", "--force", str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        shutil.rmtree(parent, ignore_errors=True)
        # Drops the administrative entry if the directory vanished some other way (a killed run,
        # a cleaned /tmp). Without it `git worktree list` accumulates dead records.
        subprocess.run(
            ["git", "-C", str(root), "worktree", "prune"],
            capture_output=True,
            text=True,
            check=False,
        )


def _require_clean_tree(root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"cannot read git status in {root}")
    if completed.stdout.strip():
        raise RuntimeError(
            "working tree is dirty; the module run uses an isolated worktree pinned at HEAD, so "
            "uncommitted changes would not be tested and the report would describe code other than "
            "the code in front of you. Commit or stash first"
        )


def _sample_limit(raw: str) -> int:
    """Parse `--limit`, refusing anything that would silently select the wrong mutant set.

    A negative limit previously selected zero mutants and still printed PASS with exit 0 — a
    complete false green from a one-character typo.
    """

    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not an integer") from None
    if value < 0:
        raise argparse.ArgumentTypeError("must be 0 (no sample cap) or a positive sample size")
    return value


def is_inconclusive(
    unverifiable: Sequence[object],
    blind: Sequence[object],
    attempted: int,
) -> bool:
    """True when no survivor was found but something went uninspected.

    Extracted from `main` so the rule can be asserted directly instead of only through a full
    sweep. `blind` — test files for which no subject could be derived at all — was printed and then
    dropped from this decision, so a run whose every pair was blind still reported PASS. That is
    strictly more uninspected than a surviving mutant, and reporting it as a pass is the exact
    false-clean this tool exists to detect, committed by the tool itself.
    """
    return bool(unverifiable or blind or not attempted)


def _restore_on_termination() -> None:
    """Turn SIGTERM/SIGHUP into an exception so the in-place restore actually runs.

    `surviving_mutants` restores the module in a `finally`, which covers a normal error and a
    Ctrl-C (SIGINT arrives as KeyboardInterrupt, and `finally` runs on the way out). It does NOT
    cover SIGTERM: the default disposition terminates the process immediately, `finally` never
    runs, and the mutated file is left on disk.

    That is not a hypothetical. A tool-harness timeout killed a sweep of `scripts/gate_a.py` mid-run
    and left `if __name__ != '__main__':` committed-adjacent in the working tree. Run as a script
    that condition is false, so `main()` never executes: the gate printed nothing, exited 0, and
    read as a perfect pass. Any automation that then says "commit your changes" ships a permanently
    green, permanently inert gate.

    Raising from the handler unwinds through the same `finally` the other paths use, so one restore
    mechanism covers every exit that Python can still observe.

    Since worktree isolation this is belt-and-braces rather than the load-bearing control: the
    mutated bytes live in a throwaway checkout, so even SIGKILL costs nothing but a directory that
    `git worktree prune` reclaims. The handler is kept because restoring cleanly is still better
    than relying on the sandbox, and because the incident above is what the sandbox was built for.
    """
    def _handler(signum: int, _frame: object) -> None:
        raise KeyboardInterrupt(f"terminated by signal {signum}")

    for name in ("SIGTERM", "SIGHUP"):
        signum = getattr(signal, name, None)
        if signum is not None:
            try:
                signal.signal(signum, _handler)
            except (OSError, ValueError):  # pragma: no cover - non-main thread or unsupported
                pass


def _run_sweep(args: argparse.Namespace) -> int:
    """The sweep itself. `args.root` is the ISOLATED checkout, never the caller's tree.

    Split out of `main` so the isolation boundary is a single visible `with`, rather than a
    convention someone has to preserve while editing a long function.
    """
    # This CLI can ask only about one module. Repository-wide blind test files say nothing about
    # that named target and therefore cannot turn its result inconclusive.
    blind: list[Path] = []
    target = (args.root / args.module).resolve()

    findings: list[tuple[Path, Path, Mutant]] = []
    unverifiable: list[str] = []
    checked = 0
    attempted = 0
    for test, subjects in discover(args.root):
        for subject in subjects:
            module = subject.path
            if module != target:
                continue
            checked += 1
            print(f"  {module.relative_to(args.root).as_posix()} <- {test.name}", flush=True)
            try:
                # Inside the try: read_text and ast.parse raise the same four types the handler
                # below catches, and leaving them outside reintroduced the sweep-aborting crash
                # this handler was added to close.
                survivors, tried = _execute_mutants(
                    module,
                    test,
                    limit=args.limit,
                    stop_after_first=True,
                )
                # Counted only on the path that actually executed, so the reported sample size
                # cannot include mutants belonging to a pair that never ran.
                attempted += tried
            except UnverifiablePair as exc:
                # Not a pass and not a failure: this pair proved nothing, and saying so is the
                # whole point of the tool.
                unverifiable.append(str(exc))
                continue
            except (
                subprocess.TimeoutExpired,
                OSError,
                SyntaxError,
                UnicodeDecodeError,
                RecursionError,
            ) as exc:
                unverifiable.append(f"cannot mutate {module.name}: {exc}")
                continue
            if survivors:
                findings.append((test, module, survivors[0]))
                break
        if findings:
            break

    for message in unverifiable:
        print(f"mutation_guard: unverifiable -- {message}", file=sys.stderr)

    if not checked:
        print("mutation_guard: no test/module pair matched", file=sys.stderr)
        return EXIT_REFUSED
    summary = (
        f"no surviving mutants among {attempted} executed across {checked} pair(s), "
        f"limit={args.limit or 'none'}, {len(unverifiable)} unverifiable, "
        f"{len(blind)} with no subject derived"
    )
    if not findings:
        if is_inconclusive(unverifiable, blind, attempted):
            # Never lead with PASS when something went uninspected. The word is what a reader and
            # a log scraper take away; a blind or unverifiable run cannot support that claim.
            print(f"mutation_guard: INCONCLUSIVE -- {summary}")
            return EXIT_INCONCLUSIVE
        print(f"mutation_guard: PASS -- {summary}")
        return 0

    test, module, mutant = findings[0]
    print("\nmutation_guard: surviving mutant -- the focused test did not notice:")
    print(
        f"  {module.relative_to(args.root).as_posix()}:{mutant.lineno} "
        f"[{mutant.description}] survived {test.name}"
    )
    print("Further mutants are intentionally not executed or inventoried.")
    print("\nA survivor may be equivalent or irrelevant to the intended contract.")
    print("A survivor count is not a finding or backlog item.")
    print("Pin one named survivor with a focused red-first test, then stop.")
    return EXIT_INCONCLUSIVE if unverifiable else EXIT_SURVIVORS


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--limit",
        type=_sample_limit,
        default=DEFAULT_LIMIT,
        help=(
            "mutants per module as an evenly spaced sample; 0 removes the sample cap; "
            "execution always stops at the first survivor"
        ),
    )
    parser.add_argument(
        "--module",
        type=Path,
        required=True,
        metavar="PATH",
        help="one repository module to inspect; fleet-wide runs are refused",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Remap argparse's usage exit off EXIT_REFUSED so "you typed the flag wrong" and "this tree
        # is dirty, I will not run" stay distinguishable. `--help` exits 0 and is left alone.
        if exc.code == 2:
            return EXIT_USAGE
        raise
    # Canonicalize the root once, before anything derives a path from it. `discover` resolves a
    # literal `.py` subject but takes sibling subjects and every reported path from the root AS
    # GIVEN, so a non-canonical root makes the two disagree and `module.relative_to(args.root)`
    # raises ValueError, killing the whole sweep. The default ROOT is already resolved, which is
    # why this never surfaced locally -- but macOS hands out `/var/...` that resolves to
    # `/private/var/...`, and Windows hands out 8.3 short paths, so both hit it immediately.
    args.root = args.root.resolve()

    # Rebase --module onto the root NOW, while `args.root` is still the caller's real checkout.
    #
    # `_run_sweep` compares each discovered module against `(args.root / args.module).resolve()`,
    # and by then `args.root` is the isolated worktree. Joining an ABSOLUTE `--module` discards the
    # left operand entirely -- `Path("/worktree") / "/repo/scripts/x.py"` is `/repo/scripts/x.py` --
    # so the comparison targeted a file outside the worktree, matched nothing, and the run died with
    # "no test/module pair matched". A relative --module happened to keep working, which is what
    # made this easy to miss. Normalizing to a repo-relative path here means the join inside the
    # worktree is correct for both spellings.
    target = (args.root / args.module).resolve()
    try:
        args.module = target.relative_to(args.root)
    except ValueError:
        # Previously this fell through to the generic "no pair matched" refusal, which reads
        # like "your module has no tests" rather than "that path is not in this repository".
        print(
            f"mutation_guard: --module {args.module} resolves to {target}, which is outside "
            f"{args.root}; pass a path inside the repository being inspected",
            file=sys.stderr,
        )
        return EXIT_REFUSED

    try:
        _require_clean_tree(args.root)
    except RuntimeError as exc:
        print(f"mutation_guard: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    # Installed AFTER the clean-tree refusal and before the first in-place rewrite, so the window
    # where a mutated file can exist on disk is exactly the window the handler covers.
    _restore_on_termination()

    try:
        with isolated_checkout(args.root) as isolated:
            # Same layout, so every relative_to(args.root) below still renders ordinary
            # repo-relative paths; the report is identical to the in-place version's.
            args.root = isolated
            return _run_sweep(args)
    except RuntimeError as exc:
        print(f"mutation_guard: {exc}", file=sys.stderr)
        return EXIT_REFUSED


if __name__ == "__main__":
    raise SystemExit(main())
