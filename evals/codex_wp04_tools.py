"""Bounded literal discovery and character reads over an exact WP04 path map.

These helpers never discover backing filesystem paths or execute commands. Search
offsets count Unicode characters, including original newline characters. Cursors
bind continuation to the selected allowlist names and literal query; they are
pagination state, not authority. The caller records every result independently.
"""

from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any, TextIO

TOOLS = frozenset({"list_files", "read_slice", "search_files"})
SEARCH_CHARS = 2 * 1024 * 1024  # At most 8 MiB of newly searched UTF-8 text.
READ_CHUNK = 65536
SNIPPET_CHARS = 240


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _path(value: Any, *, scope: bool = False) -> str:
    if scope and value == ".":
        return "."
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 4096
        or any(ord(char) < 32 for char in value)
        or any(char in value for char in ("\\", ":"))
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError("path must be a canonical relative allowlist name")
    return value


def _integer(arguments: dict[str, Any], name: str, default: int, low: int, high: int) -> int:
    value = arguments.get(name, default)
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} is outside its integer range")
    return value


def _scope(arguments: dict[str, Any], paths: dict[str, Path]) -> tuple[str, str, list[str]]:
    scope = _path(arguments.get("path", "."), scope=True)
    glob = _path(arguments.get("glob", "*"))
    names = sorted(name for name in paths if scope == "." or name == scope or name.startswith(scope + "/"))
    if scope != "." and not names:
        raise ValueError("path is outside the exact fixture/guidance allowlist")
    for name in names:
        _path(name)
    selected = [
        name for name in names if fnmatch.fnmatchcase(name if scope == "." else name.removeprefix(scope + "/"), glob)
    ]
    return scope, glob, selected


def _target(name: str, paths: dict[str, Path], resolved: dict[str, Path]) -> Path:
    name = _path(name)
    if name not in paths or name not in resolved:
        raise ValueError("path is outside the exact fixture/guidance allowlist")
    target = paths[name]
    if (
        any(part.is_symlink() for part in (target, *target.parents))
        or target.resolve(strict=True) != resolved[name]
        or not target.is_file()
    ):
        raise ValueError("allowlisted path was redirected or is not a regular file")
    return target


def _skip(handle: TextIO, count: int) -> None:
    remaining = count
    while remaining:
        part = handle.read(min(remaining, READ_CHUNK))
        if not part:
            raise ValueError("character offset exceeds the file")
        remaining -= len(part)


def _cursor(query: str, file: int, offset: int) -> str:
    data = _dump({"query": query, "file": file, "offset": offset}).encode("utf-8")
    return base64.urlsafe_b64encode(data).decode("ascii")


def _resume(value: Any, query: str, file_count: int) -> tuple[int, int]:
    if not isinstance(value, str) or len(value) > 1024:
        raise ValueError("invalid search cursor")
    try:
        data = json.loads(base64.b64decode(value, altchars=b"-_", validate=True))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid search cursor") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"query", "file", "offset"}
        or data["query"] != query
        or type(data["file"]) is not int
        or not 0 <= data["file"] < file_count
        or type(data["offset"]) is not int
        or not 0 <= data["offset"] <= 2**63 - 1
    ):
        raise ValueError("cursor does not match this search")
    return data["file"], data["offset"]


def _read(arguments: dict[str, Any], paths: dict[str, Path], resolved: dict[str, Path]) -> dict[str, Any]:
    if set(arguments) - {"path", "offset", "limit"} or "path" not in arguments:
        raise ValueError("read_slice requires path and optional offset/limit")
    path = _path(arguments["path"])
    offset = _integer(arguments, "offset", 0, 0, 2**63 - 1)
    limit = _integer(arguments, "limit", 16000, 1, 64000)
    with _target(path, paths, resolved).open(encoding="utf-8", newline="") as handle:
        _skip(handle, offset)
        content = handle.read(limit)
        eof = not handle.read(1)
    if len(content) > 16000 and len(_dump(content).encode("utf-8")) > 96000:
        # JSON escaping can expand even ASCII control characters sixfold. A
        # smaller honest page preserves the requested character continuation.
        content = content[:16000]
        eof = False
    return {
        "path": path,
        "offset": offset,
        "text": content,
        "eof": eof,
        "next_offset": None if eof else offset + len(content),
    }


def _list(arguments: dict[str, Any], paths: dict[str, Path]) -> dict[str, Any]:
    if set(arguments) - {"path", "glob", "offset", "limit"}:
        raise ValueError("list_files accepts path/glob/offset/limit only")
    _, _, names = _scope(arguments, paths)
    offset = _integer(arguments, "offset", 0, 0, len(names))
    limit = _integer(arguments, "limit", 50, 1, 100)
    # Keep even unusually long admitted names bounded without dropping continuations.
    selected: list[str] = []
    size = 0
    for name in names[offset : offset + limit]:
        size += len(name.encode("utf-8"))
        if selected and size > 32000:
            break
        selected.append(name)
    following = offset + len(selected)
    return {"files": selected, "total": len(names), "next_offset": following if following < len(names) else None}


