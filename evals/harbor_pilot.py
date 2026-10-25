"""Offline preparation and explicitly admitted Harbor static-authoring trials."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harbor_adapter.contracts import load_manifest, stage_task


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path(__file__).parent / "manifests/wp09-terminal-complex5.json"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    prepare = commands.add_parser("prepare")
    prepare.add_argument("--source", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    commands.add_parser("sdk-check")
    identity = commands.add_parser("binding")
    identity.add_argument("--config", type=Path, required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--source", type=Path, required=True)
    smoke.add_argument("--config", type=Path, required=True)
    smoke.add_argument("--case", required=True)
    smoke.add_argument("--output", type=Path, required=True)
    live = commands.add_parser("run")
    live.add_argument("--source", type=Path, required=True)
    live.add_argument("--config", type=Path, required=True)
    live.add_argument("--admission", type=Path, required=True)
    live.add_argument("--key-file", type=Path, required=True)
    live.add_argument("--output", type=Path, required=True)
    live.add_argument("--case", required=True)
    live.add_argument("--label", required=True)
    args = parser.parse_args()
    try:
        manifest = load_manifest(args.manifest)
        if args.command == "validate":
            result = {
                "selected": len(manifest["cases"]),
                "candidate_trials": 0,
                "status": "offline-valid; image pins, smoke and human admission pending",
            }
        elif args.command == "prepare":
            result = {
                "cases": [
                    stage_task(args.source, case, args.output / case["local_case_id"]) for case in manifest["cases"]
                ]
            }
        elif args.command == "sdk-check":
            from harbor.agents.factory import AgentFactory  # noqa: PLC0415
            from harbor.models.trial.config import AgentConfig  # noqa: PLC0415
            from harbor_adapter.sdk import FleetAgent, require_sdk  # noqa: PLC0415

            require_sdk()
            found = AgentFactory.get_agent_class_from_config(AgentConfig(import_path=FleetAgent.import_path()))
            result = {
                "custom_agent": found.import_path(),
                "abstract_methods": sorted(found.__abstractmethods__),
                "model_calls": 0,
            }
        elif args.command == "binding":
            from harbor_adapter.runner import binding  # noqa: PLC0415
            from swebench_adapter.configuration import load_config  # noqa: PLC0415
            from swebench_adapter.containers import Docker  # noqa: PLC0415

            result = binding(load_config(args.config), manifest, Docker())
        elif args.command == "smoke":
            from harbor_adapter.smoke import run_smoke  # noqa: PLC0415

            case = next((case for case in manifest["cases"] if case["local_case_id"] == args.case), None)
            if case is None:
                raise ValueError("case is outside the frozen selection")
            result = run_smoke(
                config_path=args.config, manifest=manifest, case=case, source=args.source, output=args.output
            )
        else:
            from harbor_adapter.runner import run_trial  # noqa: PLC0415

            case = next((case for case in manifest["cases"] if case["local_case_id"] == args.case), None)
            if case is None:
                raise ValueError("case is outside the frozen selection")
            result = run_trial(
                config_path=args.config,
                manifest=manifest,
                case=case,
                source=args.source,
                admission_path=args.admission,
                key_file=args.key_file,
                output=args.output,
                label=args.label,
            )
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        parser.exit(2, f"{type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
