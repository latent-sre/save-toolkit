#!/usr/bin/env python3
"""Prove that a test suite fails when the contract it names is broken.

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
For each test file, it derives the module(s) that test actually exercises, rewrites one small piece
of that module's logic, and runs the test file. A mutant that **survives** — the suite still passes
against deliberately broken code — is reported with the exact source change that went unnoticed.
Survivors are not automatically defects: a mutant can be semantically equivalent, or land on a line
whose behaviour genuinely does not matter. They are places where the suite proves less than it looks
like it proves.

SUBJECTS ARE DERIVED, NEVER HAND-KEPT
-------------------------------------
`discover` reads each `scripts/test_*.py` for the `.py` paths it names and the sibling `X.py` it
implies, so a new test file enrols its own subject with no edit here. That is deliberate: this
repository has already shipped a test file that was wired into nothing because a hand-kept roster
forgot it.

HONEST LIMITS
-------------
This mutates the module **in place** and restores it from memory in a `finally`. It refuses to start
on a dirty working tree, so an interrupted run can always be recovered with `git restore`, and it
converts SIGTERM/SIGHUP into an exception so a harness timeout unwinds through that same restore
instead of leaving a mutant on disk (see `_restore_on_termination` for the incident that motivated
it). SIGKILL is unrecoverable by construction. A full sweep runs the suite once per mutant, which is
far too slow for CI -- it is a deliberate run, like the routing evals.

`--limit` makes it a sampling tool rather than a proof. A clean bounded report means "no survivor
among the mutants tried"; it never means "the suite is complete", and it never establishes that any
particular mutant was among those tried. Only an unbounded run -- the default -- covers every
mutant, which is why the "the test probably never exercises it" verdict is withheld under `--limit`:
that is a claim about mutants nobody ran, and a bounded observation cannot support it.

Pure standard library.

    python3 scripts/mutation_guard.py                 # every mutant of every pair (slow)
    python3 scripts/mutation_guard.py --limit 12      # an evenly spaced sample per module
    python3 scripts/mutation_guard.py --module skills/operational-learning/scripts/packet_drift.py
"""

from __future__ import annotations

import argparse
import ast
import copy
import signal
import subprocess
import sys
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

    Provenance is load-bearing, not bookkeeping. A `sibling` subject (`test_x.py` -> `x.py`) is a
    link the repository's own convention asserts, so if every mutant of it survives, the test
    proves nothing and that is the most severe finding this tool can produce. A `literal` subject
    was inferred from a `.py` string in the test's source, which is often a fixture path rather
    than an import — there, total survival usually means the test never exercised it at all.
    Treating both the same is what let a real finding be reported in the same breath as four
    known-benign path-string artifacts.
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
    Prefix truncation only ever mutates the shallowest sites: on this repository's own
    `packet_drift.py` the motivating mutant sits at index 35 of 48, so a prefix budget would
    silently exclude the exact mutation this guard was built to catch.

    Even spacing closes that failure without making a bounded run complete. An evenly spaced
    sample can still miss any given mutant, the motivating one included -- over those same 48
    sites `--limit 12` selects 34 and 38, bracketing 35 without ever selecting it. Read the
    difference precisely: even spacing guarantees the sample *spans* the file, not that it
    *contains* anything in particular. Only an unbounded run tries every mutant.
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
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                if not node.value.endswith(".py"):
                    continue
                candidate = (root / node.value).resolve()
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
    """True when the test file passes. Run from the repository root, as Gate A runs it.

    `-B` is load-bearing: CPython validates a cached `.pyc` on `(int(mtime), size)`, and an `==`
    to `!=` swap leaves the file the same size, so two mutants written in the same second could
    otherwise be scored against the first one's bytecode.
    """

    completed = subprocess.run(
        [sys.executable, "-B", str(test)],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=RUN_TIMEOUT,
        check=False,
    )
    return completed.returncode == 0


def surviving_mutants(module: Path, test: Path, limit: int = 0) -> list[Mutant]:
    """Mutants of *module* that *test* fails to notice.

    Raises `UnverifiablePair` when the test does not pass against the normalized-but-unmutated
    source, because every mutant verdict downstream of that would be meaningless.
    """

    original = module.read_bytes()
    survivors: list[Mutant] = []
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
            # newline="\n" matters: without it Windows translates to CRLF, so the subject differs
            # from the committed bytes in a way unrelated to the mutation.
            module.write_text(mutant.mutated_source, encoding="utf-8", newline="\n")
            if run_test(test):
                survivors.append(mutant)
    finally:
        module.write_bytes(original)
        if module.read_bytes() != original:  # pragma: no cover - filesystem failure
            raise RuntimeError(f"FAILED TO RESTORE {module}; recover with git restore")
    return survivors


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
            "working tree is dirty; mutation_guard rewrites files in place and requires a clean "
            "tree so an interrupted run is always recoverable with git restore"
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
        raise argparse.ArgumentTypeError("must be 0 (every mutant) or a positive sample size")
    return value