def _search(arguments: dict[str, Any], paths: dict[str, Path], resolved: dict[str, Path]) -> dict[str, Any]:
    if set(arguments) - {"path", "glob", "pattern", "limit", "cursor"}:
        raise ValueError("search_files accepts path/glob/pattern/limit/cursor only")
    pattern = arguments.get("pattern")
    if not isinstance(pattern, str) or not 1 <= len(pattern) <= 1024:
        raise ValueError("pattern requires 1..1024 literal characters")
    scope, glob, names = _scope(arguments, paths)
    limit = _integer(arguments, "limit", 20, 1, 50)
    query = hashlib.sha256(_dump([scope, glob, pattern, names]).encode("utf-8")).hexdigest()
    file, offset = _resume(arguments["cursor"], query, len(names)) if "cursor" in arguments else (0, 0)
    matches: list[dict[str, Any]] = []
    scanned = 0
    result_bytes = 0

    def result(complete: bool) -> dict[str, Any]:
        return {
            "matches": matches,
            "complete": complete,
            "next_cursor": None if complete else _cursor(query, file, offset),
            "scanned_characters": scanned,
            "files_total": len(names),
            "match_kind": "case-sensitive literal occurrences; offsets count Unicode characters",
        }

    while file < len(names):
        remaining = SEARCH_CHARS - scanned
        if not remaining:
            return result(False)
        name = names[file]
        with _target(name, paths, resolved).open(encoding="utf-8", newline="") as handle:
            _skip(handle, offset)
            # Lookahead retains matches whose start precedes a page boundary. It is
            # not counted twice or exposed as a claim of scanning the next page.
            content = handle.read(remaining + len(pattern) - 1)
            eof = not handle.read(1)
        span = min(remaining, len(content))
        position = 0
        while (position := content.find(pattern, position)) >= 0 and position < span:
            snippet_start = max(0, position - 60)
            match = {
                "path": name,
                "offset": offset + position,
                "match_characters": len(pattern),
                "excerpt_offset": offset + snippet_start,
                "text": content[snippet_start : snippet_start + SNIPPET_CHARS],
            }
            match_bytes = len(_dump(match).encode("utf-8"))
            if matches and result_bytes + match_bytes > 48000:
                scanned += min(position, span)
                offset += position  # This match was not returned; include it next.
                return result(False)
            matches.append(match)
            result_bytes += match_bytes
            position += 1  # Preserve overlapping literal matches on continuation.
            if len(matches) == limit:
                scanned += min(position, span)
                offset += position
                return result(False)
        scanned += span
        if eof:
            file += 1
            offset = 0
        else:
            offset += span
    return result(True)


def call_tool(name: str, arguments: dict[str, Any], paths: dict[str, Path], resolved: dict[str, Path]) -> str:
    """Return one JSON-text page; the caller records errors and tool receipts."""
    if not isinstance(arguments, dict):
        raise ValueError("tool arguments must be an object")
    if name == "list_files":
        return _dump(_list(arguments, paths))
    if name == "read_slice":
        return _dump(_read(arguments, paths, resolved))
    if name == "search_files":
        return _dump(_search(arguments, paths, resolved))
    raise ValueError("tool is outside the WP04 read-only profile")


def tool_definitions() -> list[dict[str, Any]]:
    """MCP schemas for literal, bounded navigation; no backing paths are disclosed."""
    path = {
        "type": "string",
        "description": "Exact relative allowlist path or directory prefix; '.' selects all admitted names.",
    }
    glob = {
        "type": "string",
        "description": "Optional glob over relative allowlist names; default '*'. No filesystem globbing.",
    }
    definitions = [
        (
            "list_files",
            "List admitted fixture/guidance names in sorted order. Follow next_offset; unlisted files are inaccessible.",
            {
                "path": path,
                "glob": glob,
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            [],
        ),
        (
            "read_slice",
            "Read exact UTF-8 text using Unicode-character offset (default0) and limit (default16000). Follow next_offset until eof; no line-number decoration or newline conversion.",
            {
                "path": {"type": "string"},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 64000},
            },
            ["path"],
        ),
        (
            "search_files",
            "Case-sensitive literal search over admitted files only; no regex. Returns bounded snippets and character offsets for read_slice. Follow next_cursor until complete, including empty partial pages. Keep path/glob/pattern unchanged on continuation.",
            {
                "path": path,
                "glob": glob,
                "pattern": {"type": "string", "minLength": 1, "maxLength": 1024},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "cursor": {"type": "string"},
            },
            ["pattern"],
        ),
    ]
    return [
        {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        }
        for name, description, properties, required in definitions
    ]
