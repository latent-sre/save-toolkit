"""Read-only WP04 file navigation controls; no model or external service calls."""

import json

import codex_wp04_tools as tools
import pytest


def fixture(tmp_path, files):
    paths = {}
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="")
        paths[name] = path
    resolved = {name: path.resolve() for name, path in paths.items()}

    def call(name, **arguments):
        return json.loads(tools.call_tool(name, arguments, paths, resolved))

    return call, paths, resolved


def test_catalog_pagination_keeps_all_uids_and_uses_only_declared_names(tmp_path):
    call, _, _ = fixture(
        tmp_path,
        {
            "observations/events/old.json": '{"name":"stress","uid":"old"}',
            "observations/events/new.json": '{"name":"stress","uid":"new"}',
            "guidance/skills/root-cause/SKILL.md": "method",
        },
    )
    (tmp_path / "unlisted.txt").write_text("not admitted", encoding="utf-8")
    first = call("list_files", path="observations", glob="*.json", limit=1)
    second = call("list_files", path="observations", glob="*.json", offset=first["next_offset"], limit=1)
    assert first["files"] == ["observations/events/new.json"]
    assert second["files"] == ["observations/events/old.json"]
    assert first["total"] == second["total"] == 2
    assert second["next_offset"] is None
    assert "unlisted.txt" not in call("list_files")["files"]
    matches = call("search_files", path="observations/events", pattern="stress")
    assert [row["path"] for row in matches["matches"]] == first["files"] + second["files"]
    assert matches["complete"]


def test_character_reads_cover_large_unicode_source_without_newline_conversion(tmp_path):
    source = "\u03b1\r\n" * 50000 + "END🌍"
    call, paths, _ = fixture(tmp_path, {"logs.tsv": source})
    before = paths["logs.tsv"].read_bytes()
    offset = 0
    parts = []
    while True:
        page = call("read_slice", path="logs.tsv", offset=offset, limit=64000)
        assert page["offset"] == offset
        assert len(page["text"]) <= 64000
        parts.append(page["text"])
        if page["eof"]:
            assert page["next_offset"] is None
            break
        assert page["next_offset"] > offset
        offset = page["next_offset"]
    assert "".join(parts) == source
    assert paths["logs.tsv"].read_bytes() == before
    assert call("read_slice", path="logs.tsv", offset=len(source))["text"] == ""
    with pytest.raises(ValueError):
        call("read_slice", path="logs.tsv", offset=len(source) + 1)


def test_sparse_search_pages_make_progress_and_keep_boundary_unicode_matches(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "SEARCH_CHARS", 7)
    source = "01234567890123456789🌍needle" + "x" * 20 + "🌍needle"
    call, _, _ = fixture(tmp_path, {"logs.txt": source})
    arguments = {"path": "logs.txt", "pattern": "🌍needle"}
    matches, cursors, empty_partial = [], set(), False
    for _ in range(20):
        page = call("search_files", **arguments)
        assert page["scanned_characters"] <= 7
        matches.extend(page["matches"])
        if page["complete"]:
            assert page["next_cursor"] is None
            break
        empty_partial |= not page["matches"]
        assert page["next_cursor"] not in cursors
        cursors.add(page["next_cursor"])
        arguments["cursor"] = page["next_cursor"]
    else:
        pytest.fail("bounded search failed to advance to completion")
    assert empty_partial
    assert [m["offset"] for m in matches] == [20, 47]
    for match in matches:
        assert call("read_slice", path=match["path"], offset=match["offset"], limit=7)["text"] == "🌍needle"


def test_search_continuation_keeps_overlapping_matches_and_next_file(tmp_path):
    call, _, _ = fixture(tmp_path, {"a.txt": "aaaa", "b.txt": "aa"})
    args = {"pattern": "aa", "limit": 1}
    seen = []
    for _ in range(8):
        page = call("search_files", **args)
        seen.extend((m["path"], m["offset"]) for m in page["matches"])
        if page["complete"]:
            break
        args["cursor"] = page["next_cursor"]
    assert seen == [("a.txt", 0), ("a.txt", 1), ("a.txt", 2), ("b.txt", 0)]
    assert page["complete"]


def test_long_line_search_gives_readable_locator_and_bounded_snippet(tmp_path):
    source = "x" * 180000 + "needle" + "z" * 180000
    call, _, _ = fixture(tmp_path, {"objects.jsonl": source})
    page = call("search_files", pattern="needle")
    assert page["complete"]
    assert len(page["matches"]) == 1
    match = page["matches"][0]
    assert match["offset"] == 180000
    assert len(match["text"]) <= 240
    assert call("read_slice", path=match["path"], offset=match["offset"], limit=6)["text"] == "needle"
    assert str(tmp_path) not in json.dumps(page)


def test_cursor_cannot_silently_change_query_scope(tmp_path):
    call, _, _ = fixture(tmp_path, {"a.txt": "needle needle", "b.txt": "needle"})
    page = call("search_files", pattern="needle", limit=1)
    for changes in ({"pattern": "other"}, {"path": "b.txt"}, {"glob": "b*"}):
        args = {"pattern": "needle", "limit": 1, "cursor": page["next_cursor"], **changes}
        with pytest.raises(ValueError):
            call("search_files", **args)
    for cursor in ("bad", "{}", "null", True, 12):
        with pytest.raises(ValueError):
            call("search_files", pattern="needle", cursor=cursor)


