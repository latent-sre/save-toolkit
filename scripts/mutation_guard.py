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
on a dirty working tree, so an interrupted run can always be recovered with `git restore`. It is a
sampling tool, not a proof: `--limit` bounds the mutants per module and the default budget is small
enough to run in a gate, so a clean report means "no survivor among the mutants tried", never "the
suite is complete".

Pure standard library.

    python3 scripts/mutation_guard.py                 # gate budget over every discovered pair
    python3 scripts/mutation_guard.py --limit 0       # every mutant (slow)
    python3 scripts/mutation_guard.py --module skills/operational-learning/scripts/packet_drift.py
"""

from __future__ import annotations

import argparse
import ast
import copy
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
DEFAULT_LIMIT = 12
RUN_TIMEOUT = 900


@dataclass(frozen=True)
class Mutant:
    lineno: int
    description: str
    mutated_source: str


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
    """Every single-point mutant of *source*, in deterministic order, deduplicated."""

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
        if limit and len(produced) >= limit:
            break
    return produced


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

    pairs: list[tuple[Path, list[Path]]] = []
    for pattern in TEST_GLOBS:
        for test in sorted(root.glob(pattern)):
            modules: list[Path] = []
            sibling = test.with_name(test.name[len("test_") :])
            if sibling.is_file():
                modules.append(sibling)
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
                    and candidate not in modules
                    and not candidate.name.startswith("test_")
                ):
                    modules.append(candidate)
            pairs.append((test, modules))
    return pairs


def unresolved(root: Path) -> list[Path]:
    """Test files this guard cannot mutate anything for — reported, never silently skipped."""

    return [test for test, modules in discover(root) if not modules]


def _run_test(test: Path) -> bool:
    """True when the test file passes."""

    completed = subprocess.run(
        [sys.executable, str(test)],
        cwd=str(test.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=RUN_TIMEOUT,
        check=False,
    )
    return completed.returncode == 0


def surviving_mutants(module: Path, test: Path, limit: int = 0) -> list[Mutant]:
    """Mutants of *module* that *test* fails to notice."""

    original = module.read_bytes()
    survivors: list[Mutant] = []
    try:
        for mutant in mutants(original.decode("utf-8"), limit=limit):
            module.write_text(mutant.mutated_source, encoding="utf-8")
            if _run_test(test):
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="mutants per module; 0 means every mutant (slow)",
    )
    parser.add_argument("--module", type=Path, help="restrict to one module path")
    args = parser.parse_args(argv)

    try:
        _require_clean_tree(args.root)
    except RuntimeError as exc:
        print(f"mutation_guard: {exc}", file=sys.stderr)
        return 2

    blind = unresolved(args.root)
    if blind:
        print("mutation_guard: no subject derived for these test files (not mutated):")
        for test in blind:
            print(f"  {test.relative_to(args.root).as_posix()}")
        print()

    findings: list[tuple[Path, Path, Mutant]] = []
    checked = 0
    for test, modules in discover(args.root):
        for module in modules:
            if args.module is not None and module != (args.root / args.module).resolve():
                continue
            checked += 1
            print(f"  {module.relative_to(args.root).as_posix()} <- {test.name}", flush=True)
            try:
                survivors = surviving_mutants(module, test, limit=args.limit)
            except (subprocess.TimeoutExpired, OSError, SyntaxError) as exc:
                print(f"mutation_guard: cannot mutate {module}: {exc}", file=sys.stderr)
                return 2
            findings.extend((test, module, mutant) for mutant in survivors)

    if not checked:
        print("mutation_guard: no test/module pair matched", file=sys.stderr)
        return 2
    if not findings:
        print(f"mutation_guard: PASS -- no surviving mutants across {checked} pair(s)")
        return 0

    print(f"\nmutation_guard: {len(findings)} surviving mutant(s) -- the suite did not notice:")
    for test, module, mutant in findings:
        print(
            f"  {module.relative_to(args.root).as_posix()}:{mutant.lineno} "
            f"[{mutant.description}] survived {test.name}"
        )
    print("\nA survivor is not automatically a defect -- it may be semantically equivalent.")
    print("It is a place where the suite proves less than it appears to.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
