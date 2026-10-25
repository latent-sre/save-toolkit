#!/usr/bin/env python3
"""Prepare/review WP04 snapshots without running a candidate, service or judge."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from itbench_adapter import (
    assess_local,
    build_bindings,
    collect_submission,
    export_submission,
    fetch_sources,
    prepare_ground_truth,
    prepare_native,
    stage_case,
    validate_manifest,
)

DEFAULT_MANIFEST = Path(__file__).resolve().parent / "manifests" / "wp04-itbench-five.json"


def _object(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = yaml.safe_load(stream) if path.suffix in {".yaml", ".yml"} else json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def _write(path: Path, result: Mapping[str, Any] | list[dict[str, Any]]) -> None:
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError("symlink in output path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "fetch", "stage", "prepare-native", "prepare-judge-input", "rebuild-bindings"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
        if name in {"fetch", "stage", "prepare-native", "prepare-judge-input", "rebuild-bindings"}:
            command.add_argument("--source", type=Path, required=True)
        if name == "fetch":
            command.add_argument(
                "--include-hidden", action="store_true", help="evaluator cache only; never a candidate input"
            )
        if name == "prepare-judge-input":
            command.add_argument("--output", type=Path, required=True)
            command.add_argument("--receipt", type=Path, required=True)
        if name == "rebuild-bindings":
            command.add_argument("--output", type=Path, required=True)
        if name in {"stage", "prepare-native"}:
            if name == "stage":
                command.add_argument("--case", required=True)
            else:
                command.add_argument("--max-prepared-bytes", type=int, default=512 * 1024 * 1024)
            command.add_argument("--destination", type=Path, required=True)
            command.add_argument("--receipt", type=Path, required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--response", type=Path, required=True)
    collect.add_argument("--case", required=True)
    collect.add_argument("--output", type=Path, required=True)
    for name in ("export", "assess"):
        command = commands.add_parser(name)
        command.add_argument("--submission", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True)
        if name == "assess":
            command.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
            command.add_argument("--bindings", type=Path, required=True)
            command.add_argument("--ground-truth", type=Path, required=True)
            command.add_argument("--upstream-result", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            result = collect_submission(args.response.read_text(encoding="utf-8"), args.case)
            _write(args.output, result)
        elif args.command in {
            "validate",
            "fetch",
            "stage",
            "prepare-native",
            "prepare-judge-input",
            "rebuild-bindings",
        }:
            manifest = _object(args.manifest)
            validate_manifest(manifest)
            if args.command == "validate":
                result = {"valid": True, "cases": len(manifest["cases"]), "admission": "human-review-pending"}
            elif args.command == "fetch":
                result = fetch_sources(manifest, args.source, include_hidden=args.include_hidden)
            elif args.command == "rebuild-bindings":
                result = build_bindings(manifest, args.source)
                _write(args.output, result)
            elif args.command == "prepare-judge-input":
                if args.output.exists() or args.receipt.exists():
                    raise ValueError("judge input or receipt already exists")
                result = prepare_ground_truth(manifest, args.source)
                _write(args.output, result["ground_truths"])
                _write(args.receipt, result["receipt"])
            else:
                if args.receipt.resolve().is_relative_to(args.destination.resolve()):
                    raise ValueError("receipt must remain outside the candidate workspace")
                if args.receipt.exists():
                    raise ValueError("receipt already exists")
                if args.command == "prepare-native":
                    result = prepare_native(
                        manifest, args.source, args.destination, max_prepared_bytes=args.max_prepared_bytes
                    )
                else:
                    result = stage_case(manifest, args.case, args.source, args.destination)
                _write(args.receipt, result)
        else:
            submission = _object(args.submission)
            if args.command == "export":
                result = export_submission(submission)
            else:
                manifest = _object(args.manifest)
                validate_manifest(manifest)
                case = next((c for c in manifest["cases"] if c["id"] == submission.get("case_id")), None)
                if case is None:
                    raise ValueError("submission case not selected")
                gt_digest = hashlib.sha256(args.ground_truth.read_bytes()).hexdigest()
                if gt_digest != case["hidden"][0]["sha256"]:
                    raise ValueError("ground truth differs from selected case")
                bindings = _object(args.bindings)
                case_bindings = (
                    bindings.get("cases", {}).get(submission.get("case_id")) if "cases" in bindings else bindings
                )
                if not isinstance(case_bindings, dict):
                    raise ValueError("no evaluator bindings for submitted case")
                result = assess_local(
                    submission,
                    case_bindings,
                    _object(args.ground_truth),
                    _object(args.upstream_result) if args.upstream_result else None,
                )
            _write(args.output, result)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        print(f"WP04 refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
