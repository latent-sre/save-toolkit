"""Structural checks on shipped skill assets: a context-requirements sidecar that must never
declare an authority-bearing path. Checks shape, never wording."""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
