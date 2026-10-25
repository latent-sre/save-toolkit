"""Owner-started WP-08 task selection, smoke and static-repair trials."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any

from swebench_adapter.artifacts import screen, store_json
from swebench_adapter.complex_selection import REVISION as COMPLEX_REVISION
from swebench_adapter.complex_selection import propose
from swebench_adapter.configuration import binding, dependency_problems, load_config, selection_committed, smoke_problem
from swebench_adapter.selection import resolve_task, select_tasks


def read_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError("required input file is missing")
    if path.stat().st_size > 512 * 1024 * 1024:
        raise ValueError("input file exceeds the 512 MiB bound")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def _dataset(path: Path, revision: str) -> list[dict[str, Any]]:
    data = read_object(path)
    if data.get("dataset") != "SWE-bench/SWE-bench_Verified" or data.get("revision") != revision:
        raise ValueError("dataset cache differs from the pinned dataset/revision")
    rows = data.get("rows")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("dataset cache must contain full JSON rows")
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select", help="freeze the deterministic task selection; no model calls")
    select.add_argument("--revision", required=True)
    select.add_argument("--licences", type=Path, required=True)
    select.add_argument("--dataset", type=Path, required=True, help="pinned full-row cache; fetched if absent")
    select.add_argument("--out", type=Path, required=True)
    complex_case = commands.add_parser("propose-complex", help="prepare the separate hard-case proposal; no calls")
    complex_case.add_argument("--licences", type=Path, required=True)
    complex_case.add_argument("--dataset", type=Path, required=True)
    complex_case.add_argument("--out", type=Path, required=True)
    for name in ("preflight", "smoke", "trial", "batch"):
        command = commands.add_parser(name)
        command.add_argument("--selection", type=Path, required=True)
        command.add_argument("--dataset", type=Path, required=True)
        command.add_argument("--config", type=Path, required=True)
        if name != "preflight":
            command.add_argument("--out", type=Path, required=True)
        if name in {"trial", "batch"}:
            command.add_argument("--smoke-receipt", type=Path, required=True)
            command.add_argument("--key-file", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "propose-complex":
            rows = _dataset(args.dataset, COMPLEX_REVISION)
            manifest = propose(rows, read_object(args.licences))
            store_json(args.out.parent, args.out.name, manifest)
            print(json.dumps({"selection": str(args.out), "admission": manifest["admission"], "tasks": 10}))
            return 0
        if args.command == "select":
            if not args.dataset.exists():
                # The approved swebench evaluation environment supplies datasets transitively.
                try:
                    datasets = importlib.import_module("datasets")
                except ImportError as exc:
                    raise ValueError("install requirements-swebench.txt to fetch the pinned dataset") from exc
                rows = list(datasets.load_dataset("SWE-bench/SWE-bench_Verified", revision=args.revision, split="test"))
                store_json(
                    args.dataset.parent,
                    args.dataset.name,
                    {"dataset": "SWE-bench/SWE-bench_Verified", "revision": args.revision, "rows": rows},
                )
            rows = _dataset(args.dataset, args.revision)
            manifest = select_tasks(rows, args.revision, read_object(args.licences))
            store_json(args.out.parent, args.out.name, manifest)
            print(
                json.dumps(
                    {"selection": str(args.out), "tasks": len(manifest["tasks"]), "balance": manifest["balance"]}
                )
            )
            return 0
        manifest = read_object(args.selection)
        rows = _dataset(args.dataset, manifest["revision"])
        config = load_config(args.config)
        ids = [entry["instance_id"] for entry in manifest["tasks"]]
        for instance_id in ids:
            resolve_task(manifest, rows, instance_id, allow_proposed=args.command == "preflight")
        if set(config["images"]) != set(ids):
            raise ValueError("configuration images must match exactly the frozen task selection")
        problems = dependency_problems()
        if manifest.get("admission") == "pending-human-acceptance":
            problems.append("complex selection and run-plan amendment require human acceptance")
        if not selection_committed(args.selection):
            problems.append("selection must be committed unchanged before owner-started execution")
        if args.command == "preflight":
            print(
                json.dumps(
                    {"ready": not problems, "problems": problems, "binding": binding(config, manifest)}, indent=2
                )
            )
            return 3 if problems else 0
        if problems:
            raise ValueError("; ".join(problems))
        if args.command == "smoke":
            from swebench_adapter.smoke import run_smoke  # noqa: PLC0415

            result = run_smoke(config, manifest, rows, args.out)
            print(
                json.dumps(
                    {
                        "smoke_receipt": str(args.out / "smoke.json"),
                        "checks": result["checks"],
                        "error": result.get("error"),
                    },
                    indent=2,
                )
            )
            return 0 if smoke_problem(result, result["binding"]) is None else 3
        from swebench_adapter.runner import run_batch, run_trial  # noqa: PLC0415

        smoke = read_object(args.smoke_receipt)
        if args.command == "trial":
            summary = run_trial(config, manifest, rows, ids[0], args.out, args.key_file, smoke)
            print(json.dumps(summary, indent=2))
        else:
            print(json.dumps(run_batch(config, manifest, rows, args.out, args.key_file, smoke), indent=2))
        return 0
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        message = str(exc)
        try:
            screen(message.encode())
        except ValueError:
            message = "input or runtime failure; credential-shaped details withheld"
        print(f"WP-08: {message[:1000]}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
