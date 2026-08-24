#!/usr/bin/env python3
"""Parse the deliberately small frontmatter grammar shared by fleet tooling."""

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


class FrontmatterError(ValueError):
    """A syntax failure in the shared frontmatter subset."""


class ParsedFrontmatter(NamedTuple):
    fields: dict[str, FrontmatterValue]
    body: str
    raw_lines: tuple[str, ...]
    problems: tuple[str, ...]
    styles: dict[str, str]


def decode_scalar(raw: str) -> str:
    """Decode one scalar with the adapter reader's established quote behavior."""
    raw = raw.strip()
    if raw.startswith('"'):
        return json.loads(raw)
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1].replace("''", "'")
    return raw


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
