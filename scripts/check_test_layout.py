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


def _statically_false(node: ast.expr) -> bool:
    """True only for conditions a reader can prove never execute.

    Deliberately narrow — a bare ``False``/``0`` literal or ``not <truthy literal>``. Anything
    wider risks declaring a live branch dead and hiding its runner call, which is the exact
    silent-pass shape this validator exists to reject.
    """
    if isinstance(node, ast.Constant):
        return not node.value
    return (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, ast.Not)
        and isinstance(node.operand, ast.Constant)
        and bool(node.operand.value)
    )


def _reachable_children(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.If):
        children: list[ast.AST] = []
        if not _statically_false(node.test):
            children.extend(node.body)
        children.extend(node.orelse)
        return children
    if isinstance(node, ast.While):
        # A statically-false condition means the body never runs; the else clause still can.
        if _statically_false(node.test):
            return list(node.orelse)
        return list(node.body) + list(node.orelse)
    if isinstance(node, ast.Try):
        return list(node.body) + list(node.orelse) + list(node.finalbody) + [
            child for handler in node.handlers for child in ast.iter_child_nodes(handler)
        ]
    if isinstance(node, (ast.Match, ast.IfExp)):
        # Pattern/value matching cannot be proven dead statically; treat every branch reachable.
        return [child for child in ast.iter_child_nodes(node) if not isinstance(child, ast.expr)]
    return list(ast.iter_child_nodes(node))


def _guard_calls_runner(statements: list[ast.stmt]) -> bool:
    """True when the guard body itself reaches a test-runner call.

    Nested function or class bodies are never executed by running the guard, so a
    ``unittest.main()`` defined only inside one leaves the script silent; those
    statements are not descended into. A call inside a statically dead branch
    (``if False:``, ``while 0:``) likewise never runs, so it does not count either.
    """
    stack: list[ast.AST] = list(statements)
    while stack:
        node = stack.pop()
        if _is_test_runner_call(node):
            return True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        stack.extend(_reachable_children(node))
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
