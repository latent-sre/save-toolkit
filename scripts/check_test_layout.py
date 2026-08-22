#!/usr/bin/env python3
"""Reject test classes that a test file's script entrypoint makes unreachable."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST_PATTERNS = ("scripts/test_*.py", "evals/test_*.py")


def _entrypoint_line(tree: ast.Module) -> int | None:
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
        ):
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
