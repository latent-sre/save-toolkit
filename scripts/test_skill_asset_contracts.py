"""Focused regressions for executable skill starter contracts."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _indented_block(text: str, header: str) -> str:
    """Return the lines owned by an exact YAML-like header."""
    lines = text.splitlines()
    start = lines.index(header)
    header_indent = len(header) - len(header.lstrip())
    block = [header]
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= header_indent:
            break
        block.append(line)
    return "\n".join(block)


def _fenced_block_after(text: str, marker: str, language: str) -> str:
    """Return the first fenced block of `language` following `marker`."""
    section = text.split(marker, 1)[1]
    return section.split(f"```{language}", 1)[1].split("```", 1)[0]


class SkillAssetContractTests(unittest.TestCase):
    def test_service_readiness_context_requirements_match_resolver_contract(self) -> None:
        sidecar_path = ROOT / "skills/service-readiness-audit/context-requirements.yaml"
        document = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))

        # The sre-context requirements schema remains authoritative. This assertion pins only the
        # generic paths and budgets selected by this consumer for resolver v1alpha1.0.
        self.assertEqual(
            document,
            {
                "apiVersion": "sre-context/requirements/v1alpha1",
                "kind": "ContextRequirements",
                "metadata": {"id": "service-readiness-audit"},
                "spec": {
                    "required": [
                        "/target/team/id",
                        "/target/service/id",
                        "/target/environment/id",
                        "/target/deployment",
                        "/resources/repositories",
                    ],
                    "optional": [
                        "/resources/runbooks",
                        "/resources/observability",
                    ],
                    "alternatives": [
                        {
                            "id": "health-authority",
                            "anyOf": ["/resources/health", "/resources/slo"],
                        }
                    ],
                    "maxDepth": 6,
                    "maxBytes": 65536,
                },
            },
            "service-readiness-audit requirements must stay generic and match "
            "sre-context-resolver/v1alpha1.0",
        )

    def test_backend_openapi_starter_separates_liveness_and_readiness(self) -> None:
        starter = (ROOT / "skills/backend-craft/assets/openapi.starter.yaml").read_text(
            encoding="utf-8"
        )
        liveness = _indented_block(starter, "  /healthz:")
        readiness = _indented_block(starter, "  /readyz:")

        self.assertIn("summary: Liveness probe", liveness)
        self.assertNotIn("Readiness probe", liveness)
        self.assertIn("summary: Readiness probe", readiness)
        self.assertNotIn("Liveness probe", readiness)
        active_response_codes = re.findall(
            r'(?m)^        "([0-9]{3})":', readiness
        )
        self.assertEqual(active_response_codes, ["200", "503"])

    def test_backend_openapi_starter_matches_the_skill_error_and_ratelimit_contract(
        self,
    ) -> None:
        """The starter must embody what SKILL.md declares contract, not a subset of it.

        Two fields drifted out of the starter while SKILL.md kept asserting them: `request_id`,
        which SKILL.md names a defined problem+json extension and shows in its worked example, and
        the `429` + `Retry-After` pair SKILL.md requires of anything exposed. A builder copying the
        starter silently shipped an API with no log correlation and no documented rate-limit
        response, so the two files are pinned together here.
        """
        skill = (ROOT / "skills/backend-craft/SKILL.md").read_text(encoding="utf-8")
        starter = yaml.safe_load(
            (ROOT / "skills/backend-craft/assets/openapi.starter.yaml").read_text(
                encoding="utf-8"
            )
        )
        problem = starter["components"]["schemas"]["Problem"]["properties"]
        rate_limited = starter["components"]["responses"]["RateLimited"]

        self.assertIn("request_id", skill)
        self.assertIn(
            "request_id",
            problem,
            "SKILL.md declares request_id a problem+json extension; the starter must carry it",
        )
        self.assertIn("Retry-After", skill)
        self.assertTrue(
            rate_limited["headers"]["Retry-After"]["required"],
            "SKILL.md requires Retry-After on a 429; the starter must mark it required",
        )
        served = {
            code
            for operation in starter["paths"]["/incidents"].values()
            for code in operation["responses"]
        }
        self.assertIn(
            "429",
            served,
            "a rate-limited API documents its 429 on the operations that can return it",
        )

    def test_reusable_ci_concurrency_is_scoped_to_the_workflow(self) -> None:
        starter = (ROOT / "skills/ci-actions/assets/ci.reusable.yml").read_text(
            encoding="utf-8"
        )
        concurrency = _indented_block(starter, "concurrency:")
        group_lines = [
            line.strip()
            for line in concurrency.splitlines()
            if line.lstrip().startswith("group:")
        ]

        self.assertEqual(
            group_lines,
            ["group: ${{ github.workflow }}-${{ github.ref }}"],
        )

    def test_ci_concurrency_reference_is_scoped_to_the_workflow(self) -> None:
        reference = (
            ROOT / "skills/ci-actions/references/execution-and-runners.md"
        ).read_text(encoding="utf-8")
        example = _fenced_block_after(
            reference,
            "## Concurrency and artifact promotion",
            "yaml",
        )
        concurrency = _indented_block(example.strip("\n"), "concurrency:")
        group_lines = [
            line.strip()
            for line in concurrency.splitlines()
            if line.lstrip().startswith("group:")
        ]

        self.assertEqual(
            group_lines,
            ["group: ${{ github.workflow }}-${{ github.ref }}"],
        )

    def test_cli_dry_run_returns_before_credentials_are_required(self) -> None:
        starter_path = ROOT / "skills/ops-tooling/assets/cli_skeleton.py"
        tree = ast.parse(starter_path.read_text(encoding="utf-8"), filename=str(starter_path))
        scale = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "scale"
        )
        top_level_conditions = [
            (index, ast.unparse(statement.test))
            for index, statement in enumerate(scale.body)
            if isinstance(statement, ast.If)
        ]
        dry_run_index, dry_run_statement = next(
            (index, statement)
            for index, statement in enumerate(scale.body)
            if isinstance(statement, ast.If) and ast.unparse(statement.test) == "dry_run"
        )
        credential_index = next(
            index for index, condition in top_level_conditions if "CF_TOKEN" in condition
        )

        self.assertLess(dry_run_index, credential_index)
        self.assertEqual(len(dry_run_statement.body), 2)
        emit_statement, exit_statement = dry_run_statement.body
        self.assertIsInstance(emit_statement, ast.Expr)
        self.assertIsInstance(emit_statement.value, ast.Call)
        self.assertEqual(ast.unparse(emit_statement.value.func), "_emit")
        keyword_values = {
            keyword.arg: ast.unparse(keyword.value)
            for keyword in emit_statement.value.keywords
        }
        self.assertEqual(keyword_values.get("dry_run"), "True")
        self.assertIsInstance(exit_statement, ast.Raise)
        self.assertEqual(ast.unparse(exit_statement.exc), "typer.Exit(Exit.OK)")
        branch_calls = [
            ast.unparse(node.func)
            for node in ast.walk(dry_run_statement)
            if isinstance(node, ast.Call)
        ]
        self.assertCountEqual(branch_calls, ["_emit", "typer.Exit"])


if __name__ == "__main__":
    unittest.main()
