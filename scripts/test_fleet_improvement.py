#!/usr/bin/env python3
"""Mutation tests for the bounded, repository-backed fleet improvement ledger."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "skills/agent-authoring/scripts/fleet_improvement.py"
SCHEMA_PATH = ROOT / "skills/agent-authoring/assets/fleet-improvement-v1.schema.json"
PILOT_PATH = ROOT / "evals/improvements/fi_agent_routing_discovery/record.json"
ENVELOPE_PATH = ROOT / "scripts/evidence_envelope.py"
SPEC = importlib.util.spec_from_file_location("fleet_improvement", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
fleet_improvement = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fleet_improvement)
ENVELOPE_SPEC = importlib.util.spec_from_file_location("fleet_improvement_evidence", ENVELOPE_PATH)
if ENVELOPE_SPEC is None or ENVELOPE_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"cannot load {ENVELOPE_PATH}")
evidence_envelope = importlib.util.module_from_spec(ENVELOPE_SPEC)
ENVELOPE_SPEC.loader.exec_module(evidence_envelope)


SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
OBSERVATION_EVIDENCE_ID = "ev_" + "1" * 32
EVALUATION_EVIDENCE_ID = "ev_" + "2" * 32
REVIEW_EVIDENCE_ID = "ev_" + "3" * 32
MONITORING_EVIDENCE_ID = "ev_" + "4" * 32
ROLLBACK_EVIDENCE_ID = "ev_" + "5" * 32
SHADOW_EVIDENCE_ID = "ev_" + "6" * 32
ALLOWED_ROOTS = ("agents", "skills", "evals", "scripts", "schemas", "hooks", "commands")
SUBJECT_DIGEST_ALGORITHM = "sre-agents-git-artifact-selection-v1"


def _evidence_ref(evidence_id: str, digest: str) -> dict[str, object]:
    return {
        "evidence_id": evidence_id,
        "kind": "evidence_envelope",
        "locator": f"evals/evidence/{evidence_id}.json",
        "sha256": digest,
    }


def _observation(event_id: str = "fo_routing_misfire_20260731") -> dict[str, object]:
    return {
        "event_id": event_id,
        "kind": "routing_misfire",
        "observed_at": "2026-07-31T18:36:34Z",
        "source": {
            "kind": "eval_result",
            "locator": "evals/baselines/agent-routing/README.md",
            "revision": SHA_A,
            "sha256": DIGEST_A,
        },
        "trust": "mixed",
        "summary": "Explicit review requests stayed inline instead of invoking reviewer.",
        "evidence_ids": [OBSERVATION_EVIDENCE_ID],
    }


def _attempt(*, result: str = "pass", evaluation: bool = True) -> dict[str, object]:
    evaluation_value: dict[str, object] | None = None
    if evaluation:
        evaluation_value = {
            "kind": "evidence_envelope",
            "evaluator": "protected-evaluator",
            "evidence_id": EVALUATION_EVIDENCE_ID,
            "locator": f"evals/evidence/{EVALUATION_EVIDENCE_ID}.json",
            "sha256": DIGEST_B,
            "subject_revision": SHA_B,
            "evaluator_revision": SHA_A,
            "runner_sha256": DIGEST_A,
            "suite_sha256": DIGEST_B,
            "case_set_sha256": DIGEST_C,
            "requested_model": "gpt-5.6-sol",
            "observed_model": "gpt-5.6-sol",
            "reasoning_mode": "ultra",
            "trial_count": 3,
            "result": result,
            "safety_regression": False,
            "authority_regression": False,
        }
    return {
        "attempt_id": "fa_reviewer_description_v1",
        "iteration": 1,
        "parent_revision": SHA_A,
        "subject_revision": SHA_B,
        "subject_sha256": DIGEST_B,
        "change_summary": "Clarify the reviewer selection trigger without changing authority.",
        "author": {"name": "prompt-engineer", "role": "prompt-engineer"},
        "reservation": {
            "model_turns": 3,
            "evaluator_calls": 3,
            "tokens": 12000,
            "wall_seconds": 300,
            "cost_usd": 2.5,
        },
        "actual_usage": {
            "model_turns": 3,
            "evaluator_calls": 3,
            "tokens": 12000,
            "wall_seconds": 300,
            "cost_usd": 2.5,
        } if evaluation else None,
        "case_sets": {
            "calibration": {"sha256": DIGEST_A, "case_count": 3},
            "regression": {"sha256": DIGEST_B, "case_count": 2},
            "shadow": None,
        },
        "evaluation": evaluation_value,
        "outcome": result if evaluation else "proposed",
        "stop_reason": None if result == "pass" or not evaluation else "No measured improvement.",
    }


def _record(status: str = "evaluated", *, result: str = "pass") -> dict[str, object]:
    has_attempt = status not in {
        "observed",
        "qualified",
        "duplicate",
        "not_reproducible",
        "not_actionable",
    }
    evaluated = status not in {"candidate"}
    attempts = [_attempt(result=result, evaluation=evaluated)] if has_attempt else []
    record: dict[str, object] = {
        "schema_version": 1,
        "improvement_id": "fi_agent_routing_discovery",
        "created_at": "2026-07-31T18:36:34Z",
        "updated_at": "2026-07-31T19:06:34Z",
        "target": {
            "repository": "latent-sre/sre-agents",
            "base_revision": SHA_A,
            "artifact_kind": "agent",
            "artifact_paths": ["agents/reviewer.md"],
        },
        "owner": {
            "name": "latent-sre",
            "kind": "team",
            "agent_lane": "prompt-engineer",
        },
        "related_improvement_id": None,
        "severity": "medium",
        "failure_fingerprint": "ff_" + "d" * 64,
        "observations": [_observation()],
        "evidence_refs": [_evidence_ref(OBSERVATION_EVIDENCE_ID, DIGEST_A)],
        "status": status,
        "success_criteria": [
            "Reviewer routing improves without weakening the merge-readiness negative.",
            "No safety or authority regression is present.",
        ],
        "monitoring_plan": {
            "criterion_id": "fm_post_merge_regression",
            "criterion": "The regression suite remains green after merge.",
            "rollback_triggers": [
                "monitoring_fail",
                "monitoring_inconclusive",
                "security_finding",
                "authority_revoked",
                "merge_error",
                "manual_owner_decision",
            ],
        },
        "budget": {
            "origin": "predeclared",
            "max_attempts": 3,
            "max_model_turns": 30,
            "max_evaluator_calls": 30,
            "max_tokens": 200000,
            "max_wall_seconds": 7200,
            "max_cost_usd": 50.0,
        },
        "attempts": attempts,
        "reviews": [],
        "merge": None,
        "monitoring": None,
        "rollback": None,
        "lesson": {
            "status": "pending",
            "control_path": None,
            "reason": "Closeout has not happened yet.",
        },
        "disposition_reason": "The candidate has completed exact-subject evaluation.",
        "limitations": ["No human-owned shadow set was available."],
    }
    if evaluated and attempts:
        record["evidence_refs"].append(  # type: ignore[union-attr]
            _evidence_ref(EVALUATION_EVIDENCE_ID, DIGEST_B)
        )
    if status == "in_review":
        record["disposition_reason"] = "Conclusive evidence is ready for independent review."
    elif status == "rejected":
        record["disposition_reason"] = "The candidate produced no measured improvement."
        record["lesson"] = {
            "status": "encoded",
            "control_path": "evals/scenarios/agent-direct-reviewer-authz-block.yaml",
            "reason": "Use direct contracts as the behavioral gate.",
        }
    if status in {"in_review", "merged", "monitoring", "closed", "rolled_back"}:
        record["reviews"].append({  # type: ignore[union-attr]
            "attempt_id": "fa_reviewer_description_v1",
            "subject_revision": SHA_B,
            "reviewer": "reviewer",
            "verdict": "pass",
            "evidence_id": REVIEW_EVIDENCE_ID,
            "locator": f"evals/evidence/{REVIEW_EVIDENCE_ID}.json",
            "evidence_sha256": DIGEST_C,
            "reviewed_at": "2026-07-31T18:45:00Z",
        })
        record["evidence_refs"].append(  # type: ignore[union-attr]
            _evidence_ref(REVIEW_EVIDENCE_ID, DIGEST_C)
        )
    if status in {"merged", "monitoring", "closed", "rolled_back"}:
        record["merge"] = {
            "pr_url": "https://github.com/latent-sre/sre-agents/pull/1",
            "subject_revision": SHA_B,
            "merge_revision": SHA_C,
            "merged_at": "2026-07-31T18:50:00Z",
            "merged_by": "maintainer",
        }
    if status in {"monitoring", "closed", "rolled_back"}:
        monitor_result = "fail" if status == "rolled_back" else "pass"
        record["monitoring"] = {
            "subject_revision": SHA_C,
            "criterion_id": "fm_post_merge_regression",
            "observed_by": "protected-monitor",
            "observed_at": "2026-07-31T19:00:00Z",
            "result": monitor_result,
            "evidence_ids": [MONITORING_EVIDENCE_ID],
        }
        record["evidence_refs"].append(  # type: ignore[union-attr]
            _evidence_ref(MONITORING_EVIDENCE_ID, DIGEST_A)
        )
    if status == "closed":
        record["lesson"] = {
            "status": "encoded",
            "control_path": "evals/scenarios/agent-direct-reviewer-authz-block.yaml",
            "reason": "The reproduced failure is retained as regression coverage.",
        }
    if status == "rolled_back":
        record["rollback"] = {
            "subject_revision": SHA_B,
            "merge_revision": SHA_C,
            "rollback_revision": SHA_D,
            "rolled_back_at": "2026-07-31T19:05:00Z",
            "rolled_back_by": "maintainer",
            "trigger": "monitoring_fail",
            "reason": "Post-merge monitoring failed.",
            "evidence_ids": [ROLLBACK_EVIDENCE_ID],
        }
        record["evidence_refs"].append(  # type: ignore[union-attr]
            _evidence_ref(ROLLBACK_EVIDENCE_ID, DIGEST_D)
        )
        record["lesson"] = {
            "status": "encoded",
            "control_path": "evals/scenarios/agent-direct-reviewer-authz-block.yaml",
            "reason": "The rollback trigger remains deterministic regression coverage.",
        }
    return record


def _materialize_evidence_envelopes(
    repository_root: Path,
    record: dict[str, object],
    mutate: Callable[[str, dict[str, object]], None] | None = None,
) -> None:
    """Create valid fixture envelopes and synchronize their recorded file digests."""

    attempts = record["attempts"]  # type: ignore[assignment]
    attempt = attempts[-1] if attempts else None
    observation = record["observations"][0]  # type: ignore[index]
    source = observation["source"]
    evaluation = attempt["evaluation"] if attempt is not None else None
    reviews_by_id = {
        item["evidence_id"]: item for item in record["reviews"]  # type: ignore[union-attr]
    }
    shadow_by_id = {
        item["case_sets"]["shadow"]["evidence_id"]: (item, item["case_sets"]["shadow"])
        for item in attempts
        if item["case_sets"]["shadow"] is not None
    }
    monitoring = record["monitoring"]
    rollback = record["rollback"]
    started = datetime(2026, 7, 31, 18, 40, tzinfo=timezone.utc)
    ended = started + timedelta(seconds=30)

    for ref in record["evidence_refs"]:  # type: ignore[union-attr]
        if ref["kind"] == "historical_report":
            continue
        evidence_id = str(ref["evidence_id"])
        kwargs: dict[str, object]
        if evidence_id == OBSERVATION_EVIDENCE_ID:
            kwargs = {
                "producer": "triage-owner",
                "role": "triage",
                "target_revision": source["revision"] or record["target"]["base_revision"],
                "tree_digest": None,
                "criterion": "Retain the measured fleet failure as typed evidence.",
                "status": "fail",
                "attempt_id": None,
                "source": {
                    "event_id": observation["event_id"],
                    "source_kind": source["kind"],
                    "source_locator": source["locator"],
                    "source_revision": source["revision"],
                    "source_sha256": source["sha256"],
                },
            }
        elif evidence_id in shadow_by_id:
            shadow_attempt, shadow = shadow_by_id[evidence_id]
            kwargs = {
                "producer": "protected-shadow-evaluator",
                "role": "evaluator",
                "target_revision": shadow_attempt["subject_revision"],
                "tree_digest": shadow_attempt["subject_sha256"],
                "criterion": "Evaluate the exact candidate against the held-out shadow set.",
                "status": shadow["result"],
                "attempt_id": shadow_attempt["attempt_id"],
                "source": {
                    "case_set_sha256": shadow["sha256"],
                    "case_count": shadow["case_count"],
                    "held_externally": True,
                    "subject_digest_algorithm": SUBJECT_DIGEST_ALGORITHM,
                },
            }
        elif evaluation is not None and evidence_id == evaluation["evidence_id"]:
            kwargs = {
                "producer": evaluation["evaluator"],
                "role": "evaluator",
                "target_revision": attempt["subject_revision"],
                "tree_digest": attempt["subject_sha256"],
                "criterion": "Evaluate the exact candidate against frozen case sets.",
                "status": evaluation["result"],
                "attempt_id": attempt["attempt_id"],
                "source": {
                    field: evaluation[field]
                    for field in (
                        "evaluator_revision",
                        "runner_sha256",
                        "suite_sha256",
                        "case_set_sha256",
                        "requested_model",
                        "observed_model",
                        "reasoning_mode",
                        "trial_count",
                        "safety_regression",
                        "authority_regression",
                    )
                }
                | {
                    "reservation": attempt["reservation"],
                    "actual_usage": attempt["actual_usage"],
                    "subject_digest_algorithm": SUBJECT_DIGEST_ALGORITHM,
                },
            }
        elif evidence_id in reviews_by_id:
            review = reviews_by_id[evidence_id]
            reviewed_attempt = next(
                item for item in attempts if item["attempt_id"] == review["attempt_id"]
            )
            kwargs = {
                "producer": review["reviewer"],
                "role": "reviewer",
                "target_revision": review["subject_revision"],
                "tree_digest": reviewed_attempt["subject_sha256"],
                "criterion": "Independently review the exact evaluated candidate.",
                "status": "pass" if review["verdict"] == "pass" else "fail",
                "attempt_id": review["attempt_id"],
                "source": {
                    "attempt_id": review["attempt_id"],
                    "reviewer": review["reviewer"],
                    "verdict": review["verdict"],
                    "subject_digest_algorithm": SUBJECT_DIGEST_ALGORITHM,
                },
            }
        elif monitoring is not None and evidence_id in monitoring["evidence_ids"]:
            kwargs = {
                "producer": monitoring["observed_by"],
                "role": "evaluator",
                "target_revision": monitoring["subject_revision"],
                "tree_digest": None,
                "criterion": record["monitoring_plan"]["criterion"],
                "status": monitoring["result"],
                "attempt_id": attempt["attempt_id"],
                "source": {"criterion_id": monitoring["criterion_id"]},
            }
        elif rollback is not None and evidence_id in rollback["evidence_ids"]:
            kwargs = {
                "producer": rollback["rolled_back_by"],
                "role": "human_or_protected_workflow",
                "target_revision": rollback["rollback_revision"],
                "tree_digest": None,
                "criterion": "Verify the exact rollback revision was applied.",
                "status": "pass",
                "attempt_id": attempt["attempt_id"],
                "source": {
                    field: rollback[field]
                    for field in (
                        "trigger",
                        "subject_revision",
                        "merge_revision",
                        "rollback_revision",
                    )
                },
            }
        else:  # pragma: no cover - fixture construction error
            raise AssertionError(f"no fixture envelope contract for {evidence_id}")

        envelope = evidence_envelope.new_envelope(
            producer=kwargs["producer"],
            role=kwargs["role"],
            target_root=".",
            target_revision=kwargs["target_revision"],
            criterion=kwargs["criterion"],
            status=kwargs["status"],
            started_at=started,
            ended_at=ended,
            source=kwargs["source"],
            attempt_id=kwargs["attempt_id"],
            tree_digest=kwargs["tree_digest"],
            evidence_id=evidence_id,
            isolation={"network": "denied", "workspace": "temporary"},
        )
        if mutate is not None:
            mutate(evidence_id, envelope)
        raw = evidence_envelope.canonical_json(envelope)
        path = repository_root / str(ref["locator"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        ref["sha256"] = digest
        if evaluation is not None and evidence_id == evaluation["evidence_id"]:
            evaluation["sha256"] = digest
        if evidence_id in reviews_by_id:
            reviews_by_id[evidence_id]["evidence_sha256"] = digest


def _git(
    repository_root: Path,
    *arguments: str,
    input_bytes: bytes | None = None,
) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        input=input_bytes,
        stdin=None if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise AssertionError(
            f"git {' '.join(arguments)} failed with {completed.returncode}: {stderr}"
        )
    return completed.stdout.decode("utf-8", errors="strict").strip()


def _raw_tree_entry(mode: str, path: str, object_id: str) -> bytes:
    return (
        mode.encode("ascii")
        + b" "
        + path.encode("utf-8")
        + b"\0"
        + bytes.fromhex(object_id)
    )


def _raw_commit_with_entry(
    repository_root: Path,
    *,
    mode: str,
    path: str,
    object_id: str,
    message: str,
) -> str:
    tree = _git(
        repository_root,
        "hash-object",
        "-t",
        "tree",
        "--literally",
        "-w",
        "--stdin",
        input_bytes=_raw_tree_entry(mode, path, object_id),
    )
    return _git(repository_root, "commit-tree", tree, "-m", message)


def _init_git_repository(repository_root: Path) -> None:
    _git(repository_root, "init", "--quiet")
    _git(repository_root, "config", "user.name", "Fleet Improvement Test")
    _git(repository_root, "config", "user.email", "fleet-improvement@example.invalid")
    _git(repository_root, "config", "commit.gpgsign", "false")


def _commit_files(
    repository_root: Path,
    files: dict[str, str],
    message: str,
) -> str:
    for locator, content in files.items():
        path = repository_root / locator
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    _git(repository_root, "add", "--all", "--", ".")
    _git(repository_root, "commit", "--quiet", "-m", message)
    return _git(repository_root, "rev-parse", "HEAD")


def _repository_bound_record(
    repository_root: Path,
    *,
    base_revision: str,
    subject_revision: str,
    artifact_paths: list[str],
    status: str = "evaluated",
    merge_revision: str | None = None,
    rollback_revision: str | None = None,
    encoded_lesson: bool = False,
) -> dict[str, object]:
    record = _record(status)
    if status in {"closed", "rolled_back"} and not encoded_lesson:
        record["lesson"] = {
            "status": "not_applicable",
            "control_path": None,
            "reason": "This repository-binding fixture does not exercise a durable lesson control.",
        }
    record["target"]["base_revision"] = base_revision  # type: ignore[index]
    record["target"]["artifact_paths"] = artifact_paths  # type: ignore[index]
    attempt = record["attempts"][0]  # type: ignore[index]
    attempt["parent_revision"] = base_revision  # type: ignore[index]
    attempt["subject_revision"] = subject_revision  # type: ignore[index]
    attempt["subject_sha256"] = fleet_improvement.artifact_selection_sha256(
        repository_root,
        subject_revision,
        artifact_paths,
    )
    attempt["evaluation"]["subject_revision"] = subject_revision  # type: ignore[index]
    for review in record["reviews"]:  # type: ignore[union-attr]
        review["subject_revision"] = subject_revision
    if record["merge"] is not None:
        if merge_revision is None:
            raise AssertionError(f"status {status} requires merge_revision")
        record["merge"]["subject_revision"] = subject_revision  # type: ignore[index]
        record["merge"]["merge_revision"] = merge_revision  # type: ignore[index]
    if record["monitoring"] is not None:
        if merge_revision is None:
            raise AssertionError(f"status {status} requires merge_revision")
        record["monitoring"]["subject_revision"] = merge_revision  # type: ignore[index]
    if record["rollback"] is not None:
        if merge_revision is None or rollback_revision is None:
            raise AssertionError(f"status {status} requires merge_revision and rollback_revision")
        record["rollback"]["subject_revision"] = subject_revision  # type: ignore[index]
        record["rollback"]["merge_revision"] = merge_revision  # type: ignore[index]
        record["rollback"]["rollback_revision"] = rollback_revision  # type: ignore[index]
    return record


def _two_parent_rollback_application(
    repository_root: Path,
    *,
    application_files: dict[str, str] | None = None,
) -> tuple[str, str, str, str, str]:
    base = _commit_files(
        repository_root,
        {
            "agents/reviewer.md": "base\n",
            "scripts/application-state.txt": "base\n",
        },
        "base",
    )
    subject = _commit_files(
        repository_root,
        {"agents/reviewer.md": "candidate\n"},
        "candidate",
    )
    rollback_subject = _commit_files(
        repository_root,
        {"agents/reviewer.md": "base\n"},
        "prepare exact rollback subject",
    )

    _git(repository_root, "checkout", "--quiet", "--detach", subject)
    application_integration = _commit_files(
        repository_root,
        {"scripts/application-state.txt": "advanced\n"},
        "advance rollback application parent",
    )
    application_tree_files = {"agents/reviewer.md": "base\n"}
    application_tree_files.update(application_files or {})
    for locator, content in application_tree_files.items():
        path = repository_root / locator
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    _git(repository_root, "add", "--all", "--", ".")
    application_tree = _git(repository_root, "write-tree")
    application_merge = _git(
        repository_root,
        "commit-tree",
        application_tree,
        "-p",
        application_integration,
        "-p",
        rollback_subject,
        "-m",
        "apply exact rollback subject",
    )
    return (
        base,
        subject,
        rollback_subject,
        application_integration,
        application_merge,
    )


def _two_parent_merge_components(
    repository_root: Path,
) -> tuple[str, str, str, str, str]:
    base = _commit_files(
        repository_root,
        {"agents/reviewer.md": "base\n"},
        "base",
    )
    main_branch = _git(repository_root, "branch", "--show-current")
    _git(repository_root, "checkout", "--quiet", "-b", "candidate")
    subject = _commit_files(
        repository_root,
        {"agents/reviewer.md": "candidate\n"},
        "candidate",
    )
    _git(repository_root, "checkout", "--quiet", main_branch)
    integration_parent = _commit_files(
        repository_root,
        {"scripts/mainline.py": "print('integration parent')\n"},
        "advance integration parent",
    )
    candidate_agents_tree = _git(repository_root, "rev-parse", f"{subject}:agents")
    integration_scripts_tree = _git(
        repository_root,
        "rev-parse",
        f"{integration_parent}:scripts",
    )
    return (
        base,
        subject,
        integration_parent,
        candidate_agents_tree,
        integration_scripts_tree,
    )


def _closed_record_with_lesson_entry(
    repository_root: Path,
    entry_kind: str,
) -> tuple[dict[str, object], str]:
    control_path = "evals/scenarios/agent-direct-reviewer-authz-block.yaml"
    base = _commit_files(
        repository_root,
        {"agents/reviewer.md": "base\n"},
        "base",
    )
    subject = _commit_files(
        repository_root,
        {"agents/reviewer.md": "candidate\n"},
        "candidate",
    )
    if entry_kind == "regular":
        record_revision = _commit_files(
            repository_root,
            {control_path: "id: encoded-regression\n"},
            "encode terminal lesson",
        )
    elif entry_kind == "directory":
        record_revision = _commit_files(
            repository_root,
            {f"{control_path}/case.yaml": "id: nested-under-control-path\n"},
            "encode terminal lesson path as a directory",
        )
    elif entry_kind == "missing":
        record_revision = subject
    else:
        if entry_kind == "symlink":
            object_id = _git(
                repository_root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=b"../../outside\n",
            )
            mode = "120000"
        elif entry_kind == "gitlink":
            object_id = subject
            mode = "160000"
        else:  # pragma: no cover - fixture misuse
            raise AssertionError(f"unsupported lesson entry kind: {entry_kind}")
        _git(
            repository_root,
            "update-index",
            "--add",
            "--cacheinfo",
            f"{mode},{object_id},{control_path}",
        )
        lesson_tree = _git(repository_root, "write-tree")
        record_revision = _git(
            repository_root,
            "commit-tree",
            lesson_tree,
            "-p",
            subject,
            "-m",
            f"encode terminal lesson as {entry_kind}",
        )
    record = _repository_bound_record(
        repository_root,
        base_revision=base,
        subject_revision=subject,
        artifact_paths=["agents/reviewer.md"],
        status="closed",
        merge_revision=subject,
        encoded_lesson=True,
    )
    return record, record_revision


class FleetImprovementContractTests(unittest.TestCase):
    def _validate(self, record: dict[str, object]) -> None:
        fleet_improvement.validate_record(
            record,
            allowed_artifact_roots=ALLOWED_ROOTS,
        )

    def _transition(
        self,
        previous: dict[str, object],
        current: dict[str, object],
        role: str,
        *,
        actor: str | None = None,
    ) -> None:
        prior_time = datetime.fromisoformat(str(previous["updated_at"]).replace("Z", "+00:00"))
        current["updated_at"] = (prior_time + timedelta(seconds=1)).isoformat().replace(
            "+00:00", "Z"
        )
        subject_revision = None
        if current["attempts"]:
            subject_revision = current["attempts"][-1]["subject_revision"]  # type: ignore[index]
        if actor is None:
            if len(current["attempts"]) > len(previous["attempts"]):  # type: ignore[arg-type]
                actor = current["attempts"][-1]["author"]["name"]  # type: ignore[index]
            elif (
                current["attempts"]
                and previous["attempts"]
                and previous["attempts"][-1]["evaluation"] is None  # type: ignore[index]
                and current["attempts"][-1]["evaluation"] is not None  # type: ignore[index]
            ):
                actor = current["attempts"][-1]["evaluation"]["evaluator"]  # type: ignore[index]
            elif len(current["reviews"]) > len(previous["reviews"]):  # type: ignore[arg-type]
                actor = current["reviews"][-1]["reviewer"]  # type: ignore[index]
            elif previous["merge"] is None and current["merge"] is not None:
                actor = current["merge"]["merged_by"]  # type: ignore[index]
            elif previous["monitoring"] is None and current["monitoring"] is not None:
                actor = current["monitoring"]["observed_by"]  # type: ignore[index]
            elif previous["rollback"] is None and current["rollback"] is not None:
                actor = current["rollback"]["rolled_back_by"]  # type: ignore[index]
            else:
                actor = {
                    "triage": "triage-owner",
                    "author": "prompt-engineer",
                    "evaluator": "protected-evaluator",
                    "reviewer": "reviewer",
                    "human_or_protected_workflow": "maintainer",
                }[role]
        fleet_improvement.validate_transition(
            previous,
            current,
            allowed_artifact_roots=ALLOWED_ROOTS,
            authority={
                "actor": actor,
                "role": role,
                "subject_revision": subject_revision,
            },
        )

    def test_schema_tracks_executable_validator(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(set(schema["required"]), fleet_improvement.TOP_FIELDS)
        self.assertEqual(set(schema["properties"]), fleet_improvement.TOP_FIELDS)
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            fleet_improvement.STATUSES,
        )
        self.assertEqual(
            schema["$defs"]["target"]["properties"]["artifact_paths"]["maxItems"],
            fleet_improvement.MAX_ARTIFACT_PATHS,
        )
        self.assertEqual(
            schema["$defs"]["target"]["properties"]["artifact_paths"]["maxItems"],
            fleet_improvement.MAX_ARTIFACT_PATHS,
        )
        required_sets = {
            "target": fleet_improvement.TARGET_FIELDS,
            "owner": fleet_improvement.OWNER_FIELDS,
            "observation_source": fleet_improvement.SOURCE_FIELDS,
            "observation": fleet_improvement.OBSERVATION_FIELDS,
            "evidence_ref": fleet_improvement.EVIDENCE_REF_FIELDS,
            "budget": fleet_improvement.BUDGET_FIELDS,
            "monitoring_plan": fleet_improvement.MONITORING_PLAN_FIELDS,
            "author": fleet_improvement.AUTHOR_FIELDS,
            "usage": fleet_improvement.USAGE_FIELDS,
            "visible_case_set": fleet_improvement.VISIBLE_CASE_SET_FIELDS,
            "shadow": fleet_improvement.SHADOW_FIELDS,
            "case_sets": fleet_improvement.CASE_SET_FIELDS,
            "evaluation": fleet_improvement.EVALUATION_FIELDS,
            "attempt": fleet_improvement.ATTEMPT_FIELDS,
            "review": fleet_improvement.REVIEW_FIELDS,
            "merge": fleet_improvement.MERGE_FIELDS,
            "monitoring": fleet_improvement.MONITORING_FIELDS,
            "rollback": fleet_improvement.ROLLBACK_FIELDS,
            "lesson": fleet_improvement.LESSON_FIELDS,
        }
        for definition, expected in required_sets.items():
            with self.subTest(definition=definition):
                self.assertEqual(set(schema["$defs"][definition]["required"]), expected)
                self.assertEqual(set(schema["$defs"][definition]["properties"]), expected)

        references: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                if "$ref" in value:
                    references.append(value["$ref"])
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(schema)
        for reference in references:
            with self.subTest(reference=reference):
                self.assertRegex(reference, r"^#\/\$defs\/[a-z0-9_]+$")
                self.assertIn(reference.removeprefix("#/$defs/"), schema["$defs"])

    def test_schema_uses_one_strict_literal_t_timestamp_contract_everywhere(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        timestamp_reference = {"$ref": "#/$defs/timestamp"}
        timestamp_properties = (
            ("created_at", schema["properties"]["created_at"]),
            ("updated_at", schema["properties"]["updated_at"]),
            (
                "observation.observed_at",
                schema["$defs"]["observation"]["properties"]["observed_at"],
            ),
            (
                "review.reviewed_at",
                schema["$defs"]["review"]["properties"]["reviewed_at"],
            ),
            ("merge.merged_at", schema["$defs"]["merge"]["properties"]["merged_at"]),
            (
                "monitoring.observed_at",
                schema["$defs"]["monitoring"]["properties"]["observed_at"],
            ),
            (
                "rollback.rolled_back_at",
                schema["$defs"]["rollback"]["properties"]["rolled_back_at"],
            ),
        )
        for field, timestamp_property in timestamp_properties:
            with self.subTest(field=field):
                self.assertEqual(timestamp_property, timestamp_reference)

        pattern = schema["$defs"]["timestamp"]["pattern"]
        self.assertIsNotNone(re.search(pattern, "2026-07-31T18:36:34Z"))
        for invalid in (
            "2026-07-31t18:36:34Z",
            "2026-07-31 18:36:34Z",
            "2026-07-31_18:36:34Z",
            "2026-07-31X18:36:34Z",
            "2026-07-31TT18:36:34Z",
            "2026-07-31T18:36Z",
            "2026-07-31T18:36:34z",
            "2026-07-31T18:36:34+00:00",
        ):
            with self.subTest(invalid=invalid):
                self.assertIsNone(re.search(pattern, invalid))

    def test_cli_record_loader_rejects_duplicate_json_keys(self) -> None:
        payloads = (
            '{"schema_version":1,"schema_version":2}\n',
            '{"target":{"repository":"first","repository":"second"}}\n',
        )
        for payload in payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temporary:
                record_path = Path(temporary) / "record.json"
                record_path.write_text(payload, encoding="utf-8", newline="\n")
                with self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    "duplicate JSON(?: object)? key",
                ):
                    fleet_improvement._load(record_path, "record")

    def test_committed_historical_pilot_is_rejected_and_non_promotable(self) -> None:
        pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
        self._validate(pilot)
        fleet_improvement.validate_evidence_files(
            pilot,
            repository_root=ROOT,
            allowed_evidence_roots=("evals/baselines",),
            envelope_validator=lambda envelope: None,
        )
        self.assertEqual(pilot["status"], "rejected")
        self.assertEqual(pilot["budget"]["origin"], "retrospective_import")
        self.assertEqual(pilot["attempts"][-1]["evaluation"]["kind"], "historical_report")
        self.assertIsNone(pilot["attempts"][-1]["subject_revision"])

        tampered = copy.deepcopy(pilot)
        tampered["evidence_refs"][0]["sha256"] = DIGEST_A
        tampered["attempts"][0]["evaluation"]["sha256"] = DIGEST_A
        self._validate(tampered)
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "does not match its recorded sha256",
        ):
            fleet_improvement.validate_evidence_files(
                tampered,
                repository_root=ROOT,
                allowed_evidence_roots=("evals/baselines",),
                envelope_validator=lambda envelope: None,
            )

    def test_promoted_records_require_resolved_evidence_files(self) -> None:
        record = _record("closed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "evals/evidence").mkdir(parents=True)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "cannot be inspected",
            ):
                fleet_improvement.validate_evidence_files(
                    record,
                    repository_root=root,
                    allowed_evidence_roots=("evals/evidence",),
                    envelope_validator=lambda envelope: None,
                )

    def test_resolved_envelopes_are_schema_valid_and_cross_bound(self) -> None:
        record = _record("closed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _materialize_evidence_envelopes(root, record)
            self._validate(record)
            fleet_improvement.validate_evidence_files(
                record,
                repository_root=root,
                allowed_evidence_roots=("evals/evidence",),
                envelope_validator=evidence_envelope.validate_envelope,
            )

        mutations = (
            (
                "observation source",
                OBSERVATION_EVIDENCE_ID,
                lambda envelope: envelope["source"].update(  # type: ignore[union-attr]
                    {"source_locator": "evals/forged.json"}
                ),
                "observations\\[0\\] evidence source disagrees on source_locator",
            ),
            (
                "evaluation target",
                EVALUATION_EVIDENCE_ID,
                lambda envelope: envelope["target"].update({"revision": SHA_C}),  # type: ignore[union-attr]
                "evaluation evidence target revision",
            ),
            (
                "evaluation producer",
                EVALUATION_EVIDENCE_ID,
                lambda envelope: envelope["producer"].update(  # type: ignore[union-attr]
                    {"name": "different-evaluator"}
                ),
                "evaluation evidence producer does not match evaluator",
            ),
            (
                "evaluation source",
                EVALUATION_EVIDENCE_ID,
                lambda envelope: envelope["source"].update(  # type: ignore[union-attr]
                    {"requested_model": "different-model"}
                ),
                "evaluation evidence source disagrees on requested_model",
            ),
            (
                "evaluation actual usage",
                EVALUATION_EVIDENCE_ID,
                lambda envelope: envelope["source"].update(  # type: ignore[union-attr]
                    {
                        "actual_usage": {
                            "model_turns": 3,
                            "evaluator_calls": 3,
                            "tokens": 11_999,
                            "wall_seconds": 300,
                            "cost_usd": 2.5,
                        }
                    }
                ),
                "evaluation evidence source disagrees on actual_usage",
            ),
            (
                "evaluation reservation",
                EVALUATION_EVIDENCE_ID,
                lambda envelope: envelope["source"].update(  # type: ignore[union-attr]
                    {
                        "reservation": {
                            "model_turns": 3,
                            "evaluator_calls": 3,
                            "tokens": 11_999,
                            "wall_seconds": 300,
                            "cost_usd": 2.5,
                        }
                    }
                ),
                "evaluation evidence source disagrees on reservation",
            ),
            (
                "review producer",
                REVIEW_EVIDENCE_ID,
                lambda envelope: envelope["producer"].update(  # type: ignore[union-attr]
                    {"name": "different-reviewer"}
                ),
                "evidence producer does not match reviewer",
            ),
            (
                "monitoring criterion",
                MONITORING_EVIDENCE_ID,
                lambda envelope: envelope.update({"criterion": "A post-selected criterion."}),
                "criterion does not match monitoring_plan",
            ),
            (
                "monitoring producer",
                MONITORING_EVIDENCE_ID,
                lambda envelope: envelope["producer"].update(  # type: ignore[union-attr]
                    {"name": "different-monitor"}
                ),
                "evidence producer does not match monitoring.observed_by",
            ),
        )
        for label, evidence_id, mutate, expected in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                tampered = _record("closed")

                def targeted(identifier: str, envelope: dict[str, object]) -> None:
                    if identifier == evidence_id:
                        mutate(envelope)

                _materialize_evidence_envelopes(root, tampered, targeted)
                self._validate(tampered)
                with self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    expected,
                ):
                    fleet_improvement.validate_evidence_files(
                        tampered,
                        repository_root=root,
                        allowed_evidence_roots=("evals/evidence",),
                        envelope_validator=evidence_envelope.validate_envelope,
                    )

    def test_subject_digest_algorithm_is_exact_and_required_for_bound_envelopes(self) -> None:
        self.assertEqual(
            fleet_improvement.SUBJECT_DIGEST_ALGORITHM,
            SUBJECT_DIGEST_ALGORITHM,
        )

        def with_shadow() -> dict[str, object]:
            record = _record("in_review")
            attempt = record["attempts"][0]  # type: ignore[index]
            attempt["case_sets"]["shadow"] = {  # type: ignore[index]
                "sha256": DIGEST_D,
                "case_count": 2,
                "result": "pass",
                "evidence_id": SHADOW_EVIDENCE_ID,
            }
            record["evidence_refs"].append(  # type: ignore[union-attr]
                _evidence_ref(SHADOW_EVIDENCE_ID, DIGEST_D)
            )
            return record

        valid = with_shadow()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _materialize_evidence_envelopes(root, valid)
            self._validate(valid)
            fleet_improvement.validate_evidence_files(
                valid,
                repository_root=root,
                allowed_evidence_roots=("evals/evidence",),
                envelope_validator=evidence_envelope.validate_envelope,
            )

        for evidence_id in (
            SHADOW_EVIDENCE_ID,
            EVALUATION_EVIDENCE_ID,
            REVIEW_EVIDENCE_ID,
        ):
            for replacement in (None, "different-artifact-selection-v1"):
                with (
                    self.subTest(evidence_id=evidence_id, replacement=replacement),
                    tempfile.TemporaryDirectory() as temporary,
                ):
                    root = Path(temporary)
                    tampered = with_shadow()

                    def targeted(identifier: str, envelope: dict[str, object]) -> None:
                        if identifier != evidence_id:
                            return
                        source = envelope["source"]  # type: ignore[assignment]
                        if replacement is None:
                            source.pop("subject_digest_algorithm")  # type: ignore[union-attr]
                        else:
                            source["subject_digest_algorithm"] = replacement  # type: ignore[index]

                    _materialize_evidence_envelopes(root, tampered, targeted)
                    self._validate(tampered)
                    with self.assertRaisesRegex(
                        fleet_improvement.FleetImprovementValidationError,
                        "subject_digest_algorithm",
                    ):
                        fleet_improvement.validate_evidence_files(
                            tampered,
                            repository_root=root,
                            allowed_evidence_roots=("evals/evidence",),
                            envelope_validator=evidence_envelope.validate_envelope,
                        )

    def test_valid_observed_rejected_and_closed_records_pass(self) -> None:
        self._validate(_record("observed"))
        self._validate(_record("rejected", result="fail"))
        self._validate(_record("closed"))

    def test_new_records_cannot_bootstrap_into_promoted_states(self) -> None:
        fleet_improvement.validate_initial_record(
            _record("observed"),
            allowed_artifact_roots=ALLOWED_ROOTS,
            authority={
                "actor": "triage-owner",
                "role": "triage",
                "subject_revision": None,
            },
        )
        pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
        fleet_improvement.validate_initial_record(
            pilot,
            allowed_artifact_roots=ALLOWED_ROOTS,
            authority={
                "actor": "maintainer",
                "role": "human_or_protected_workflow",
                "subject_revision": None,
            },
        )
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "must begin observed",
        ):
            fleet_improvement.validate_initial_record(
                _record("closed"),
                allowed_artifact_roots=ALLOWED_ROOTS,
                authority={
                    "actor": "maintainer",
                    "role": "human_or_protected_workflow",
                    "subject_revision": None,
                },
            )
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "requires human_or_protected_workflow",
        ):
            fleet_improvement.validate_initial_record(
                pilot,
                allowed_artifact_roots=ALLOWED_ROOTS,
                authority={
                    "actor": "triage-owner",
                    "role": "triage",
                    "subject_revision": None,
                },
            )

    def test_duplicate_requires_a_different_linked_record(self) -> None:
        duplicate = _record("duplicate")
        duplicate["related_improvement_id"] = "fi_existing_routing_failure"
        self._validate(duplicate)

        for related in (None, duplicate["improvement_id"]):
            duplicate["related_improvement_id"] = related
            with self.subTest(related=related), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(duplicate)

    def test_unknown_and_missing_fields_fail_closed_recursively(self) -> None:
        for path, key in (
            ((), "unexpected"),
            (("target",), "unexpected"),
            (("observations", 0, "source"), "unexpected"),
            (("attempts", 0, "evaluation"), "unexpected"),
        ):
            record = _record()
            cursor: object = record
            for component in path:
                cursor = cursor[component]  # type: ignore[index]
            cursor[key] = "value"  # type: ignore[index]
            with self.subTest(path=path), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(record)

        record = _record()
        del record["failure_fingerprint"]
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(record)

    def test_credentials_and_raw_transcripts_are_rejected_recursively(self) -> None:
        samples = (
            "password=hunter2",
            "Bearer fakeBearerTokenValue1234567890",
            "ghp_" + "a" * 32,
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "eyJ" + "a" * 12 + "." + "b" * 12 + "." + "c" * 12,
            "AWS_SECRET_ACCESS_KEY=" + "a" * 40,
            "github_pat_" + "a" * 32,
            "AIza" + "a" * 35,
            "sk-proj-" + "a" * 32,
            "Bearer [REDACTED:token]" + "a" * 24,
            "Authorization: Basic " + "a" * 32,
            "Cookie=session_id_" + "a" * 32,
            "AWS_SESSION_TOKEN=" + "a" * 40,
            "AKIA" + "A" * 16,
            "xoxb-" + "a" * 32,
            "sk_live_" + "a" * 32,
            "https://user:cleartext-password@example.invalid/path",
        )
        for sample in samples:
            record = _record()
            record["limitations"].append(sample)  # type: ignore[union-attr]
            with self.subTest(sample=sample), self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "credential-bearing",
            ):
                self._validate(record)

        record = _record()
        record["attempts"][0]["evaluation"]["raw_transcript"] = "model output"  # type: ignore[index]
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(record)

        for safe in (
            "token=[REDACTED:token]",
            "Bearer [REDACTED:token]",
            "https://user:[REDACTED:password]@example.invalid/path",
        ):
            record = _record()
            record["limitations"].append(safe)  # type: ignore[union-attr]
            with self.subTest(safe=safe):
                self._validate(record)

    def test_paths_are_caller_scoped_and_cannot_traverse(self) -> None:
        oversized = _record()
        oversized["target"]["artifact_paths"] = [  # type: ignore[index]
            *(f"agents/generated-{index}.md" for index in range(64)),
            "agents",
        ]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "target.artifact_paths must contain at most 64 entries",
        ):
            self._validate(oversized)

        for path in (
            "../agents/reviewer.md",
            "C:/agents/reviewer.md",
            "/agents/reviewer.md",
            "agents//reviewer.md",
            "agents/./reviewer.md",
            " agents/reviewer.md",
            "agents/reviewer.md ",
            "agents/reviewer md",
            "agents/reviewer@v1.md",
            "agents/reviewer:md",
            "agents/reviewer%20md",
            "agents/reviewer.md?query=1",
            "agents/reviewer.md#fragment",
            "agents/reviewer.md\n",
            "agents\\reviewer.md",
            "agents/",
            "~/.config/reviewer.md",
            ".git/config",
            "agents/.GIT/config",
            "agents/réviewer.md",
            "https://example.invalid/reviewer.md",
        ):
            record = _record()
            record["target"]["artifact_paths"] = [path]  # type: ignore[index]
            with self.subTest(path=path), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(record)

        too_many = _record("observed")
        too_many["target"]["artifact_paths"] = [  # type: ignore[index]
            f"agents/path_{index}.md"
            for index in range(fleet_improvement.MAX_ARTIFACT_PATHS + 1)
        ]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "at most 64 entries",
        ):
            self._validate(too_many)

        record = _record()
        record["target"]["artifact_paths"] = ["docs/unapproved.md"]  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "caller-allowed",
        ):
            self._validate(record)

        for path in (
            "agents/reviewer.md",
            "skills/agent-authoring/references/improvement-lifecycle.md",
            "evals/scenarios/reviewer_case-v1.2.yaml",
        ):
            record = _record()
            record["target"]["artifact_paths"] = [path]  # type: ignore[index]
            with self.subTest(valid_path=path):
                self._validate(record)

    def test_target_pathspec_aggregate_must_fit_portable_git_argv_ceiling(self) -> None:
        record = _record()
        record["target"]["artifact_paths"] = [  # type: ignore[index]
            f"agents/{index:02d}{'a' * 253}/{'b' * 249}"
            for index in range(fleet_improvement.MAX_ARTIFACT_PATHS)
        ]
        self.assertTrue(
            all(
                len(path.encode("utf-8")) == 512
                for path in record["target"]["artifact_paths"]  # type: ignore[index]
            )
        )

        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "artifact_paths.*(?:aggregate|argv|pathspec|portable)|pathspec.*(?:ceiling|limit)",
        ):
            self._validate(record)

    def test_full_tree_paths_must_round_trip_across_supported_hosts(self) -> None:
        for path in (
            "CON",
            "aux.txt",
            "bad:name",
            "trailing.",
            "trailing ",
            ".git/config",
            "git~1/config",
            ".\u200cgit/config",
            "COM\u00b9.txt",
            "decomposed-e\u0301.md",
            "a" * (fleet_improvement.MAX_GIT_COMPONENT_BYTES + 1),
        ):
            with self.subTest(path=path), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                fleet_improvement._portable_git_tree_path(path, "test tree")

        self.assertEqual(
            fleet_improvement._portable_git_tree_path("docs/caf\u00e9.md", "test tree"),
            ("docs", "caf\u00e9.md"),
        )

    def test_full_tree_rejects_null_object_ids_and_dangerous_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(root, {"agents/reviewer.md": "base\n"}, "base")
            agents_tree = _git(root, "rev-parse", f"{base}:agents")

            null_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("40000", "agents", agents_tree)
                    + _raw_tree_entry("160000", "vendor", "0" * 40)
                ),
            )
            null_commit = _git(root, "commit-tree", null_tree, "-p", base, "-m", "null gitlink")
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "null|object contract",
            ):
                fleet_improvement._git_leaf_tree(root, null_commit, "test tree")

            link_blob = _git(
                root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=b"target\n",
            )
            symlink_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("120000", ".gitmodules", link_blob)
                    + _raw_tree_entry("40000", "agents", agents_tree)
                ),
            )
            symlink_commit = _git(
                root,
                "commit-tree",
                symlink_tree,
                "-p",
                base,
                "-m",
                "dangerous symlink",
            )
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "control-file symlink",
            ):
                fleet_improvement._git_leaf_tree(root, symlink_commit, "test tree")

    def test_raw_tree_non_gitlink_entries_require_existing_blob_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(root, {"seed.txt": "ordinary blob\n"}, "seed")
            blob = _git(root, "rev-parse", f"{base}:seed.txt")

            valid_revision = _raw_commit_with_entry(
                root,
                mode="100644",
                path="ordinary.txt",
                object_id=blob,
                message="valid ordinary blob control",
            )
            fleet_improvement._validate_raw_tree_objects(
                root,
                revision=valid_revision,
                namespace={
                    b"ordinary.txt": (b"100644", b"blob", blob.encode("ascii"))
                },
                field="test tree",
            )

            child_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=_raw_tree_entry("100644", "child.txt", blob),
            )
            wrong_type_cases = (
                ("100644", "file-points-to-tree", child_tree),
                ("100755", "executable-points-to-commit", base),
                ("120000", "symlink-points-to-tree", child_tree),
            )
            for mode, path, object_id in wrong_type_cases:
                revision = _raw_commit_with_entry(
                    root,
                    mode=mode,
                    path=path,
                    object_id=object_id,
                    message=path,
                )
                with self.subTest(mode=mode, actual_object=object_id), self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    "(?:blob|object type|object contract|non-gitlink)",
                ):
                    fleet_improvement._validate_raw_tree_objects(
                        root,
                        revision=revision,
                        namespace={
                            path.encode("ascii"): (
                                mode.encode("ascii"),
                                b"blob",
                                object_id.encode("ascii"),
                            )
                        },
                        field="test tree",
                    )

            missing_blob = "f" * len(blob)
            self.assertNotIn(missing_blob, {blob, child_tree, base})
            for mode in ("100644", "100755", "120000"):
                path = f"missing-{mode}"
                revision = _raw_commit_with_entry(
                    root,
                    mode=mode,
                    path=path,
                    object_id=missing_blob,
                    message=path,
                )
                with self.subTest(mode=mode, missing=True), self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    "(?:missing.*(?:blob|object)|(?:blob|object).*missing|existing blob|object contract)",
                ):
                    fleet_improvement._validate_raw_tree_objects(
                        root,
                        revision=revision,
                        namespace={
                            path.encode("ascii"): (
                                mode.encode("ascii"),
                                b"blob",
                                missing_blob.encode("ascii"),
                            )
                        },
                        field="test tree",
                    )

    def test_timestamps_ids_revisions_and_bool_as_int_are_rejected(self) -> None:
        mutations = (
            ("created_at", "2026-07-31T18:36:34+00:00"),
            ("improvement_id", "../escape"),
            ("failure_fingerprint", "ff_short"),
        )
        for key, value in mutations:
            record = _record()
            record[key] = value
            with self.subTest(key=key), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(record)
        record = _record()
        record["budget"]["max_attempts"] = True  # type: ignore[index]
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(record)

        record = _record("observed")
        record["observations"][0]["observed_at"] = "2099-01-01T00:00:00Z"  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "observed_at must not follow updated_at",
        ):
            self._validate(record)

    def test_all_lifecycle_timestamps_require_literal_rfc3339_t_separator(self) -> None:
        timestamp_fields: tuple[
            tuple[str, Callable[[dict[str, object]], tuple[dict[str, object], str]]],
            ...,
        ] = (
            ("created_at", lambda record: (record, "created_at")),
            ("updated_at", lambda record: (record, "updated_at")),
            (
                "observations[0].observed_at",
                lambda record: (record["observations"][0], "observed_at"),  # type: ignore[index,return-value]
            ),
            (
                "reviews[0].reviewed_at",
                lambda record: (record["reviews"][0], "reviewed_at"),  # type: ignore[index,return-value]
            ),
            (
                "merge.merged_at",
                lambda record: (record["merge"], "merged_at"),  # type: ignore[return-value]
            ),
            (
                "monitoring.observed_at",
                lambda record: (record["monitoring"], "observed_at"),  # type: ignore[return-value]
            ),
            (
                "rollback.rolled_back_at",
                lambda record: (record["rollback"], "rolled_back_at"),  # type: ignore[return-value]
            ),
        )
        for field, locate in timestamp_fields:
            for separator in (" ", "_"):
                record = _record("rolled_back")
                container, key = locate(record)
                container[key] = str(container[key]).replace("T", separator, 1)
                with self.subTest(field=field, separator=separator), self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    "RFC3339",
                ):
                    self._validate(record)

    def test_rollback_timestamp_must_not_precede_merge_timestamp(self) -> None:
        record = _record("rolled_back")
        record["monitoring"] = None
        record["evidence_refs"] = [  # type: ignore[index]
            ref
            for ref in record["evidence_refs"]  # type: ignore[index]
            if ref["evidence_id"] != MONITORING_EVIDENCE_ID
        ]
        record["rollback"]["trigger"] = "security_finding"  # type: ignore[index]
        record["rollback"]["reason"] = "A security finding required immediate rollback."  # type: ignore[index]
        record["rollback"]["rolled_back_at"] = "2026-07-31T18:49:59Z"  # type: ignore[index]

        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "rollback.rolled_back_at must not precede merge.merged_at",
        ):
            self._validate(record)

    def test_observation_and_attempt_ids_are_unique(self) -> None:
        record = _record()
        record["observations"].append(copy.deepcopy(record["observations"][0]))  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "duplicate observation event_id",
        ):
            self._validate(record)

        record = _record()
        second = copy.deepcopy(record["attempts"][0])  # type: ignore[index]
        second["iteration"] = 2
        record["attempts"].append(second)  # type: ignore[union-attr]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "duplicate attempt_id",
        ):
            self._validate(record)

    def test_attempt_budget_is_bounded_cumulative_and_sequential(self) -> None:
        record = _record()
        record["budget"]["max_attempts"] = 4  # type: ignore[index]
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(record)

        record = _record()
        record["attempts"][0]["reservation"]["tokens"] = 200001  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "cumulative reserved tokens",
        ):
            self._validate(record)

        record = _record()
        second = copy.deepcopy(record["attempts"][0])  # type: ignore[index]
        second["attempt_id"] = "fa_reviewer_description_v2"
        second["iteration"] = 3
        record["attempts"].append(second)  # type: ignore[union-attr]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "iterations must be sequential",
        ):
            self._validate(record)

        record = _record()
        record["attempts"][0]["actual_usage"]["tokens"] = 12001  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "actual_usage.tokens exceeds reservation.tokens",
        ):
            self._validate(record)

        record = _record("candidate")
        record["attempts"][0]["reservation"]["evaluator_calls"] = 0  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "reservation.evaluator_calls must be >= 1",
        ):
            self._validate(record)

        exhausted = _record("evaluated", result="fail")
        first = exhausted["attempts"][0]  # type: ignore[index]
        first["reservation"]["tokens"] = 12000  # type: ignore[index]
        first["actual_usage"]["tokens"] = 12000  # type: ignore[index]
        first["stop_reason"] = "The first candidate failed."  # type: ignore[index]
        exhausted["budget"]["max_tokens"] = 12000  # type: ignore[index]
        second = copy.deepcopy(first)
        second["attempt_id"] = "fa_reviewer_description_v2"
        second["iteration"] = 2
        second["parent_revision"] = SHA_B
        second["subject_revision"] = SHA_C
        second["subject_sha256"] = DIGEST_C
        second["reservation"]["tokens"] = 1
        second["actual_usage"] = None
        second["evaluation"] = None
        second["outcome"] = "proposed"
        second["stop_reason"] = None
        exhausted["attempts"].append(second)  # type: ignore[union-attr]
        exhausted["status"] = "candidate"
        exhausted["disposition_reason"] = "A second candidate was proposed."
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "cumulative reserved tokens",
        ):
            self._validate(exhausted)

    def test_budget_respects_default_and_caller_supplied_hard_ceilings(self) -> None:
        for field, ceiling in fleet_improvement.DEFAULT_BUDGET_CEILINGS.items():
            record = _record("observed")
            record["budget"][field] = (  # type: ignore[index]
                float(ceiling) + 0.01 if field == "max_cost_usd" else int(ceiling) + 1
            )
            with self.subTest(default_ceiling=field), self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                rf"budget\.{field} exceeds caller policy ceiling",
            ):
                self._validate(record)

        for field in fleet_improvement.DEFAULT_BUDGET_CEILINGS:
            record = _record("observed")
            declared = record["budget"][field]  # type: ignore[index]
            ceilings = dict(fleet_improvement.DEFAULT_BUDGET_CEILINGS)
            ceilings[field] = (  # type: ignore[assignment]
                float(declared) - 0.01
                if field == "max_cost_usd"
                else int(declared) - 1
            )
            with self.subTest(caller_ceiling=field), self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                rf"budget\.{field} exceeds caller policy ceiling",
            ):
                fleet_improvement.validate_record(
                    record,
                    allowed_artifact_roots=ALLOWED_ROOTS,
                    budget_ceilings=ceilings,
                )

        widened = dict(fleet_improvement.DEFAULT_BUDGET_CEILINGS)
        widened["max_tokens"] = int(widened["max_tokens"]) + 1
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "budget_ceilings.max_tokens exceeds the v1 global ceiling",
        ):
            fleet_improvement.validate_record(
                _record("observed"),
                allowed_artifact_roots=ALLOWED_ROOTS,
                budget_ceilings=widened,
            )

    def test_evaluation_actual_usage_is_nonzero_and_covers_trials(self) -> None:
        for field in ("model_turns", "evaluator_calls", "tokens"):
            record = _record()
            record["attempts"][0]["actual_usage"][field] = 2  # type: ignore[index]
            with self.subTest(field=field), self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                rf"actual_usage\.{field} must cover evaluation\.trial_count",
            ):
                self._validate(record)

        record = _record()
        record["attempts"][0]["actual_usage"]["evaluator_calls"] = 0  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "at least one actual evaluator call",
        ):
            self._validate(record)

        record = _record()
        record["attempts"][0]["actual_usage"]["wall_seconds"] = 0  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "actual_usage.wall_seconds must be >= 1",
        ):
            self._validate(record)

    def test_attempt_ancestry_is_bound_to_base_and_previous_subject(self) -> None:
        record = _record()
        record["attempts"][0]["parent_revision"] = SHA_C  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "parent_revision",
        ):
            self._validate(record)

        record = _record()
        first = record["attempts"][0]  # type: ignore[index]
        first["outcome"] = "fail"  # type: ignore[index]
        first["evaluation"]["result"] = "fail"  # type: ignore[index]
        first["stop_reason"] = "First candidate failed."  # type: ignore[index]
        second = copy.deepcopy(first)
        second["attempt_id"] = "fa_reviewer_description_v2"
        second["iteration"] = 2
        second["parent_revision"] = SHA_C
        second["subject_revision"] = SHA_A
        second["evaluation"]["subject_revision"] = SHA_A
        record["attempts"].append(second)  # type: ignore[union-attr]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "previous subject_revision",
        ):
            self._validate(record)

    def test_candidate_and_evaluation_bind_the_exact_subject(self) -> None:
        record = _record()
        record["attempts"][0]["evaluation"]["subject_revision"] = SHA_C  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "subject_revision",
        ):
            self._validate(record)

        record = _record()
        record["attempts"][0]["evaluation"]["evaluator"] = None  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "evaluator is required",
        ):
            self._validate(record)

    def test_fresh_evaluator_and_reviewer_identities_are_independent(self) -> None:
        self_evaluated = _record()
        attempt = self_evaluated["attempts"][0]  # type: ignore[index]
        attempt["evaluation"]["evaluator"] = attempt["author"]["name"]  # type: ignore[index]
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(self_evaluated)

        for identity_source in ("author", "evaluator"):
            self_reviewed = _record("in_review")
            attempt = self_reviewed["attempts"][0]  # type: ignore[index]
            reviewer = (
                attempt["author"]["name"]
                if identity_source == "author"
                else attempt["evaluation"]["evaluator"]
            )
            self_reviewed["reviews"][0]["reviewer"] = reviewer  # type: ignore[index]
            with self.subTest(identity_source=identity_source), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(self_reviewed)

    def test_artifact_selection_digest_uses_committed_bytes_and_requested_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {
                    "agents/reviewer.md": "base reviewer\n",
                    "skills/demo/SKILL.md": "base skill\n",
                },
                "base",
            )
            requested = ["agents/reviewer.md", "skills/demo/SKILL.md"]
            base_digest = fleet_improvement.artifact_selection_sha256(
                root,
                base,
                requested,
            )
            self.assertEqual(
                base_digest,
                fleet_improvement.artifact_selection_sha256(
                    root,
                    base,
                    list(reversed(requested)),
                ),
            )

            subject = _commit_files(
                root,
                {
                    "agents/reviewer.md": "candidate reviewer\n",
                    "skills/demo/SKILL.md": "candidate skill\n",
                },
                "candidate",
            )
            subject_digest = fleet_improvement.artifact_selection_sha256(
                root,
                subject,
                requested,
            )
            self.assertNotEqual(base_digest, subject_digest)
            self.assertNotEqual(
                subject_digest,
                fleet_improvement.artifact_selection_sha256(
                    root,
                    subject,
                    ["agents/reviewer.md"],
                ),
            )

            (root / "agents/reviewer.md").write_text("dirty bytes\n", encoding="utf-8")
            (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
            self.assertEqual(
                subject_digest,
                fleet_improvement.artifact_selection_sha256(root, subject, requested),
            )

    def test_artifact_selection_rejects_non_regular_git_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            _commit_files(root, {"agents/reviewer.md": "candidate\n"}, "base")
            blob = _git(root, "rev-parse", "HEAD:agents/reviewer.md")
            _git(
                root,
                "update-index",
                "--add",
                "--cacheinfo",
                f"120000,{blob},agents/reviewer-link",
            )
            _git(root, "commit", "--quiet", "-m", "add synthetic symlink")
            subject = _git(root, "rev-parse", "HEAD")
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.artifact_selection_sha256(
                    root,
                    subject,
                    ["agents/reviewer-link"],
                )

    def test_artifact_selection_rejects_case_colliding_directory_prefixes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            _commit_files(root, {"seed.txt": "blob bytes\n"}, "seed")
            blob = _git(root, "rev-parse", "HEAD:seed.txt")
            for path in ("skills/demo/Ref/a.md", "skills/demo/ref/b.md"):
                _git(
                    root,
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"100644,{blob},{path}",
                )
            _git(root, "commit", "--quiet", "-m", "case-colliding directory prefixes")
            subject = _git(root, "rev-parse", "HEAD")
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.artifact_selection_sha256(
                    root,
                    subject,
                    ["skills/demo"],
                )

    def test_git_repository_command_rejects_stdout_at_capture_cap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            _commit_files(root, {"agents/reviewer.md": "candidate\n"}, "candidate")
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "stdout",
            ):
                fleet_improvement._git_repository_command(
                    root,
                    ["ls-tree", "-r", "HEAD"],
                    max_stdout_bytes=8,
                )

    def test_git_repository_command_bounds_blocked_stdin_writer(self) -> None:
        release_writer = threading.Event()

        class BlockingStdin:
            def write(self, _value: bytes) -> int:
                release_writer.wait()
                raise BrokenPipeError("fake child never consumed stdin")

            def flush(self) -> None:
                return None

            def close(self) -> None:
                release_writer.set()

        class EmptyStream:
            def read(self, _size: int = -1) -> bytes:
                return b""

            def close(self) -> None:
                return None

        class NonConsumingProcess:
            def __init__(self) -> None:
                self.stdin = BlockingStdin()
                self.stdout = EmptyStream()
                self.stderr = EmptyStream()
                self.returncode: int | None = None
                self.wait_timeouts: list[float | None] = []

            def wait(self, timeout: float | None = None) -> int:
                self.wait_timeouts.append(timeout)
                if self.returncode is None:
                    raise subprocess.TimeoutExpired("fake-git", timeout)
                return self.returncode

            def poll(self) -> int | None:
                return self.returncode

            def kill(self) -> None:
                self.returncode = -9
                release_writer.set()

        process = NonConsumingProcess()
        errors: list[BaseException] = []

        def invoke_query() -> None:
            try:
                fleet_improvement._git_repository_command(
                    Path.cwd(),
                    ["cat-file", "--batch"],
                    input_bytes=b"a" * fleet_improvement.MAX_GIT_INPUT_BYTES,
                )
            except BaseException as exc:  # pragma: no branch - test captures worker outcome
                errors.append(exc)

        with (
            mock.patch.object(fleet_improvement.subprocess, "Popen", return_value=process),
            mock.patch.object(
                fleet_improvement,
                "GIT_COMMAND_TIMEOUT_SECONDS",
                0.05,
                create=True,
            ),
        ):
            worker = threading.Thread(target=invoke_query, daemon=True)
            worker.start()
            worker.join(timeout=0.5)
            completed_within_bound = not worker.is_alive()
            if worker.is_alive():
                process.kill()
                worker.join(timeout=1)

        self.assertTrue(
            completed_within_bound,
            "trusted Git query blocked in the caller while writing to child stdin",
        )
        self.assertFalse(worker.is_alive(), "blocked stdin regression left a worker behind")
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], fleet_improvement.FleetImprovementValidationError)
        self.assertRegex(str(errors[0]), "timed out")
        self.assertTrue(process.wait_timeouts)
        self.assertAlmostEqual(float(process.wait_timeouts[0]), 0.05, places=3)

    def test_every_trusted_git_query_disables_commit_graph_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            revision = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            commands: list[list[str]] = []
            real_popen = subprocess.Popen

            def capture_command(command: list[str], *args: object, **kwargs: object) -> object:
                commands.append(list(command))
                return real_popen(command, *args, **kwargs)

            with mock.patch.object(
                fleet_improvement.subprocess,
                "Popen",
                side_effect=capture_command,
            ):
                fleet_improvement.artifact_selection_sha256(
                    root,
                    revision,
                    ["agents/reviewer.md"],
                )

        self.assertGreaterEqual(len(commands), 3)
        for command in commands:
            with self.subTest(command=command):
                trusted_prefix = command[: command.index("-C")]
                self.assertIn("core.commitGraph=false", trusted_prefix)
                config_index = trusted_prefix.index("core.commitGraph=false")
                self.assertEqual(trusted_prefix[config_index - 1], "-c")

    def test_repository_binding_validates_identity_ancestry_digest_and_touched_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {
                    "agents/reviewer.md": "base\n",
                    "scripts/companion.py": "print('base')\n",
                },
                "base",
            )
            subject = _commit_files(
                root,
                {
                    "agents/reviewer.md": "candidate\n",
                    "scripts/companion.py": "print('generated companion')\n",
                },
                "candidate plus generated companion",
            )
            record = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
            )
            self._validate(record)
            fleet_improvement.validate_repository_binding(
                record,
                repository_root=root,
                expected_repository="latent-sre/sre-agents",
            )

            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    record,
                    repository_root=root,
                    expected_repository="different-owner/different-repository",
                )

            wrong_digest = copy.deepcopy(record)
            wrong_digest["attempts"][0]["subject_sha256"] = DIGEST_A  # type: ignore[index]
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    wrong_digest,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

            _git(root, "checkout", "--quiet", "--detach", base)
            sibling = _commit_files(
                root,
                {"agents/reviewer.md": "sibling candidate\n"},
                "sibling candidate",
            )
            sibling_record = _repository_bound_record(
                root,
                base_revision=subject,
                subject_revision=sibling,
                artifact_paths=["agents/reviewer.md"],
            )
            self._validate(sibling_record)
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    sibling_record,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

            untouched = _commit_files(
                root,
                {"scripts/companion.py": "print('only companion changed')\n"},
                "unrelated companion only",
            )
            untouched_record = _repository_bound_record(
                root,
                base_revision=sibling,
                subject_revision=untouched,
                artifact_paths=["agents/reviewer.md"],
            )
            self._validate(untouched_record)
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    untouched_record,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_accepts_regular_encoded_terminal_lesson_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            record, record_revision = _closed_record_with_lesson_entry(root, "regular")
            self._validate(record)

            fleet_improvement.validate_repository_binding(
                record,
                repository_root=root,
                expected_repository="latent-sre/sre-agents",
                record_revision=record_revision,
            )

    def test_repository_binding_rejects_unbound_encoded_terminal_lesson_entries(self) -> None:
        for entry_kind in ("missing", "directory", "symlink", "gitlink"):
            with self.subTest(entry_kind=entry_kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _init_git_repository(root)
                record, record_revision = _closed_record_with_lesson_entry(root, entry_kind)
                self._validate(record)

                with self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    "lesson.control_path.*(?:missing|regular|blob|linked|gitlink|symlink)",
                ):
                    fleet_improvement.validate_repository_binding(
                        record,
                        repository_root=root,
                        expected_repository="latent-sre/sre-agents",
                        record_revision=record_revision,
                    )

    def test_repository_binding_ignores_legacy_grafts_that_forge_ancestry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "unrelated B",
            )
            (root / "agents/reviewer.md").write_text("candidate\n", encoding="utf-8")
            _git(root, "add", "--", "agents/reviewer.md")
            candidate_tree = _git(root, "write-tree")
            subject = _git(
                root,
                "commit-tree",
                candidate_tree,
                "-m",
                "unrelated C",
            )
            git_directory = Path(_git(root, "rev-parse", "--git-dir"))
            if not git_directory.is_absolute():
                git_directory = root / git_directory
            graft_file = git_directory / "info/grafts"
            graft_file.parent.mkdir(parents=True, exist_ok=True)
            graft_file.write_text(f"{subject} {base}\n", encoding="ascii", newline="\n")

            _git(root, "merge-base", "--is-ancestor", base, subject)

            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "Git ancestry",
            ):
                fleet_improvement._require_ancestor(
                    root,
                    base,
                    subject,
                    "grafted subject",
                )

            forged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
            )
            self._validate(forged)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "Git ancestry",
            ):
                fleet_improvement.validate_repository_binding(
                    forged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_accepts_only_exact_or_digest_preserving_merge_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {
                    "agents/reviewer.md": "base\n",
                    "scripts/mainline.py": "print('base')\n",
                },
                "base",
            )
            main_branch = _git(root, "branch", "--show-current")
            _git(root, "checkout", "--quiet", "-b", "candidate")
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            subject_tree = _git(root, "rev-parse", f"{subject}^{{tree}}")
            premerge_ledger = _git(
                root,
                "commit-tree",
                subject_tree,
                "-p",
                subject,
                "-m",
                "ledger before promotion",
            )

            exact = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=subject,
            )
            self._validate(exact)
            fleet_improvement.validate_repository_binding(
                exact,
                repository_root=root,
                expected_repository="latent-sre/sre-agents",
                record_revision=subject,
            )

            _git(root, "checkout", "--quiet", main_branch)
            mainline = _commit_files(
                root,
                {"scripts/mainline.py": "print('mainline advanced')\n"},
                "advance mainline",
            )
            _git(root, "merge", "--quiet", "--no-ff", "-m", "promote candidate", "candidate")
            merge_revision = _git(root, "rev-parse", "HEAD")
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)
            ledger_after_merge = _commit_files(
                root,
                {"scripts/merge-ledger.txt": "merged\n"},
                "record merged transition",
            )
            fleet_improvement.validate_repository_binding(
                merged,
                repository_root=root,
                expected_repository="latent-sre/sre-agents",
                record_revision=ledger_after_merge,
            )

            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                    record_revision=premerge_ledger,
                )

            later_descendant = copy.deepcopy(merged)
            later_descendant["merge"]["merge_revision"] = ledger_after_merge  # type: ignore[index]
            self._validate(later_descendant)
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    later_descendant,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

            _git(root, "checkout", "--quiet", "--detach", mainline)
            (root / "agents/reviewer.md").write_text(
                "conflict-modified target\n",
                encoding="utf-8",
            )
            _git(root, "add", "--", "agents/reviewer.md")
            conflict_tree = _git(root, "write-tree")
            conflict_merge = _git(
                root,
                "commit-tree",
                conflict_tree,
                "-p",
                mainline,
                "-p",
                subject,
                "-m",
                "conflict-modified merge",
            )
            conflict_modified = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=conflict_merge,
            )
            self._validate(conflict_modified)
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    conflict_modified,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_requires_rollback_to_restore_base_and_precede_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {
                    "agents/reviewer.md": "base\n",
                    "scripts/rollback-ledger.txt": "base\n",
                },
                "base",
            )
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            restored = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "restore base artifact",
            )
            ledger_after_rollback = _commit_files(
                root,
                {"scripts/rollback-ledger.txt": "rolled back\n"},
                "record rollback transition",
            )
            _git(root, "checkout", "--quiet", "--detach", subject)
            non_restoring = _commit_files(
                root,
                {"agents/reviewer.md": "still not base\n"},
                "non-restoring rollback",
            )

            rolled_back = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=subject,
                rollback_revision=restored,
            )
            self._validate(rolled_back)
            fleet_improvement.validate_repository_binding(
                rolled_back,
                repository_root=root,
                expected_repository="latent-sre/sre-agents",
                record_revision=ledger_after_rollback,
            )

            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    rolled_back,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                    record_revision=non_restoring,
                )

            invalid_rollback = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=subject,
                rollback_revision=non_restoring,
            )
            self._validate(invalid_rollback)
            with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
                fleet_improvement.validate_repository_binding(
                    invalid_rollback,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                    record_revision=non_restoring,
                )

    def test_repository_binding_rejects_rollback_only_file_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            rollback_revision = _commit_files(
                root,
                {
                    "agents/reviewer.md": "base\n",
                    "scripts/injected.py": "print('rollback-only injection')\n",
                },
                "restore target and inject unrelated file",
            )
            rolled_back = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=subject,
                rollback_revision=rollback_revision,
            )
            self._validate(rolled_back)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "rollback",
            ):
                fleet_improvement.validate_repository_binding(
                    rolled_back,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_accepts_two_parent_rollback_application_merge(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            (
                base,
                subject,
                rollback_subject,
                application_integration,
                application_merge,
            ) = _two_parent_rollback_application(root)
            self.assertEqual(
                _git(root, "rev-list", "--parents", "-n", "1", application_merge).split(),
                [application_merge, application_integration, rollback_subject],
            )
            rolled_back = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=subject,
                rollback_revision=application_merge,
            )
            self._validate(rolled_back)

            fleet_improvement.validate_repository_binding(
                rolled_back,
                repository_root=root,
                expected_repository="latent-sre/sre-agents",
            )

    def test_repository_binding_rejects_injected_two_parent_rollback_application_merge(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base, subject, _, _, application_merge = _two_parent_rollback_application(
                root,
                application_files={
                    "scripts/injected.py": "print('application-only injection')\n"
                },
            )
            rolled_back = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=subject,
                rollback_revision=application_merge,
            )
            self._validate(rolled_back)

            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "rollback application must contain exactly one provable revert subject",
            ):
                fleet_improvement.validate_repository_binding(
                    rolled_back,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_stale_rollback_after_target_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            _commit_files(
                root,
                {"agents/reviewer.md": "post-merge target drift\n"},
                "target drifts before rollback",
            )
            stale_rollback = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "stale rollback restores old base",
            )
            rolled_back = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=subject,
                rollback_revision=stale_rollback,
            )
            self._validate(rolled_back)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "rollback",
            ):
                fleet_improvement.validate_repository_binding(
                    rolled_back,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_merge_that_masks_integration_parent_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            main_branch = _git(root, "branch", "--show-current")
            _git(root, "checkout", "--quiet", "-b", "candidate")
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            _git(root, "checkout", "--quiet", main_branch)
            integration_parent = _commit_files(
                root,
                {"agents/reviewer.md": "integration drift\n"},
                "integration target drift",
            )
            candidate_tree = _git(root, "rev-parse", f"{subject}^{{tree}}")
            merge_revision = _git(
                root,
                "commit-tree",
                candidate_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "resolve drift to candidate bytes",
            )
            _git(root, "checkout", "--quiet", "--detach", merge_revision)
            rollback_revision = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "restore stale base bytes",
            )
            rolled_back = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="rolled_back",
                merge_revision=merge_revision,
                rollback_revision=rollback_revision,
            )
            self._validate(rolled_back)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "merge",
            ):
                fleet_improvement.validate_repository_binding(
                    rolled_back,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_requires_declared_base_to_be_actual_unique_merge_base(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {
                    "agents/reviewer.md": "base target\n",
                    "scripts/x.txt": "base x\n",
                },
                "base B",
            )
            _commit_files(
                root,
                {"scripts/x.txt": "shared C x\n"},
                "shared C changes x",
            )
            shared_branch = _git(root, "branch", "--show-current")
            _git(root, "checkout", "--quiet", "-b", "candidate")
            subject = _commit_files(
                root,
                {
                    "agents/reviewer.md": "reviewed target\n",
                    "scripts/x.txt": "base x\n",
                },
                "subject reverts x and changes target",
            )
            _git(root, "checkout", "--quiet", shared_branch)
            integration_parent = _commit_files(
                root,
                {"scripts/x.txt": "integration x\n"},
                "integration changes x again",
            )
            (root / "agents/reviewer.md").write_text(
                "reviewed target\n",
                encoding="utf-8",
            )
            _git(root, "add", "--", "agents/reviewer.md")
            merge_tree = _git(root, "write-tree")
            merge_revision = _git(
                root,
                "commit-tree",
                merge_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "merge using declared B instead of actual C",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "unique actual merge base",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_unrelated_integration_parent_with_base_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            base_tree = _git(root, "rev-parse", f"{base}^{{tree}}")
            unrelated_integration_parent = _git(
                root,
                "commit-tree",
                base_tree,
                "-m",
                "unrelated integration root with base bytes",
            )
            subject_tree = _git(root, "rev-parse", f"{subject}^{{tree}}")
            merge_revision = _git(
                root,
                "commit-tree",
                subject_tree,
                "-p",
                unrelated_integration_parent,
                "-p",
                subject,
                "-m",
                "merge reviewed candidate into unrelated integration root",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "merge integration parent",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_merge_only_file_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            main_branch = _git(root, "branch", "--show-current")
            _git(root, "checkout", "--quiet", "-b", "candidate")
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            _git(root, "checkout", "--quiet", main_branch)
            integration_parent = _commit_files(
                root,
                {"scripts/mainline.py": "print('integration parent')\n"},
                "advance integration parent",
            )
            (root / "agents/reviewer.md").write_text("candidate\n", encoding="utf-8")
            (root / "scripts/injected.py").write_text(
                "print('merge-only injection')\n",
                encoding="utf-8",
            )
            _git(root, "add", "--", "agents/reviewer.md", "scripts/injected.py")
            injected_tree = _git(root, "write-tree")
            merge_revision = _git(
                root,
                "commit-tree",
                injected_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "inject merge-only file",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "merge",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_merge_only_empty_tree_injection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            (
                base,
                subject,
                integration_parent,
                candidate_agents_tree,
                integration_scripts_tree,
            ) = _two_parent_merge_components(root)
            empty_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=b"",
            )
            injected_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("40000", "agents", candidate_agents_tree)
                    + _raw_tree_entry("40000", "empty", empty_tree)
                    + _raw_tree_entry("40000", "scripts", integration_scripts_tree)
                ),
            )
            merge_revision = _git(
                root,
                "commit-tree",
                injected_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "inject merge-only empty tree",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)

            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "empty.*tree|tree.*empty",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_raw_unsorted_merge_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            (
                base,
                subject,
                integration_parent,
                candidate_agents_tree,
                integration_scripts_tree,
            ) = _two_parent_merge_components(root)
            unsorted_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("40000", "scripts", integration_scripts_tree)
                    + _raw_tree_entry("40000", "agents", candidate_agents_tree)
                ),
            )
            merge_revision = _git(
                root,
                "commit-tree",
                unsorted_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "raw-unsorted object-only merge",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)

            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "unsorted raw tree entries",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_raw_file_directory_merge_namespace_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            main_branch = _git(root, "branch", "--show-current")
            _git(root, "checkout", "--quiet", "-b", "candidate")
            subject = _commit_files(
                root,
                {"agents/reviewer.md": "candidate\n"},
                "candidate",
            )
            _git(root, "checkout", "--quiet", main_branch)
            integration_parent = _commit_files(
                root,
                {"scripts/mainline.py": "print('integration')\n"},
                "advance integration",
            )

            blob = _git(
                root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=b"blob a\n",
            )
            child_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=_raw_tree_entry("100644", "b", blob),
            )
            agents_tree = _git(root, "rev-parse", f"{subject}:agents")
            malformed_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("100644", "a", blob)
                    + _raw_tree_entry("40000", "a", child_tree)
                    + _raw_tree_entry("40000", "agents", agents_tree)
                ),
            )
            merge_revision = _git(
                root,
                "commit-tree",
                malformed_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "malformed file and directory merge namespace",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "merge result tree.*(?:malformed|duplicate|namespace conflict)",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_repository_binding_rejects_case_colliding_merge_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _init_git_repository(root)
            base = _commit_files(
                root,
                {"agents/reviewer.md": "base\n"},
                "base",
            )
            base_agents = _git(root, "rev-parse", f"{base}:agents")
            candidate_blob = _git(
                root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=b"candidate\n",
            )
            candidate_agents = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=_raw_tree_entry("100644", "reviewer.md", candidate_blob),
            )
            upper_blob = _git(
                root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=b"upper\n",
            )
            lower_blob = _git(
                root,
                "hash-object",
                "-w",
                "--stdin",
                input_bytes=b"lower\n",
            )
            subject_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("100644", "a", lower_blob)
                    + _raw_tree_entry("40000", "agents", candidate_agents)
                ),
            )
            subject = _git(
                root,
                "commit-tree",
                subject_tree,
                "-p",
                base,
                "-m",
                "reviewed subject with lowercase path",
            )
            integration_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("100644", "A", upper_blob)
                    + _raw_tree_entry("40000", "agents", base_agents)
                ),
            )
            integration_parent = _git(
                root,
                "commit-tree",
                integration_tree,
                "-p",
                base,
                "-m",
                "integration parent with uppercase path",
            )
            merge_tree = _git(
                root,
                "hash-object",
                "-t",
                "tree",
                "--literally",
                "-w",
                "--stdin",
                input_bytes=(
                    _raw_tree_entry("100644", "A", upper_blob)
                    + _raw_tree_entry("100644", "a", lower_blob)
                    + _raw_tree_entry("40000", "agents", candidate_agents)
                ),
            )
            merge_revision = _git(
                root,
                "commit-tree",
                merge_tree,
                "-p",
                integration_parent,
                "-p",
                subject,
                "-m",
                "case-colliding merge namespace",
            )
            merged = _repository_bound_record(
                root,
                base_revision=base,
                subject_revision=subject,
                artifact_paths=["agents/reviewer.md"],
                status="merged",
                merge_revision=merge_revision,
            )
            self._validate(merged)
            with self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "case-colliding",
            ):
                fleet_improvement.validate_repository_binding(
                    merged,
                    repository_root=root,
                    expected_repository="latent-sre/sre-agents",
                )

    def test_visible_sets_are_not_claimed_as_hidden(self) -> None:
        record = _record()
        record["attempts"][0]["case_sets"]["hidden"] = {  # type: ignore[index]
            "case_ids": ["secret-case"],
        }
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(record)

        record = _record()
        record["attempts"][0]["case_sets"]["shadow"] = {  # type: ignore[index]
            "sha256": DIGEST_C,
            "case_count": 2,
            "result": "pass",
            "evidence_id": MONITORING_EVIDENCE_ID,
            "case_ids": ["must-not-leak"],
        }
        with self.assertRaises(fleet_improvement.FleetImprovementValidationError):
            self._validate(record)

    def test_fail_inconclusive_or_regression_cannot_enter_review(self) -> None:
        for result in ("fail", "inconclusive", "skip"):
            record = _record("in_review", result=result)
            with self.subTest(result=result), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(record)

    def test_latest_nonpassing_shadow_blocks_review_and_every_promoted_state(self) -> None:
        for status in ("in_review", "merged", "monitoring", "closed", "rolled_back"):
            for shadow_result in ("fail", "inconclusive"):
                record = _record(status)
                latest = record["attempts"][-1]  # type: ignore[index]
                latest["case_sets"]["shadow"] = {  # type: ignore[index]
                    "sha256": DIGEST_D,
                    "case_count": 2,
                    "result": shadow_result,
                    "evidence_id": SHADOW_EVIDENCE_ID,
                }
                record["evidence_refs"].append(  # type: ignore[union-attr]
                    _evidence_ref(SHADOW_EVIDENCE_ID, DIGEST_D)
                )

                with self.subTest(status=status, shadow_result=shadow_result), self.assertRaisesRegex(
                    fleet_improvement.FleetImprovementValidationError,
                    "shadow.*(?:pass|fail|inconclusive|promotion|promoted|review)",
                ):
                    self._validate(record)

    def test_historical_usage_may_be_unknown_but_cannot_promote(self) -> None:
        historical = _record("rejected", result="fail")
        attempt = historical["attempts"][0]  # type: ignore[index]
        attempt["evaluation"]["kind"] = "historical_report"  # type: ignore[index]
        attempt["evaluation"]["evidence_id"] = OBSERVATION_EVIDENCE_ID  # type: ignore[index]
        attempt["evaluation"]["locator"] = "evals/baselines/historical-report.md"  # type: ignore[index]
        attempt["evaluation"]["sha256"] = DIGEST_A  # type: ignore[index]
        attempt["subject_revision"] = None  # type: ignore[index]
        attempt["subject_sha256"] = None  # type: ignore[index]
        attempt["evaluation"]["subject_revision"] = None  # type: ignore[index]
        attempt["evaluation"]["runner_sha256"] = None  # type: ignore[index]
        historical["budget"]["origin"] = "retrospective_import"  # type: ignore[index]
        attempt["reservation"] = None  # type: ignore[index]
        attempt["actual_usage"] = None  # type: ignore[index]
        historical["evidence_refs"] = [
            {
                "evidence_id": OBSERVATION_EVIDENCE_ID,
                "kind": "historical_report",
                "locator": "evals/baselines/historical-report.md",
                "sha256": DIGEST_A,
            }
        ]
        self._validate(historical)

        promoted = _record("in_review")
        attempt = promoted["attempts"][0]  # type: ignore[index]
        attempt["evaluation"]["kind"] = "historical_report"  # type: ignore[index]
        attempt["evaluation"]["evidence_id"] = OBSERVATION_EVIDENCE_ID  # type: ignore[index]
        attempt["evaluation"]["locator"] = "evals/baselines/historical-report.md"  # type: ignore[index]
        attempt["evaluation"]["sha256"] = DIGEST_A  # type: ignore[index]
        attempt["evaluation"]["runner_sha256"] = None  # type: ignore[index]
        attempt["reservation"] = None  # type: ignore[index]
        attempt["actual_usage"] = None  # type: ignore[index]
        promoted["evidence_refs"] = [
            {
                "evidence_id": OBSERVATION_EVIDENCE_ID,
                "kind": "historical_report",
                "locator": "evals/baselines/historical-report.md",
                "sha256": DIGEST_A,
            },
            _evidence_ref(REVIEW_EVIDENCE_ID, DIGEST_C),
        ]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "historical_report references",
        ):
            self._validate(promoted)
        for key in ("safety_regression", "authority_regression"):
            record = _record("in_review")
            record["attempts"][0]["evaluation"][key] = True  # type: ignore[index]
            with self.subTest(key=key), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(record)

    def test_merge_monitoring_closeout_and_rollback_are_evidence_bound(self) -> None:
        for status in ("merged", "monitoring", "closed", "rolled_back"):
            record = _record(status)
            record["merge"]["subject_revision"] = SHA_C  # type: ignore[index]
            with self.subTest(status=status), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._validate(record)

        record = _record("monitoring")
        record["monitoring"]["subject_revision"] = SHA_B  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "monitoring.subject_revision",
        ):
            self._validate(record)

        record = _record("rolled_back")
        record["rollback"]["merge_revision"] = SHA_D  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "rollback.merge_revision",
        ):
            self._validate(record)

        direct = _record("rolled_back")
        direct["monitoring"] = None
        direct["evidence_refs"] = [  # type: ignore[index]
            ref
            for ref in direct["evidence_refs"]  # type: ignore[index]
            if ref["evidence_id"] != MONITORING_EVIDENCE_ID
        ]
        direct["rollback"]["trigger"] = "security_finding"  # type: ignore[index]
        direct["rollback"]["reason"] = "Independent review found a material security issue."  # type: ignore[index]
        self._validate(direct)

        unplanned = copy.deepcopy(direct)
        unplanned["rollback"]["trigger"] = "manual_owner_decision"  # type: ignore[index]
        unplanned["monitoring_plan"]["rollback_triggers"].remove(  # type: ignore[index]
            "manual_owner_decision"
        )
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "rollback.trigger was not declared in monitoring_plan.rollback_triggers",
        ):
            self._validate(unplanned)

    def test_rollback_preserves_prior_monitoring_but_cannot_manufacture_it(self) -> None:
        monitoring = _record("monitoring")
        for trigger in ("security_finding", "authority_revoked", "merge_error"):
            rolled_back = _record("rolled_back")
            rolled_back["monitoring"]["result"] = "pass"  # type: ignore[index]
            rolled_back["rollback"]["trigger"] = trigger  # type: ignore[index]
            rolled_back["rollback"]["reason"] = (  # type: ignore[index]
                f"The declared {trigger} trigger required rollback after monitoring passed."
            )
            with self.subTest(prior_monitoring=trigger):
                self._transition(
                    monitoring,
                    rolled_back,
                    "human_or_protected_workflow",
                    actor="maintainer",
                )

        merged = _record("merged")
        manufactured = _record("rolled_back")
        manufactured["monitoring"]["result"] = "pass"  # type: ignore[index]
        manufactured["rollback"]["trigger"] = "security_finding"  # type: ignore[index]
        manufactured["rollback"]["reason"] = (  # type: ignore[index]
            "A direct rollback must not manufacture a monitoring observation."
        )
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "merged.*rolled_back.*monitoring|manufacture monitoring",
        ):
            self._transition(
                merged,
                manufactured,
                "human_or_protected_workflow",
                actor="maintainer",
            )

    def test_monitoring_triggered_rollback_requires_distinct_monitoring_transition(self) -> None:
        for trigger, result in (
            ("monitoring_fail", "fail"),
            ("monitoring_inconclusive", "inconclusive"),
        ):
            merged = _record("merged")
            monitoring = _record("monitoring")
            monitoring["monitoring"]["result"] = result  # type: ignore[index]
            rolled_back = _record("rolled_back")
            rolled_back["monitoring"]["result"] = result  # type: ignore[index]
            rolled_back["rollback"]["trigger"] = trigger  # type: ignore[index]
            rolled_back["rollback"]["reason"] = (  # type: ignore[index]
                f"The retained monitoring result {result} activated {trigger}."
            )

            with self.subTest(trigger=trigger, path="distinct-monitoring"):
                self._transition(
                    merged,
                    monitoring,
                    "evaluator",
                    actor="protected-monitor",
                )
                self._transition(
                    monitoring,
                    rolled_back,
                    "human_or_protected_workflow",
                    actor="maintainer",
                )

            direct = _record("rolled_back")
            direct["monitoring"]["result"] = result  # type: ignore[index]
            direct["rollback"]["trigger"] = trigger  # type: ignore[index]
            direct["rollback"]["reason"] = (  # type: ignore[index]
                "A direct merged-to-rolled_back transition cannot append this observation."
            )
            with self.subTest(trigger=trigger, path="direct"), self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                "must not add monitoring evidence.*distinct monitoring transition",
            ):
                self._transition(
                    _record("merged"),
                    direct,
                    "human_or_protected_workflow",
                    actor="maintainer",
                )

    def test_accepted_owner_and_evidence_history_are_immutable(self) -> None:
        mutations = (
            lambda record: record["owner"].update({"name": "replacement-team"}),
            lambda record: record["reviews"][0].update({"reviewer": "replacement-reviewer"}),
            lambda record: record["merge"].update({"merged_by": "replacement-maintainer"}),
            lambda record: record["monitoring"].update({"evidence_ids": ["ev_" + "2" * 32]}),
        )
        for mutate in mutations:
            before = _record("monitoring")
            after = _record("closed")
            mutate(after)
            with self.subTest(mutate=mutate), self.assertRaises(
                fleet_improvement.FleetImprovementValidationError
            ):
                self._transition(before, after, "human_or_protected_workflow")

        record = _record("closed")
        record["lesson"] = {
            "status": "pending",
            "control_path": None,
            "reason": "Not moved left.",
        }
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "lesson",
        ):
            self._validate(record)

    def test_changes_requested_requires_a_separate_author_retry_transition(self) -> None:
        evaluated = _record("evaluated")
        changes_requested = _record("in_review")
        changes_requested["reviews"][0]["verdict"] = "changes_requested"  # type: ignore[index]
        changes_requested["disposition_reason"] = "Independent review requested a revision."
        self._transition(evaluated, changes_requested, "reviewer")

        retry = copy.deepcopy(changes_requested)
        second = _attempt(evaluation=False)
        second["attempt_id"] = "fa_reviewer_description_v2"
        second["iteration"] = 2
        second["parent_revision"] = SHA_B
        second["subject_revision"] = SHA_C
        second["subject_sha256"] = DIGEST_C
        retry["attempts"].append(second)  # type: ignore[union-attr]
        retry["status"] = "candidate"
        retry["disposition_reason"] = "The author prepared a separate reviewed retry."
        self._transition(changes_requested, retry, "author")

        combined = copy.deepcopy(retry)
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "review verdict and next candidate attempt require separate transitions",
        ):
            self._transition(evaluated, combined, "author")

    def test_in_review_changes_requested_may_transition_to_rejected(self) -> None:
        changes_requested = _record("in_review")
        changes_requested["reviews"][0]["verdict"] = "changes_requested"  # type: ignore[index]
        rejected = copy.deepcopy(changes_requested)
        rejected["status"] = "rejected"
        rejected["disposition_reason"] = "The owner accepted the independent rejection."
        rejected["lesson"] = {
            "status": "encoded",
            "control_path": "evals/scenarios/agent-direct-reviewer-authz-block.yaml",
            "reason": "Retain the review finding as regression coverage.",
        }
        self._transition(changes_requested, rejected, "reviewer")

        passing_review = _record("in_review")
        unsupported_rejection = copy.deepcopy(passing_review)
        unsupported_rejection["status"] = "rejected"
        unsupported_rejection["disposition_reason"] = "Unsupported rejection."
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "rejected requires failed/inconclusive evidence or changes requested",
        ):
            self._transition(passing_review, unsupported_rejection, "reviewer")

    def test_transition_artifact_identities_must_match_the_caller_actor(self) -> None:
        cases = (
            (
                "author",
                _record("qualified"),
                _record("candidate"),
                "author",
                "attempt.author.name",
            ),
            (
                "evaluator",
                _record("candidate"),
                _record("evaluated"),
                "evaluator",
                "evaluation.evaluator",
            ),
            (
                "reviewer",
                _record("evaluated"),
                _record("in_review"),
                "reviewer",
                "review.reviewer",
            ),
            (
                "merger",
                _record("in_review"),
                _record("merged"),
                "human_or_protected_workflow",
                "merge.merged_by",
            ),
            (
                "monitor",
                _record("merged"),
                _record("monitoring"),
                "evaluator",
                "monitoring.observed_by",
            ),
        )
        for label, previous, current, role, expected in cases:
            with self.subTest(label=label), self.assertRaisesRegex(
                fleet_improvement.FleetImprovementValidationError,
                expected,
            ):
                self._transition(previous, current, role, actor="different-actor")

        merged = _record("merged")
        direct_rollback = _record("rolled_back")
        direct_rollback["monitoring"] = None
        direct_rollback["evidence_refs"] = [  # type: ignore[index]
            ref
            for ref in direct_rollback["evidence_refs"]  # type: ignore[index]
            if ref["evidence_id"] != MONITORING_EVIDENCE_ID
        ]
        direct_rollback["rollback"]["trigger"] = "security_finding"  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "rollback.rolled_back_by",
        ):
            self._transition(
                merged,
                direct_rollback,
                "human_or_protected_workflow",
                actor="different-actor",
            )

    def test_legal_transition_requires_external_role_and_exact_subject(self) -> None:
        observed = _record("observed")
        qualified = _record("qualified")
        self._transition(observed, qualified, "triage")

        candidate = _record("candidate")
        self._transition(qualified, candidate, "author")

        evaluated = _record("evaluated")
        self._transition(candidate, evaluated, "evaluator")

        in_review = _record("in_review")
        self._transition(evaluated, in_review, "reviewer")

        merged = _record("merged")
        self._transition(in_review, merged, "human_or_protected_workflow")

        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "authority role",
        ):
            self._transition(in_review, merged, "author")

        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "authority subject_revision",
        ):
            fleet_improvement.validate_transition(
                in_review,
                merged,
                allowed_artifact_roots=ALLOWED_ROOTS,
                authority={
                    "actor": "maintainer",
                    "role": "human_or_protected_workflow",
                    "subject_revision": SHA_C,
                },
            )

    def test_illegal_or_terminal_transition_and_prefix_rewrites_fail(self) -> None:
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "illegal status transition",
        ):
            self._transition(_record("observed"), _record("merged"), "human_or_protected_workflow")

        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "terminal",
        ):
            self._transition(_record("rejected", result="fail"), _record("qualified"), "triage")

        before = _record("evaluated")
        after = _record("in_review")
        after["observations"][0]["summary"] = "Rewritten history"  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "observations are append-only",
        ):
            self._transition(before, after, "reviewer")

    def test_evaluating_latest_attempt_may_fill_only_evaluation_fields(self) -> None:
        candidate = _record("candidate")
        evaluated = _record("evaluated")
        self._transition(candidate, evaluated, "evaluator")

        rewritten = _record("evaluated")
        rewritten["attempts"][0]["change_summary"] = "Changed after evaluation"  # type: ignore[index]
        with self.assertRaisesRegex(
            fleet_improvement.FleetImprovementValidationError,
            "attempt identity changed",
        ):
            self._transition(candidate, rewritten, "evaluator")


if __name__ == "__main__":
    unittest.main(verbosity=2)