@pytest.mark.parametrize("path", ["/etc/passwd", "../outside", "a/../a.txt", "./a.txt", "a//b", "C:/data", "a\\b", ""])
@pytest.mark.parametrize("tool", ["list_files", "search_files", "read_slice"])
def test_external_or_noncanonical_paths_are_rejected(tmp_path, path, tool):
    call, _, _ = fixture(tmp_path, {"a.txt": "needle"})
    args = {"path": path}
    if tool == "search_files":
        args["pattern"] = "needle"
    with pytest.raises(ValueError):
        call(tool, **args)


@pytest.mark.parametrize(
    "tool,args",
    [
        ("list_files", {"offset": True}),
        ("list_files", {"limit": 101}),
        ("list_files", {"glob": "../*"}),
        ("list_files", {"glob": "/tmp/*"}),
        ("read_slice", {"path": "a.txt", "limit": 64001}),
        ("read_slice", {"path": "a.txt", "offset": -1}),
        ("read_slice", {"path": "a.txt", "offset": False}),
        ("search_files", {"pattern": ""}),
        ("search_files", {"pattern": "needle", "limit": 0}),
        ("search_files", {"pattern": "needle", "limit": True}),
        ("search_files", {"pattern": "needle", "regex": True}),
        ("write_file", {"path": "a.txt", "content": "changed"}),
    ],
)
def test_invalid_arguments_and_write_attempts_fail_closed(tmp_path, tool, args):
    call, paths, _ = fixture(tmp_path, {"a.txt": "needle"})
    with pytest.raises(ValueError):
        call(tool, **args)
    assert paths["a.txt"].read_text() == "needle"


@pytest.mark.parametrize("directory_redirect", [False, True])
def test_symlink_or_parent_redirection_is_rejected_before_read(tmp_path, directory_redirect):
    call, paths, _ = fixture(tmp_path, {"data/a.txt": "admitted"})
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "a.txt").write_text("outside value")
    if directory_redirect:
        paths["data/a.txt"].unlink()
        (tmp_path / "data").rmdir()
        target, link = outside, tmp_path / "data"
    else:
        paths["data/a.txt"].unlink()
        target, link = outside / "a.txt", paths["data/a.txt"]
    try:
        link.symlink_to(target, target_is_directory=directory_redirect)
    except OSError, NotImplementedError:
        pytest.skip("host cannot create symlinks")
    for tool, args in [("read_slice", {"path": "data/a.txt"}), ("search_files", {"pattern": "outside"})]:
        with pytest.raises(ValueError):
            call(tool, **args)


def test_literal_pattern_does_not_gain_regex_or_command_meaning(tmp_path):
    call, _, _ = fixture(tmp_path, {"data.txt": "literal $(no-command) [a-z]+\nordinary abc"})
    matches = call("search_files", pattern="[a-z]+")
    assert len(matches["matches"]) == 1
    assert matches["matches"][0]["offset"] == 22
    assert call("search_files", pattern="$(no-command)")["matches"][0]["offset"] == 8


def test_tool_schemas_advertise_only_the_three_readonly_tools():
    schemas = tools.tool_definitions()
    assert {schema["name"] for schema in schemas} == {"list_files", "read_slice", "search_files"}
    assert all(schema["inputSchema"]["additionalProperties"] is False for schema in schemas)


def test_search_response_budget_returns_continuation_before_large_names_overflow(tmp_path):
    target = tmp_path / "source.txt"
    target.write_text("needle", encoding="utf-8")
    names = ["segment/" * 250 + f"{index:02d}.txt" for index in range(50)]
    paths = {name: target for name in names}
    resolved = {name: target.resolve() for name in names}
    args = {"pattern": "needle", "limit": 50}
    found = []
    for _ in range(5):
        raw = tools.call_tool("search_files", args, paths, resolved)
        assert len(raw.encode("utf-8")) <= 65536
        result = json.loads(raw)
        found.extend(item["path"] for item in result["matches"])
        if result["complete"]:
            break
        args["cursor"] = result["next_cursor"]
    assert found == names


def test_read_response_budget_preserves_control_characters_through_continuation(tmp_path):
    source = "\x00" * 64000
    call, paths, resolved = fixture(tmp_path, {"data.txt": source})
    raw = tools.call_tool("read_slice", {"path": "data.txt", "limit": 64000}, paths, resolved)
    assert len(raw.encode("utf-8")) <= 131072
    first = json.loads(raw)
    assert first["text"] == source[: first["next_offset"]]
    assert not first["eof"]
    remaining = call("read_slice", path="data.txt", offset=first["next_offset"], limit=64000)
    assert remaining["text"] == source[first["next_offset"] : first["next_offset"] + len(remaining["text"])]
    assert call("read_slice", path="data.txt", offset=48000, limit=64000)["eof"]