def is_inconclusive(
    unverifiable: Sequence[object],
    unexercised: Sequence[object],
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
    return bool(unverifiable or unexercised or blind or not attempted)


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
    mechanism covers every exit that Python can still observe. SIGKILL remains unrecoverable by
    construction -- hence the clean-tree requirement, which keeps `git restore` a reliable undo.
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--limit",
        type=_sample_limit,
        default=DEFAULT_LIMIT,
        help="mutants per module as an evenly spaced sample; 0 means every mutant (slow)",
    )
    parser.add_argument("--module", type=Path, help="restrict to one module path")
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

    try:
        _require_clean_tree(args.root)
    except RuntimeError as exc:
        print(f"mutation_guard: {exc}", file=sys.stderr)
        return EXIT_REFUSED

    # Installed AFTER the clean-tree refusal and before the first in-place rewrite, so the window
    # where a mutated file can exist on disk is exactly the window the handler covers.
    _restore_on_termination()

    blind = unresolved(args.root)
    if blind:
        print("mutation_guard: no subject derived for these test files (not mutated):")
        for test in blind:
            print(f"  {test.relative_to(args.root).as_posix()}")
        print()

    findings: list[tuple[Path, Path, Mutant]] = []
    unverifiable: list[str] = []
    unexercised: list[str] = []
    checked = 0
    attempted = 0
    for test, subjects in discover(args.root):
        for subject in subjects:
            module = subject.path
            if args.module is not None and module != (args.root / args.module).resolve():
                continue
            checked += 1
            print(f"  {module.relative_to(args.root).as_posix()} <- {test.name}", flush=True)
            try:
                # Inside the try: read_text and ast.parse raise the same four types the handler
                # below catches, and leaving them outside reintroduced the sweep-aborting crash
                # this handler was added to close.
                tried = len(mutants(module.read_text(encoding="utf-8"), limit=args.limit))
                survivors = surviving_mutants(module, test, limit=args.limit)
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
            # Collapse ONLY inferred subjects, and ONLY on an unbounded run.
            #
            # Inferred: a `.py` string in a test is often a fixture path, so total survival there
            # usually means the test never exercised the module and `tried` separate findings would
            # bury the real ones. A sibling subject is different — the repository's own naming
            # convention asserts that link, so total survival is the most severe finding this tool
            # can produce and must stay a finding. Collapsing both traded one false clean for
            # another.
            #
            # Unbounded: under `--limit`, `tried` is the sample size, not the mutant population, so
            # `len(survivors) == tried` says only that every *sampled* mutant survived. A module the
            # test genuinely exercises can sample that way, and calling it unexercised would be this
            # tool asserting a strong negative from a bounded observation — the same overclaim it
            # exists to detect. Bounded runs report the survivors they actually saw instead.
            every_mutant_survived = bool(survivors) and len(survivors) == tried
            inferred = subject.origin == "literal"
            if every_mutant_survived and inferred and not args.limit:
                unexercised.append(
                    f"{module.relative_to(args.root).as_posix()} <- {test.name}: "
                    f"all {tried} mutants survived an inferred (non-sibling) pairing "
                    "on an unbounded run; the test probably never exercises it"
                )
                continue
            findings.extend((test, module, mutant) for mutant in survivors)

    for message in unexercised:
        print(f"mutation_guard: unexercised -- {message}", file=sys.stderr)
    for message in unverifiable:
        print(f"mutation_guard: unverifiable -- {message}", file=sys.stderr)

    if not checked:
        print("mutation_guard: no test/module pair matched", file=sys.stderr)
        return EXIT_REFUSED
    summary = (
        f"no surviving mutants among {attempted} executed across {checked} pair(s), "
        f"limit={args.limit or 'none'}, {len(unverifiable)} unverifiable, "
        f"{len(unexercised)} unexercised, {len(blind)} with no subject derived"
    )
    if not findings:
        if is_inconclusive(unverifiable, unexercised, blind, attempted):
            # Never lead with PASS when something went uninspected. The word is what a reader and
            # a log scraper take away, and "PASS" over an unexercised bucket is this tool
            # committing the false-clean it exists to detect.
            print(f"mutation_guard: INCONCLUSIVE -- {summary}")
            return EXIT_INCONCLUSIVE
        print(f"mutation_guard: PASS -- {summary}")
        return 0

    print(f"\nmutation_guard: {len(findings)} surviving mutant(s) -- the suite did not notice:")
    for test, module, mutant in findings:
        print(
            f"  {module.relative_to(args.root).as_posix()}:{mutant.lineno} "
            f"[{mutant.description}] survived {test.name}"
        )
    print("\nA survivor is not automatically a defect -- it may be semantically equivalent.")
    print("It is a place where the suite proves less than it appears to.")
    return EXIT_INCONCLUSIVE if (unverifiable or unexercised) else EXIT_SURVIVORS


if __name__ == "__main__":
    raise SystemExit(main())
