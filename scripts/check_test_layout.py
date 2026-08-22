#!/usr/bin/env python3
"""Require executable test entrypoints and reject classes they make unreachable."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATTERNS = ("scripts/test_*.py", "evals/test_*.py")


def _is_main_guard(node: ast.expr) -> bool:
    if (
        not isinstance(node, ast.Compare)
        or len(node.ops) != 1
        or not isinstance(node.ops[0], ast.Eq)
        or len(node.comparators) != 1
    ):
        return False
    left, right = node.left, node.comparators[0]
    return (
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(right, ast.Constant)
        and right.value == "__main__"
    ) or (
        isinstance(right, ast.Name)
        and right.id == "__name__"
        and isinstance(left, ast.Constant)
        and left.value == "__main__"
    )


def _is_test_runner_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    function = node.func
    return (
        isinstance(function, ast.Name)
        and function.id == "main"
    ) or (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "unittest"
        and function.attr == "main"
    )


def _guard_calls_runner(statements: list[ast.stmt]) -> bool:
    """True when the guard body itself reaches a test-runner call.

    Nested function or class bodies are never executed by running the guard, so a
    ``unittest.main()`` defined only inside one leaves the script silent; those
    statements are not descended into.
    """
    stack: list[ast.AST] = list(statements)
    while stack:
        node = stack.pop()
        if _is_test_runner_call(node):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(ast.iter_child_nodes(node))
    return False


def _entrypoint_line(tree: ast.Module) -> int | None:
    for node in tree.body:
        if not isinstance(node, ast.If) or not _is_main_guard(node.test):
            continue
        if _guard_calls_runner(node.body):
            return node.lineno
    return None


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    paths = [
        path
        for pattern in TEST_PATTERNS
        for path in sorted(root.glob(pattern))
    ]
    if not paths:
        return ["test corpus not found; test-layout validation would prove nothing"]

    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError) as exc:
            failures.append(f"{path.relative_to(root).as_posix()}: cannot inspect test layout: {exc}")
            continue
        entrypoint = _entrypoint_line(tree)
        if entrypoint is None:
            failures.append(
                f"{path.relative_to(root).as_posix()}: missing executable test entrypoint; "
                "add an if __name__ == '__main__' block that calls unittest.main() or main()"
            )
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.lineno > entrypoint:
                failures.append(
                    f"{path.relative_to(root).as_posix()}:{node.lineno}: "
                    f"class {node.name} is unreachable when the test runs as a script"
                )
    return failures


def main() -> int:
    failures = validate()
    if failures:
        print("check_test_layout: FAIL", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("check_test_layout: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
