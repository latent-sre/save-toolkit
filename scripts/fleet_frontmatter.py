#!/usr/bin/env python3
"""Parse fleet frontmatter as the hosts read it: one YAML mapping between `---` fences.

PyYAML's safe loader gives the values Claude Code and Copilot see, so a scalar the host types
(`true`, `1`, `null`, `[Read, Grep]`) arrives typed here too, and a plain scalar the host rejects
(an unquoted `description` with `: ` inside it) is rejected here with its line number. Two fleet
rules sit on top of YAML: a duplicate key is an error, and keys are strings. The safe loader follows
YAML 1.1 typing, which is stricter than a YAML 1.2 host for `yes`/`no`/`on`/`off` and a few numeric
spellings; a reader that must match both hosts checks the spelled text (check_links' manual-only
rule does).

The module also owns the lexical conventions the grammar's readers share: component names, tool
grants, and the spellings of the plugin's runtime root.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, NamedTuple, TypeAlias

import yaml

Mode: TypeAlias = Literal["strict", "lenient"]
# Whatever the safe loader constructs: str, bool, int, float, None, list or dict.
FrontmatterValue: TypeAlias = object

# A component name: lowercase kebab-case. Pattern text, so callers can embed it in larger patterns.
KEBAB_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NAME_RE = re.compile(rf"^{KEBAB_NAME}$")
# Both spellings of the Claude plugin's runtime root: `${CLAUDE_PLUGIN_ROOT}` for POSIX shells, and
# `$env:CLAUDE_PLUGIN_ROOT` for PowerShell, where the braced form is a shell variable rather than the
# process environment. Pattern text; check_links and the adapter generator must recognize the same set.
PLUGIN_ROOT = r"\$(?:\{CLAUDE_PLUGIN_ROOT\}|env:CLAUDE_PLUGIN_ROOT)"
TOOL_GRANT_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.*-]*)(?:\((.*)\))?")
# The first frontmatter line is file line 1, so YAML's zero-based line inside the block is offset 2.
BLOCK_LINE_OFFSET = 2


class FrontmatterError(ValueError):
    """A syntax failure in the shared frontmatter grammar."""


class ParsedFrontmatter(NamedTuple):
    fields: dict[str, FrontmatterValue]
    body: str
    raw_lines: tuple[str, ...]
    problems: tuple[str, ...]
    # Per key: "plain", "double-quoted", "single-quoted", "block" (`|` or `>`), "list" or "mapping".
    styles: dict[str, str]


# Skills that must carry `disable-model-invocation: true`. Single-sourced here so
# check_links.py (validation) and generate_platform_adapters.py (projection) cannot
# drift; both import this name and keep a module attribute for test compatibility.
MANUAL_ONLY = {"pcf-deploy"}


class ToolGrant(NamedTuple):
    """One ``tools:`` entry, ``Name`` or ``Name(arguments)``."""

    spec: str
    # The text before any ``(``, even for a malformed entry: authority checks still reason over
    # what a malformed grant names, while its syntax is reported separately.
    base: str
    # The text inside the parentheses; None when there are none or the entry is malformed. An
    # empty ``Name()`` gives "", which callers treat as unscoped.
    arguments: str | None
    well_formed: bool


def split_tool_specs(raw: object) -> list[str]:
    """Split tool grants while keeping commas inside ``Tool(...)`` arguments."""
    if isinstance(raw, list):
        return [item.strip() for item in raw if isinstance(item, str) and item.strip()]
    if not isinstance(raw, str):
        return []
    result: list[str] = []
    start = depth = 0
    for index, char in enumerate(raw):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif char == "," and depth == 0:
            if spec := raw[start:index].strip():
                result.append(spec)
            start = index + 1
    if spec := raw[start:].strip():
        result.append(spec)
    return result


def parse_tool_grant(spec: str) -> ToolGrant:
    match = TOOL_GRANT_RE.fullmatch(spec)
    if match is None:
        return ToolGrant(spec, spec.split("(", 1)[0].strip(), None, well_formed=False)
    return ToolGrant(spec, match.group(1), match.group(2), well_formed=True)


def tool_grants(raw: object) -> list[ToolGrant]:
    """Parse a ``tools:`` value, a comma-separated string or a list, in declaration order."""
    return [parse_tool_grant(spec) for spec in split_tool_specs(raw)]


def delegation_targets(grants: list[ToolGrant], source: str | Path, *, plugin: str) -> list[str]:
    """Bare target names from exact ``Agent(plugin:target, ...)`` grants, in declaration order.

    An ``Agent`` grant without an explicit allowlist, a target outside ``plugin``, and a repeated
    target are errors: a delegation graph that cannot be read exactly must not be guessed at.
    """
    targets: list[str] = []
    for grant in grants:
        if grant.base != "Agent":
            continue
        # Exactly `Agent(<targets>)`: a bare or malformed grant carries no arguments, and nested
        # parentheses are not an allowlist.
        arguments = grant.arguments
        if arguments is None or "(" in arguments or ")" in arguments:
            raise ValueError(f"{source}: Agent tool must declare an explicit target allowlist")
        for target in (item.strip() for item in arguments.split(",")):
            if not re.fullmatch(rf"{re.escape(plugin)}:{KEBAB_NAME}", target):
                raise ValueError(f"{source}: invalid Agent target {target!r}")
            target = target.removeprefix(f"{plugin}:")
            if target in targets:
                raise ValueError(f"{source}: duplicate Agent target {target!r}")
            targets.append(target)
    return targets


def _problem(
    problems: list[str], mode: Mode, source: str, line_number: int | None, message: str
) -> None:
    where = f"{source}:{line_number}" if line_number is not None else source
    rendered = f"{where}: {message}"
    if mode == "strict":
        raise FrontmatterError(rendered)
    problems.append(rendered)


def _line(node: yaml.Node) -> int:
    return int(node.start_mark.line) + BLOCK_LINE_OFFSET


def _style(node: yaml.Node) -> str:
    if isinstance(node, yaml.SequenceNode):
        return "list"
    if isinstance(node, yaml.MappingNode):
        return "mapping"
    style = node.style if isinstance(node, yaml.ScalarNode) else None
    return {'"': "double-quoted", "'": "single-quoted", "|": "block", ">": "block"}.get(str(style or ""), "plain")


def _yaml_error_detail(exc: yaml.YAMLError) -> tuple[int | None, str]:
    mark = getattr(exc, "problem_mark", None)
    line = None if mark is None else int(mark.line) + BLOCK_LINE_OFFSET
    detail = getattr(exc, "problem", None) or str(exc).splitlines()[0]
    return line, str(detail)


def parse(text: str, source: str | Path, *, mode: Mode = "strict") -> ParsedFrontmatter:
    """Parse frontmatter text in strict (raise) or lenient (collect) mode.

    Lenient mode collects duplicate keys and non-string keys and keeps the first value; a YAML
    syntax error ends the parse with that one problem, because nothing after it is defined.
    """
    if mode not in {"strict", "lenient"}:
        raise ValueError(f"unsupported frontmatter parse mode: {mode!r}")

    source_name = source.as_posix() if isinstance(source, Path) else str(source)
    problems: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        _problem(problems, mode, source_name, None, "missing opening frontmatter marker")
        return ParsedFrontmatter({}, text, (), tuple(problems), {})
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        _problem(problems, mode, source_name, None, "missing closing frontmatter marker")
        return ParsedFrontmatter({}, text, (), tuple(problems), {})

    raw_lines = tuple(lines[1:end])
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    if text.endswith("\n"):
        body += "\n"

    fields: dict[str, FrontmatterValue] = {}
    styles: dict[str, str] = {}
    # The block ends with a line break in the file (the closing fence follows it), so the host sees
    # one; without it a clip-chomped block scalar (`|`, `>`) would lose its final newline here.
    loader = yaml.SafeLoader("\n".join(raw_lines) + "\n")
    try:
        try:
            document = loader.get_single_node()
        except yaml.YAMLError as exc:
            line, detail = _yaml_error_detail(exc)
            _problem(problems, mode, source_name, line, f"invalid frontmatter YAML: {detail}")
            return ParsedFrontmatter({}, body, raw_lines, tuple(problems), {})
        if document is None:  # an empty block between the fences
            return ParsedFrontmatter({}, body, raw_lines, tuple(problems), {})
        if not isinstance(document, yaml.MappingNode):
            _problem(problems, mode, source_name, _line(document), "frontmatter must be a YAML mapping")
            return ParsedFrontmatter({}, body, raw_lines, tuple(problems), {})
        for key_node, value_node in document.value:
            key = loader.construct_object(key_node, deep=True)
            if not isinstance(key, str):
                _problem(problems, mode, source_name, _line(key_node), f"frontmatter keys must be strings, not {key!r}")
                continue
            if key in fields:
                _problem(problems, mode, source_name, _line(key_node), f"duplicate frontmatter key {key!r}")
                continue
            try:
                value = loader.construct_object(value_node, deep=True)
            except yaml.YAMLError as exc:
                line, detail = _yaml_error_detail(exc)
                _problem(problems, mode, source_name, line, f"invalid frontmatter YAML: {detail}")
                continue
            fields[key] = value
            styles[key] = _style(value_node)
    finally:
        loader.dispose()
    return ParsedFrontmatter(fields, body, raw_lines, tuple(problems), styles)


def parse_file(path: Path, *, mode: Mode = "strict") -> ParsedFrontmatter:
    """Read one UTF-8 file and parse it with the shared grammar."""
    return parse(path.read_text(encoding="utf-8"), path, mode=mode)
