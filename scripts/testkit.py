"""Helpers shared by the scripts/ test suites. Not a test module: pytest collects only test_*.py.

Plain functions rather than pytest fixtures, because most suites are unittest.TestCase classes that
also run directly (`python scripts/test_platform_adapters.py`), where fixtures do not exist. Nothing
here runs at import time; every xdist worker imports this module once per process.

Helpers that read Markdown are deliberately independent of the generator's and validator's own
parsers: checking a tool's output with that tool's parser would make the assertion circular.

Each test module keeps its own `ROOT = Path(__file__).resolve().parents[1]` and reads repository
files as `ROOT / "..."` there. The fleet atlas credits a test with verifying a file only through
that module-local binding (fleet_atlas_v2_extract.rooted_reads), so a test that imports ROOT from
here silently drops out of the atlas's change-impact answers. `_ROOT` below is this module's own.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import unittest
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType

_ROOT = Path(__file__).resolve().parents[1]

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
    """A POSIX `sh` or `bash` for this host's files.

    On Windows, Git for Windows' copy comes first, including where it sits off PATH, and the
    System32 `bash.exe` is refused: that one launches WSL, a different machine's view of the files.
    """
    if os.name != "nt":
        return shutil.which(name)
    for directory in ("bin", "usr/bin"):
        candidate = _GIT_FOR_WINDOWS / directory / f"{name}.exe"
        if candidate.is_file():
            return str(candidate)
    found = shutil.which(name)
    system = Path(os.environ.get("SYSTEMROOT", r"C:\Windows")) / "System32"
    if found and Path(found).parent.resolve() == system.resolve():
        return None
    return found


def require_shell(name: str = "sh") -> str:
    """The shell's path; skip a local run without one, but fail on CI, where a skip reads as green.

    Raises unittest.SkipTest, which both unittest and pytest report as a skip, so it serves
    TestCase methods and plain pytest functions alike.
    """
    found = find_shell(name)
    if found:
        return found
    if os.environ.get("CI"):
        raise AssertionError(f"CI has no `{name}`; this test's shell contract would be reported green unexercised")
    raise unittest.SkipTest(f"no `{name}` on this host")


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


# --- Guard ------------------------------------------------------------------------------------
# Every suite that classifies commands with scripts/readonly-guard.py runs it through these, the way
# the hook launches it: `python -I -S`, the PreToolUse payload on stdin. The exit codes are literals
# on purpose, never read from the guard: codes taken from the module under test would agree with
# whatever value it chose, and the hook launchers hard-code these three.

GUARD = _ROOT / "scripts" / "readonly-guard.py"
GUARD_ALLOW = 42
GUARD_DENY = 43
GUARD_INDETERMINATE = 44
SRE_ASSISTANT = "save-toolkit:sre-assistant"


def guard_payload(command: object, *, tool_name: str = "Bash", agent_type: str | None = SRE_ASSISTANT) -> str:
    """A PreToolUse payload from the guarded agent unless told otherwise.

    The guard no-ops unless `agent_type` names a lane it inspects, so a default without one would let
    a deny corpus pass while testing only the short-circuit. `agent_type=None` omits the key, which
    is what the main loop sends (absent, not null; probed on CLI 2.1.200) and what --copilot reads.
    """
    data: dict[str, object] = {"tool_name": tool_name, "tool_input": {"command": command}}
    if agent_type is not None:
        data["agent_type"] = agent_type
    return json.dumps(data)


def run_guard(payload: str, *, copilot: bool = False) -> subprocess.CompletedProcess[bytes]:
    """One guard run with `payload` on stdin, isolated as the hook runs it."""
    return subprocess.run(
        [sys.executable, "-I", "-S", str(GUARD), *(["--copilot"] if copilot else [])],
        input=payload.encode("utf-8"), capture_output=True, timeout=30, check=False,
    )


def run_guard_batch(payloads: Iterable[str], *, copilot: bool = False) -> list[subprocess.CompletedProcess[bytes]]:
    """run_guard for each payload, overlapped, in payload order.

    The guard is a stateless stdin-to-verdict filter, so overlap changes nothing about any one run;
    it stops hundreds of interpreter launches queuing behind each other.
    """
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda payload: run_guard(payload, copilot=copilot), payloads))


def guard_decision(proc: subprocess.CompletedProcess[bytes]) -> str:
    """'allow' or 'deny', failing unless the exit code and stdout agree.

    The hook takes the exit code as proof that this guard answered, not a stand-in that exits 0, so
    stdout and code must match on every call. Any other exit, 44 included, is not a decision and
    fails here; a test expecting indeterminate asserts the code itself.
    """
    out = proc.stdout.decode("utf-8").strip()
    if proc.returncode == GUARD_ALLOW:
        if out:
            raise AssertionError(f"exit {GUARD_ALLOW} (allow) but stdout was not empty: {out!r}")
        return "allow"
    if proc.returncode == GUARD_DENY:
        verdict = json.loads(out)["hookSpecificOutput"]["permissionDecision"]
        if verdict != "deny":
            raise AssertionError(f"exit {GUARD_DENY} (deny) but stdout said {verdict!r}")
        return "deny"
    raise AssertionError(
        f"guard exited {proc.returncode}, expected {GUARD_ALLOW} (allow) or {GUARD_DENY} (deny); "
        f"stdout={out!r} stderr={proc.stderr.decode('utf-8', 'replace')[:300]!r}"
    )


def assert_guard_decisions(
    test: unittest.TestCase,
    expected: str,
    commands: Iterable[object],
    *,
    tool_names: Iterable[str] = ("Bash",),
    agent_types: Iterable[str | None] = (SRE_ASSISTANT,),
    copilot: bool = False,
    reason: str | None = None,
) -> None:
    """Assert `expected` for every command in every tool and agent context, run as one batch.

    Each case is its own subTest. `reason`, when given, must appear in every answer's stdout.
    """
    cases = list(itertools.product(tool_names, agent_types, commands))
    payloads = [guard_payload(command, tool_name=tool, agent_type=agent) for tool, agent, command in cases]
    for (tool, agent, command), proc in zip(cases, run_guard_batch(payloads, copilot=copilot), strict=True):
        with test.subTest(tool_name=tool, agent_type=agent, command=command):
            test.assertEqual(expected, guard_decision(proc))
            if reason is not None:
                test.assertIn(reason, proc.stdout.decode("utf-8"))
