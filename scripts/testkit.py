"""Helpers shared by the scripts/ test suites. Not a test module: pytest collects only test_*.py.

Plain functions rather than pytest fixtures, because most suites are unittest.TestCase classes that
also run directly (`python scripts/test_platform_adapters.py`), where fixtures do not exist. Nothing
here runs at import time; every xdist worker imports this module once per process.

Helpers that read Markdown are deliberately independent of the generator's and validator's own
parsers: checking a tool's output with that tool's parser would make the assertion circular.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]

_GIT_FOR_WINDOWS = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Git"


def load_path(path: Path, name: str) -> ModuleType:
    """Import one source file as module `name`, registered in sys.modules while it executes.

    Registration is what `import` itself does; without it a dataclass or a pickled object defined in
    the file cannot find its module. A failed import leaves no half-initialized module behind.
    """
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path} as a module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def find_shell(name: str = "sh") -> str | None:
    """A POSIX `sh` or `bash`, including the copies Git for Windows installs off PATH."""
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        for directory in ("bin", "usr/bin"):
            candidate = _GIT_FOR_WINDOWS / directory / f"{name}.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def require_shell(test: unittest.TestCase, name: str = "sh") -> str:
    """The shell's path; skip a local run without one, but fail on CI, where a skip reads as green."""
    found = find_shell(name)
    if found:
        return found
    if os.environ.get("CI"):
        test.fail(f"CI has no `{name}`; this test's shell contract would be reported green unexercised")
    test.skipTest(f"no `{name}` on this host")


def must_replace(text: str, old: str, new: str, count: int = 1) -> str:
    """`text.replace(old, new, count)` that fails when `old` is absent.

    A mutation that silently matches nothing leaves an acceptance test (`assertEqual([], failures)`)
    passing without having tested anything.
    """
    if old not in text:
        raise AssertionError(f"mutation target not found: {old!r}")
    return text.replace(old, new, count)


def normalized(text: str) -> str:
    """Case- and whitespace-insensitive form, so rewrapping a paragraph does not break an assertion."""
    return re.sub(r"\s+", " ", text.lower()).strip()


def markdown_section(text: str, heading: str) -> str:
    """The body under the exact heading line `heading` (e.g. `## Evidence`), up to the next heading
    of the same or a higher level. `## Evidence` does not match `### Evidence` or `## Evidence base`.
    """
    level = len(heading) - len(heading.lstrip("#"))
    if not level:
        raise ValueError(f"not a Markdown heading: {heading!r}")
    found = re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.MULTILINE)
    if found is None:
        raise AssertionError(f"missing heading {heading!r}")
    body = text[found.end():]
    following = re.search(rf"^#{{1,{level}}}[ \t]", body, re.MULTILINE)
    return body[: following.start()] if following else body


def frontmatter_block(text: str) -> str:
    """The raw text between a document's opening `---` fence and its closing `---` line."""
    found = re.match(r"---\n(.*?)^---$", text, re.DOTALL | re.MULTILINE)
    if found is None:
        raise AssertionError("document does not open with a closed `---` frontmatter block")
    return found.group(1)
