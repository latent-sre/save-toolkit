"""Structural checks on shipped skill assets: a context-requirements sidecar that must never
declare an authority-bearing path, and a CLI starter whose dry-run branch must return before any
credential is required. Both check shape or control flow, never wording."""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class SkillAssetTests(unittest.TestCase):
    def test_service_lifecycle_context_requirements_declare_no_authority_paths(self) -> None:
        sidecar_path = ROOT / "skills/service-lifecycle/context-requirements.yaml"
        document = yaml.safe_load(sidecar_path.read_text(encoding="utf-8"))
        spec = document["spec"]

        self.assertEqual(
            spec["forbidden"],
            ["/target/approval", "/target/credential"],
            "an effect-capable consumer must keep approval and credential paths forbidden",
        )
        declared = (
            spec["required"]
            + spec["optional"]
            + [p for alt in spec.get("alternatives", []) for p in alt["anyOf"]]
        )
        self.assertTrue(declared, "the sidecar declares no context paths at all")
        for pointer in declared:
            for banned in ("approval", "approve", "credential", "secret", "token", "auth"):
                with self.subTest(pointer=pointer, banned=banned):
                    self.assertNotIn(banned, pointer.lower())

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
