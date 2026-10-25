"""Discover tests, native cases and campaign guides; export selections without executing them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Never

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        self.exit(3, f"catalog: {message}\n")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read(path: Path) -> Any:
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError(f"oversized JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_pairs)


def checked_path(root: Path, relative: str, *, test: bool = False) -> Path:
    """Manifest paths are portable file names, never commands, globs or node selectors."""
    path = PurePosixPath(relative)
    if (
        not relative
        or "\\" in relative
        or ":" in relative
        or path.is_absolute()
        or any(part in {".", ".."} for part in relative.split("/"))
    ):
        raise ValueError(f"unsafe repository path: {relative!r}")
    if test and (
        len(path.parts) != 2
        or path.parts[0] not in {"scripts", "evals"}
        or not path.name.startswith("test_")
        or path.suffix != ".py"
    ):
        raise ValueError(f"expected a repository test file: {relative!r}")
    target = root.joinpath(*path.parts)
    if (
        any(root.joinpath(*path.parts[:i]).is_symlink() for i in range(1, len(path.parts) + 1))
        or not target.resolve().is_relative_to(root.resolve())
        or not target.is_file()
    ):
        raise ValueError(f"missing or linked repository file: {relative!r}")
    return target


def _strings(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f"{field} must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"duplicate member in {field}")
    return value


def load_suites(root: Path) -> dict[str, dict[str, Any]]:
    """Validate structure and tests without importing the native runner or benchmark SDKs."""
    result: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "evals/suites").glob("*.json")):
        checked_path(root, path.relative_to(root).as_posix())
        suite = _read(path)
        if (
            not isinstance(suite, dict)
            or set(suite) != {"schema_version", "id", "summary", "tests", "native_scenarios", "campaigns", "guides"}
            or type(suite["schema_version"]) is not int
            or suite["schema_version"] != 1
            or suite["id"] != path.stem
            or not SLUG.fullmatch(path.stem)
            or not isinstance(suite["summary"], str)
            or not suite["summary"].strip()
        ):
            raise ValueError(f"invalid suite schema: {path.name}")
        for relative in _strings(suite["tests"], "tests"):
            checked_path(root, relative, test=True)
        for name in _strings(suite["native_scenarios"], "native_scenarios"):
            if not SLUG.fullmatch(name):
                raise ValueError(f"invalid scenario id: {name!r}")
        _strings(suite["guides"], "guides")
        if not isinstance(suite["campaigns"], list):
            raise ValueError("campaigns must be a list")
        campaign_ids: set[str] = set()
        for campaign in suite["campaigns"]:
            if (
                not isinstance(campaign, dict)
                or set(campaign) != {"id", "entrypoint", "selection", "guide"}
                or any(not isinstance(x, str) or not x for x in campaign.values())
                or not SLUG.fullmatch(campaign["id"])
                or campaign["id"] in campaign_ids
            ):
                raise ValueError(f"invalid or duplicate campaign in {path.name}")
            campaign_ids.add(campaign["id"])
        if not any(suite[field] for field in ("tests", "native_scenarios", "campaigns")):
            raise ValueError(f"empty suite: {path.stem}")
        result[path.stem] = suite
    return result


def choose(suites: dict[str, dict[str, Any]], names: list[str]) -> dict[str, dict[str, Any]]:
    unknown = set(names) - suites.keys()
    if unknown:
        raise ValueError(f"unknown suite(s): {', '.join(sorted(unknown))}")
    return {name: suites[name] for name in sorted(set(names))} if names else suites


def test_rows(root: Path, suites: dict[str, dict[str, Any]], *, selected: bool) -> list[dict[str, Any]]:
    members: dict[str, list[str]] = {}
    for name, suite in suites.items():
        for path in suite["tests"]:
            members.setdefault(path, []).append(name)
    paths = (
        sorted(members)
        if selected
        else sorted(
            path.relative_to(root).as_posix()
            for folder in ("scripts", "evals")
            for path in (root / folder).glob("test_*.py")
        )
    )
    return [{"path": path, "selected_by": sorted(members.get(path, []))} for path in paths]


def native_inventory() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    from probe import catalog as native  # noqa: PLC0415 -- test lookup is standard-library-only
    from probe import constants  # noqa: PLC0415 -- only native discovery needs these paths

    specs = native.load_all_scenarios()
    paths = {
        native.load_scenario(path)["id"]: path.relative_to(ROOT).as_posix()
        for directory in (constants.SCENARIO_DIR, constants.CONTRACT_SCENARIO_DIR)
        for path in directory.glob("*.yaml")
    }
    rows = []
    for spec in sorted(specs, key=lambda value: value["id"]):
        target = spec.get("target", {})
        component = (
            f"agent:{spec['agent']}"
            if spec.get("agent")
            else f"skill:{spec['skill']}"
            if spec.get("skill")
            else f"{target['kind']}:{target['name']}"
        )
        conversation = spec.get("conversation", {})
        rows.append(
            {
                "id": spec["id"],
                "path": paths[spec["id"]],
                "kind": native.scenario_kind(spec),
                "component": component,
                "routing_expectation": spec.get("routing", {}).get("expect"),
                "profile": conversation.get("profile"),
                "partition": conversation.get("partition"),
                "manual_review": conversation.get("manual_review"),
                "max_turns": spec["max_turns"],
            }
        )
    return rows, {spec["id"]: spec for spec in specs}


def campaign_rows(root: Path, suites: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name, suite in suites.items():
        for campaign in suite["campaigns"]:
            for field in ("entrypoint", "selection", "guide"):
                checked_path(root, campaign[field])
            row = result.setdefault(campaign["id"], {**campaign, "selected_by": []})
            if any(row[key] != value for key, value in campaign.items()):
                raise ValueError(f"conflicting campaign reference: {campaign['id']}")
            row["selected_by"].append(name)
    return [result[name] for name in sorted(result)]


def validate_references(root: Path, suites: dict[str, dict[str, Any]], specs: dict[str, Any]) -> None:
    for name, suite in suites.items():
        unknown = set(suite["native_scenarios"]) - specs.keys()
        if unknown:
            raise ValueError(f"suite {name}: missing native scenarios: {', '.join(sorted(unknown))}")
        for guide in suite["guides"]:
            checked_path(root, guide)
    campaign_rows(root, suites)


def load_tracks(root: Path, suites: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Index existing entrypoints and plans without importing or activating any of them."""
    data = _read(checked_path(root, "evals/tracks.json"))
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "tracks"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or not isinstance(data["tracks"], list)
    ):
        raise ValueError("invalid track index schema")
    seen: set[str] = set()
    for track in data["tracks"]:
        if (
            not isinstance(track, dict)
            or set(track) != {"id", "summary", "kind", "implementation", "entrypoints", "suites", "guides"}
            or not isinstance(track["id"], str)
            or not SLUG.fullmatch(track["id"])
            or track["id"] in seen
            or not isinstance(track["summary"], str)
            or not track["summary"].strip()
            or track["kind"] not in ("runner", "benchmark", "tooling", "sandbox", "judge", "proposal")
            or track["implementation"] not in ("present", "planned", "proposal")
        ):
            raise ValueError("invalid or duplicate track")
        seen.add(track["id"])
        entrypoints = _strings(track["entrypoints"], "entrypoints")
        if bool(entrypoints) != (track["implementation"] == "present"):
            raise ValueError(f"track {track['id']}: only present implementations have entrypoints")
        guides = _strings(track["guides"], "guides")
        if not guides:
            raise ValueError(f"track {track['id']} needs a source guide")
        for path in [*entrypoints, *guides]:
            checked_path(root, path)
        unknown = set(_strings(track["suites"], "suites")) - suites.keys()
        if unknown:
            raise ValueError(f"track {track['id']}: unknown suites: {', '.join(sorted(unknown))}")
    return sorted(data["tracks"], key=lambda row: row["id"])


