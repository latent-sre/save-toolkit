"""Prepare the proposed SWT5 pilot offline; run only after exact admission and live smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from swebench_adapter.artifacts import store_json
from swebench_adapter.configuration import load_config
from swt_adapter import core, runner, smoke, verifier


def inputs(
    manifest_path: Path, dataset_path: Path, source: Path
) -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    manifest = json.loads(manifest_path.read_text())
    dataset = json.loads(dataset_path.read_text())
    if (
        not isinstance(dataset, dict)
        or dataset.get("dataset") != core.DATASET
        or dataset.get("revision") != core.DATASET_REVISION
    ):
        raise ValueError("source must be the pinned original SWE dataset envelope")
    verifier.check_source(source)
    filtering = (source / "dataset/filter_cases_verified.txt").read_bytes()
    if hashlib.sha256(filtering).hexdigest() != manifest["filter"]["sha256"]:
        raise ValueError("upstream exclusion filter digest mismatch")
    excluded = set(filtering.decode().splitlines())
    rows = core.select(manifest, dataset["rows"], excluded)
    return manifest, rows, excluded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate", "stage", "prepare", "export", "assess", "smoke", "run"])
    parser.add_argument("--manifest", type=Path, default=Path(__file__).parent / "manifests/wp09-swt-five.json")
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--instance-id")
    parser.add_argument("--patch", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--relevance", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--admission", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "assess":
            if args.receipt is None or args.patch is None:
                raise ValueError("assess requires receipt and patch")
            receipt = json.loads(args.receipt.read_text())
            manifest = json.loads(args.manifest.read_text())
            case = next(c for c in manifest["cases"] if c["instance_id"] == receipt["instance_id"])
            admission = core.admit_patch(args.patch.read_text(), case["test_roots"])
            if receipt["patch_sha256"] != admission["patch_sha256"]:
                raise ValueError("patch receipt identity mismatch")
            result = core.assess(
                receipt["instance_id"],
                receipt["upstream_report"],
                receipt["variants"],
                admission,
                relevance=json.loads(args.relevance.read_text()) if args.relevance else None,
            )
        else:
            if args.source is None or args.dataset is None:
                raise ValueError("pinned source and dataset are required")
            manifest, rows, excluded = inputs(args.manifest, args.dataset, args.source)
            result = {
                "status": "offline-valid",
                "selected": len(rows),
                "case_ids": [r["instance_id"] for r in rows],
                "manifest_sha256": core.digest(manifest),
                "human_acceptance": "pending",
                "live_execution": False,
            }
            if args.action in {"stage", "prepare"}:
                if args.output is None:
                    raise ValueError("output directory required")
                result.update(core.stage(manifest, rows, excluded, args.output))
                if args.action == "prepare":
                    store_json(
                        args.output,
                        "campaign-selection.json",
                        manifest,
                    )
                    store_json(
                        args.output,
                        "author-commands.json",
                        {
                            r["instance_id"]: runner.author_command(
                                {"model": "anthropic/claude-sonnet-5.5"}, core.author_input(r)
                            )
                            for r in rows
                        },
                    )
                    store_json(
                        args.output,
                        "pending-admission.json",
                        {
                            "accepted": False,
                            "owner": None,
                            "binding": None,
                            "required_smoke_checks": list(runner.SMOKE_CHECKS),
                            "smoke_receipt": None,
                            "smoke_sha256": None,
                            "profile": "static-tests-independently-verified-dec13",
                            "adapter_sha256": runner.adapter_digest(),
                            "manifest_sha256": core.digest(manifest),
                        },
                    )
            elif args.action == "export":
                if args.patch is None or args.output is None:
                    raise ValueError("export requires patch and output directory")
                case = next(c for c in manifest["cases"] if c["instance_id"] == args.instance_id)
                pred = core.prediction(args.instance_id, args.patch.read_text(), case["test_roots"])
                store_json(args.output, "predictions.json", [pred])
                result["predictions"] = str(args.output / "predictions.json")
            elif args.action == "smoke":
                if args.config is None or args.output is None or args.instance_id is None:
                    raise ValueError("smoke requires config, output and instance-id")
                result = smoke.run_smoke(
                    load_config(args.config), manifest, rows, excluded, args.source, args.output, args.instance_id
                )
            elif args.action == "run":
                if any(x is None for x in (args.config, args.key_file, args.admission, args.output, args.instance_id)):
                    raise ValueError("run requires config, key-file, admission, output and instance-id")

                result = runner.run_trial(
                    load_config(args.config),
                    manifest,
                    rows,
                    excluded,
                    args.instance_id,
                    args.output,
                    args.key_file,
                    args.source,
                    args.admission,
                )
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, KeyError, OSError, StopIteration) as error:
        print(f"SWT request refused: {type(error).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
