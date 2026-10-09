#!/usr/bin/env python3
"""Parse the deliberately small frontmatter grammar shared by fleet tooling.

It also owns the lexical conventions the grammar's readers must agree on: component names, tool
grants, and the spellings of the plugin's runtime root.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, NamedTuple, TypeAlias


Mode: TypeAlias = Literal["strict", "lenient"]
FrontmatterValue: TypeAlias = str | list[str]

KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
LIST_ITEM_RE = re.compile(r"\s+-\s+(.+?)\s*")
BLOCK_MARKERS = {">", ">-", "|", "|-"}
# A component name: lowercase kebab-case. Pattern text, so callers can embed it in larger patterns.
KEBAB_NAME = r"[a-z0-9]+(?:-[a-z0-9]+)*"
NAME_RE = re.compile(rf"^{KEBAB_NAME}$")
# Both spellings of the Claude plugin's runtime root: `${CLAUDE_PLUGIN_ROOT}` for POSIX shells, and
# `$env:CLAUDE_PLUGIN_ROOT` for PowerShell, where the braced form is a shell variable rather than the
# process environment. Pattern text; check_links and the adapter generator must recognize the same set.
PLUGIN_ROOT = r"\$(?:\{CLAUDE_PLUGIN_ROOT\}|env:CLAUDE_PLUGIN_ROOT)"
TOOL_GRANT_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.*-]*)(?:\((.*)\))?")


class FrontmatterError(ValueError):
    """A syntax failure in the shared frontmatter subset."""


class ParsedFrontmatter(NamedTuple):
    fields: dict[str, FrontmatterValue]
    body: str
    raw_lines: tuple[str, ...]
    problems: tuple[str, ...]
    styles: dict[str, str]


# Skills that must carry `disable-model-invocation: true`. Single-sourced here so
# check_links.py (validation) and generate_platform_adapters.py (projection) cannot
# drift; both import this name and keep a module attribute for test compatibility.
MANUAL_ONLY = {"pcf-deploy"}


def decode_scalar(raw: str) -> str:
    """Decode one scalar with the adapter reader's established quote behavior."""
    raw = raw.strip()
    if raw.startswith('"'):
        decoded: str = json.loads(raw)  # a JSON document opening with `"` is a string or an error
        return decoded
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


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


def _source_name(source: str | Path) -> str:
    return source.as_posix() if isinstance(source, Path) else str(source)


def _problem(
    problems: list[str], mode: Mode, source: str, line_number: int | None, message: str
) -> None:
    where = f"{source}:{line_number}" if line_number is not None else source
    rendered = f"{where}: {message}"
    if mode == "strict":
        raise FrontmatterError(rendered)
    problems.append(rendered)


def _scalar(
    raw: str,
    *,
    problems: list[str],
    mode: Mode,
    source: str,
    line_number: int,
) -> tuple[str, str]:
    stripped = raw.strip()
    if stripped.startswith("'") and not stripped.endswith("'"):
        return stripped, "single-quoted-unmatched"
    style = (
        "double-quoted"
        if stripped.startswith('"')
        else "single-quoted"
        if stripped.startswith("'") and stripped.endswith("'")
        else "plain"
    )
    try:
        return decode_scalar(stripped), style
    except (json.JSONDecodeError, TypeError):
        _problem(problems, mode, source, line_number, "invalid quoted scalar")
        return stripped, style


def parse(text: str, source: str | Path, *, mode: Mode = "strict") -> ParsedFrontmatter:
    """Parse frontmatter text in strict (raise) or lenient (collect) mode."""
    if mode not in {"strict", "lenient"}:
        raise ValueError(f"unsupported frontmatter parse mode: {mode!r}")

    source_name = _source_name(source)
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

    fields: dict[str, FrontmatterValue] = {}
    styles: dict[str, str] = {}
    raw_lines = lines[1:end]
    index = 0
    while index < len(raw_lines):
        line = raw_lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = KEY_RE.fullmatch(line)
        if not match:
            _problem(
                problems,
                mode,
                source_name,
                index + 2,
                "unsupported frontmatter syntax",
            )
            index += 1
            continue

        key, raw = match.group(1), (match.group(2) or "")
        duplicate = key in fields
        if duplicate:
            _problem(
                problems,
                mode,
                source_name,
                index + 2,
                f"duplicate frontmatter key {key!r}",
            )

        if raw in BLOCK_MARKERS:
            chunks: list[str] = []
            index += 1
            while index < len(raw_lines) and (
                not raw_lines[index] or raw_lines[index].startswith((" ", "\t"))
            ):
                chunks.append(raw_lines[index].strip())
                index += 1
            value: FrontmatterValue = " ".join(chunk for chunk in chunks if chunk)
            style = "block"
        elif not raw:
            items: list[str] = []
            index += 1
            while index < len(raw_lines):
                item = LIST_ITEM_RE.fullmatch(raw_lines[index])
                if not item:
                    break
                decoded, _item_style = _scalar(
                    item.group(1),
                    problems=problems,
                    mode=mode,
                    source=source_name,
                    line_number=index + 2,
                )
                items.append(decoded)
                index += 1
            value = items
            style = "list"
        else:
            value, style = _scalar(
                raw,
                problems=problems,
                mode=mode,
                source=source_name,
                line_number=index + 2,
            )
            index += 1

        if not duplicate:
            fields[key] = value
            styles[key] = style

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    if text.endswith("\n"):
        body += "\n"
    return ParsedFrontmatter(fields, body, tuple(raw_lines), tuple(problems), styles)


def parse_file(path: Path, *, mode: Mode = "strict") -> ParsedFrontmatter:
    """Read one UTF-8 file and parse it with the shared grammar."""
    return parse(path.read_text(encoding="utf-8"), path, mode=mode)