def coverage(
    root: Path,
    suites: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    specs: dict[str, dict[str, Any]],
    tracks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Membership and declared checks are inventory, never a model-performance score."""
    tests = test_rows(root, suites, selected=False)
    assigned = {name for suite in suites.values() for name in suite["native_scenarios"]}
    by_id = {row["id"]: row for row in rows}
    items = []
    for name, suite in suites.items():
        selected = [by_id[case] for case in suite["native_scenarios"]]
        selected_specs = [specs[case] for case in suite["native_scenarios"]]
        checks = [check for spec in selected_specs for check in spec.get("checks", [])]
        graders = {grader["type"] for spec in selected_specs for grader in spec.get("graders", [])}
        for spec in selected_specs:
            for turn in spec.get("conversation", {}).get("turn_graders", []):
                graders.update(grader["type"] for grader in turn)
        graders.update(check["name"] for check in checks if check.get("check") == "fleet_grader")
        items.append(
            {
                "id": name,
                "summary": suite["summary"],
                "native_cases": len(selected),
                "test_files": len(suite["tests"]),
                "kinds": dict(Counter(row["kind"] for row in selected)),
                "components": sorted({row["component"] for row in selected}),
                "profiles": sorted({row["profile"] for row in selected if row["profile"]}),
                "check_types": sorted({check["check"] for check in checks}),
                "grader_types": sorted(graders),
                "declared_manual_review_cases": sum(row["manual_review"] is not None for row in selected),
                "tracks": [track["id"] for track in tracks if name in track["suites"]],
                "campaigns": [campaign["id"] for campaign in suite["campaigns"]],
                "guides": suite["guides"],
            }
        )
    return {
        "schema_version": 1,
        "view": "coverage",
        "meaning": "Inventory membership and declared checks; not measured model quality or candidate acceptance.",
        "summary": {
            "native_cases": len(specs),
            "assigned_native_cases": len(assigned),
            "test_files": len(tests),
            "assigned_test_files": sum(bool(row["selected_by"]) for row in tests),
            "unassigned_native_cases": sorted(specs.keys() - assigned),
            "unassigned_test_files": [row["path"] for row in tests if not row["selected_by"]],
            "tracks": len(tracks),
        },
        "items": items,
    }


def _git(*arguments: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8", timeout=15
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def export_selection(args: argparse.Namespace, suites: dict[str, dict[str, Any]]) -> dict[str, Any]:
    from probe import fingerprints  # noqa: PLC0415 -- only export needs identities

    if not 1 <= args.trials <= 10000:
        raise ValueError("trials must be 1..10000")
    if any(suite["campaigns"] for suite in suites.values()):
        raise ValueError("linked external campaigns require their adapter guide, not native export")
    empty = [name for name, suite in suites.items() if not suite["native_scenarios"]]
    if empty:
        raise ValueError(f"suite(s) have no native cases: {', '.join(empty)}")
    rows, specs = native_inventory()
    validate_references(ROOT, suites, specs)
    names = sorted(set(args.scenario or [case for suite in suites.values() for case in suite["native_scenarios"]]))
    if not names or set(names) - specs.keys():
        raise ValueError("selection requires nonempty existing native scenario IDs")
    status = _git("status", "--porcelain")
    data = {
        "schema_version": 1,
        "profile": "native-selection-v1",
        "trials": args.trials,
        "tasks": [{"instance_id": name, "case_sha256": fingerprints.case_digest(specs[name])} for name in names],
        "source": {
            "git_revision": _git("rev-parse", "HEAD"),
            "dirty": None if status is None else bool(status),
            "suites": [
                {
                    "id": name,
                    "sha256": hashlib.sha256((ROOT / "evals/suites" / f"{name}.json").read_bytes()).hexdigest(),
                }
                for name in suites
            ],
        },
    }
    target = args.out.absolute()
    if ".." in args.out.parts or any(path.is_symlink() for path in (target, *target.parents)):
        raise ValueError("selection output cannot traverse symlinks or '..'")
    encoded = (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(encoded)
    return {
        "path": str(target),
        "selection_file_sha256": hashlib.sha256(encoded).hexdigest(),
        "trials": args.trials,
        "cases": len(names),
        "slots": len(names) * args.trials,
        "items": [row for row in rows if row["id"] in names],
    }


def parser() -> argparse.ArgumentParser:
    result = Parser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("suites", "list", "show", "tests", "campaigns", "tracks", "coverage", "check", "select"):
        command = commands.add_parser(name)
        command.add_argument("--json", action="store_true", help="versioned machine-readable output")
        if name == "select":
            group = command.add_mutually_exclusive_group(required=True)
            group.add_argument("--suite", action="append", default=[])
            group.add_argument("--scenario", action="append", default=[])
            command.add_argument("--trials", type=int, required=True)
            command.add_argument("--out", type=Path, required=True)
        elif name not in {"check", "coverage"}:
            command.add_argument("--suite", action="append", default=[], required=name == "show")
        if name == "list":
            for flag in ("kind", "component", "profile"):
                command.add_argument(f"--{flag}", action="append", default=[])
    return result


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    suites = load_suites(ROOT)
    chosen = choose(suites, getattr(args, "suite", []))
    view = args.command
    if view == "select":
        return {"schema_version": 1, "view": view, **export_selection(args, chosen if args.suite else {})}
    if view in {"suites", "show"}:
        items = list(chosen.values())
    elif view == "tests":
        items = test_rows(ROOT, chosen, selected=bool(args.suite))
    elif view == "campaigns":
        items = campaign_rows(ROOT, chosen)
    elif view == "tracks":
        items = [track for track in load_tracks(ROOT, suites) if not args.suite or set(track["suites"]) & chosen.keys()]
    else:
        rows, specs = native_inventory()
        validate_references(ROOT, suites, specs)
        if view == "check":
            tracks = load_tracks(ROOT, suites)
            items = [{"suites": len(suites), "native_cases": len(specs), "tracks": len(tracks), "status": "valid"}]
        elif view == "coverage":
            return coverage(ROOT, suites, rows, specs, load_tracks(ROOT, suites))
        else:
            for row in rows:
                row["selected_by"] = [name for name, suite in suites.items() if row["id"] in suite["native_scenarios"]]
            for key in ("kind", "component", "profile"):
                requested = getattr(args, key)
                valid = {row[key] for row in rows} - {None}
                if set(requested) - valid:
                    raise ValueError(f"unknown {key}: {', '.join(sorted(set(requested) - valid))}")
            items = [
                row
                for row in rows
                if (not args.suite or set(row["selected_by"]) & chosen.keys())
                and all(
                    not getattr(args, key) or row[key] in getattr(args, key) for key in ("kind", "component", "profile")
                )
            ]
    return {"schema_version": 1, "view": view, "items": items}


def render(envelope: dict[str, Any]) -> str:
    view = envelope["view"]
    if view in {"show", "check", "select"}:
        return json.dumps(envelope, indent=2, ensure_ascii=False)
    if view == "coverage":
        summary = envelope["summary"]
        lines = [
            envelope["meaning"],
            f"Native cases assigned: {summary['assigned_native_cases']}/{summary['native_cases']}; "
            f"test files assigned: {summary['assigned_test_files']}/{summary['test_files']}",
            "suite\tnative cases\ttest files\tdeclared kinds",
        ]
        for row in envelope["items"]:
            kinds = ", ".join(f"{key}:{value}" for key, value in sorted(row["kinds"].items())) or "none"
            lines.append(f"{row['id']}\t{row['native_cases']}\t{row['test_files']}\t{kinds}")
        for key in ("unassigned_native_cases", "unassigned_test_files"):
            if summary[key]:
                lines.append(f"{key}: {', '.join(summary[key])}")
        return "\n".join(lines)
    fields = {
        "list": ("id", "kind", "component", "profile", "partition", "manual_review", "selected_by"),
        "tests": ("path", "selected_by"),
        "suites": ("id", "summary"),
        "campaigns": ("id", "entrypoint", "selection", "guide"),
        "tracks": ("id", "kind", "implementation", "entrypoints", "summary"),
    }[view]
    lines = ["\t".join(fields)]
    for row in envelope["items"]:
        lines.append(
            "\t".join(
                ",".join(row[field]) if isinstance(row.get(field), list) else str(row.get(field) or "unknown")
                for field in fields
            )
        )
    lines.append(f"{len(envelope['items'])} {'test files (not collected tests)' if view == 'tests' else 'matches'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        envelope = dispatch(args)
    except (OSError, ValueError) as exc:
        print(f"catalog: {exc}", file=sys.stderr)
        return 3
    print(json.dumps(envelope, ensure_ascii=False, allow_nan=False) if args.json else render(envelope))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
