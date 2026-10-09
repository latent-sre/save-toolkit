"""Where the runner's inputs live, and the tool inventories a trial is measured against."""

from __future__ import annotations

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
EVALS_DIR = PACKAGE_DIR.parent
ROOT = EVALS_DIR.parent
SCENARIO_DIR = ROOT / "evals" / "build-scenarios"
ORACLE_DIR = (ROOT / "evals" / "oracles").resolve()
CONTRACT_SCENARIO_DIR = ROOT / "evals" / "scenarios"


def stays_inside(relative: str) -> bool:
    """Whether a path a scenario names stays inside the folder it is relative to: not absolute, and
    no `..` part. Fixture files, references and probe-owned writes all name repository paths."""
    path = Path(relative)
    return not path.is_absolute() and ".." not in path.parts


def oracle_source(relative: object) -> Path | None:
    """The oracle file a check's `writes_from` names, or None unless it is a file under evals/oracles/."""
    source = (ROOT / str(relative)).resolve()
    return source if source.is_file() and ORACLE_DIR in source.parents else None


BUILD_TOOLS = ("Read", "Edit", "Write", "Grep", "Glob", "Bash", "Skill", "Task")
# Tools that can change files. A trial holding any of these never gets the measured checkout as a
# working directory, so a mistaken or fixture-supplied instruction cannot edit the candidate.
SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
WRITING_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"}) | SHELL_TOOLS
READ_TOOLS = ("Glob", "Grep", "Read")
# The dispatch tool goes by two names: `Agent` in agent frontmatter and in the calls a trace records,
# `Task` in the inventory a trial requests and the runtime advertises.
DISPATCH_TOOLS = frozenset({"Task", "Agent"})


def requested_tool_name(name: str) -> str:
    """A tool as a trial's inventory names it: either name of the dispatch tool is `Task`."""
    return "Task" if name in DISPATCH_TOOLS else name
