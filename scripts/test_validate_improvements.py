"""Mutation tests for scripts/validate_improvements.py.

Proves the stdlib schema validator actually rejects the failures it claims to — a validator whose
tests only exercise the happy path is the repo's own documented dead-rule mode.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_improvements as vi

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "evals/improvements/fi_agent_routing_discovery/record.json"


class ValidateImprovementsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.record = json.loads(RECORD.read_text(encoding="utf-8"))
        self.schema = json.loads(vi.SCHEMA.read_text(encoding="utf-8"))

    def _errors(self, record: dict) -> list[str]:
        return vi._errors(record, self.schema, self.schema, "record")

    def _check_schema(self, schema: dict) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / vi.SCHEMA.relative_to(ROOT)
            schema_path.parent.mkdir(parents=True)
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            return vi.check(root)

    def _check_record(self, record: dict, schema: dict | None = None) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / vi.SCHEMA.relative_to(ROOT)
            schema_path.parent.mkdir(parents=True)
            schema_path.write_text(
                json.dumps(self.schema if schema is None else schema),
                encoding="utf-8",
            )
            record_dir = root / "evals/improvements/fi_test"
            record_dir.mkdir(parents=True)
            (record_dir / "record.json").write_text(json.dumps(record), encoding="utf-8")
            return vi.check(root)

    def test_real_record_is_valid(self) -> None:
        # Anchor: the shipped record must pass, or every mutation below is meaningless.
        self.assertEqual([], self._errors(self.record))
        self.assertEqual([], vi.check(ROOT))

    def test_missing_required_field_is_rejected(self) -> None:
        bad = copy.deepcopy(self.record)
        del bad["status"]
        self.assertTrue(any("missing required 'status'" in e for e in self._errors(bad)))

    def test_unknown_top_level_field_is_rejected(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["surprise"] = 1
        self.assertTrue(any("unexpected propert" in e and "surprise" in e for e in self._errors(bad)))

    def test_bad_status_enum_is_rejected(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["status"] = "totally-made-up-status"
        self.assertTrue(any("not in" in e for e in self._errors(bad)))

    def test_schema_version_const_is_enforced(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["schema_version"] = 2
        self.assertTrue(any("must equal 1" in e for e in self._errors(bad)))

    def test_boolean_schema_version_is_rejected_end_to_end(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["schema_version"] = True

        failures = self._check_record(bad)

        self.assertTrue(
            any("schema_version" in error and "must equal 1" in error for error in failures),
            failures,
        )

    def test_budget_cap_over_maximum_is_rejected(self) -> None:
        # The lifecycle's three-attempts ceiling is a real safety bound; the schema pins it.
        bad = copy.deepcopy(self.record)
        bad["budget"]["max_attempts"] = 4
        errs = self._errors(bad)
        self.assertTrue(any("max_attempts" in e and "maximum" in e for e in errs), errs)

    def test_id_pattern_is_enforced(self) -> None:
        bad = copy.deepcopy(self.record)
        bad["improvement_id"] = "not-an-fi-id"
        self.assertTrue(any("improvement_id" in e and "does not match" in e for e in self._errors(bad)))

    def test_unique_items_duplicate_is_rejected(self) -> None:
        # success_criteria declares uniqueItems:true; a duplicated entry must fail. The schema uses
        # uniqueItems on six arrays and the validator now enforces it, so this can't pass silently.
        bad = copy.deepcopy(self.record)
        bad["success_criteria"] = [bad["success_criteria"][0], bad["success_criteria"][0]]
        self.assertTrue(any("uniqueItems" in e for e in self._errors(bad)), self._errors(bad))

    def test_unique_items_check_is_value_based_not_identity(self) -> None:
        # Direct exercise: unhashable dict items compared by value, not by object identity.
        schema = {"type": "array", "uniqueItems": True, "items": {"type": "object"}}
        dup = [{"a": 1}, {"a": 1}]
        self.assertTrue(any("uniqueItems" in e for e in vi._errors(dup, schema, schema, "arr")))
        self.assertEqual([], vi._errors([{"a": 1}, {"a": 2}], schema, schema, "arr"))

    def test_json_semantic_equality_distinguishes_booleans_from_numbers(self) -> None:
        self.assertFalse(vi._json_equal(True, 1))
        self.assertFalse(vi._json_equal(False, 0.0))
        self.assertTrue(vi._json_equal(1, 1.0))
        self.assertFalse(vi._json_equal({"nested": [True]}, {"nested": [1]}))
        self.assertTrue(vi._json_equal({"nested": [1]}, {"nested": [1.0]}))

    def test_const_enum_and_unique_items_use_json_semantic_equality(self) -> None:
        const_schema = {"const": 1}
        self.assertTrue(vi._errors(True, const_schema, const_schema, "value"))
        self.assertEqual([], vi._errors(1.0, const_schema, const_schema, "value"))

        enum_schema = {"enum": [1]}
        self.assertTrue(vi._errors(True, enum_schema, enum_schema, "value"))
        self.assertEqual([], vi._errors(1.0, enum_schema, enum_schema, "value"))
        self.assertEqual([], vi._schema_keyword_errors({"enum": [True, 1]}))
        duplicate_enum_errors = vi._schema_keyword_errors({"enum": [1, 1.0]})
        self.assertTrue(any("values must be unique" in error for error in duplicate_enum_errors))

        unique_schema = {"type": "array", "uniqueItems": True}
        self.assertEqual([], vi._errors([True, 1], unique_schema, unique_schema, "value"))
        self.assertTrue(vi._errors([1, 1.0], unique_schema, unique_schema, "value"))

    def test_unsupported_schema_keyword_fails_closed(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["properties"]["budget"]["exclusiveMaximum"] = 0
        errors = vi._schema_keyword_errors(schema)
        self.assertTrue(
            any("unsupported JSON Schema keyword 'exclusiveMaximum'" in error for error in errors),
            errors,
        )

    def test_format_is_a_recognized_annotation_not_an_assertion(self) -> None:
        schema = {"type": "string", "format": "date-time"}
        self.assertEqual([], vi._schema_keyword_errors(schema))
        self.assertEqual([], vi._errors("not-a-date", schema, schema, "timestamp"))

    def test_check_rejects_schema_with_unsupported_keyword(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / vi.SCHEMA.relative_to(ROOT)
            schema_path.parent.mkdir(parents=True)
            schema = copy.deepcopy(self.schema)
            schema["properties"]["budget"]["exclusiveMaximum"] = 0
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            failures = vi.check(root)
        self.assertTrue(any("exclusiveMaximum" in failure for failure in failures), failures)

    def test_unused_optional_external_ref_fails_closed(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["properties"]["unused_optional"] = {
            "$ref": "https://example.invalid/unused.schema.json"
        }

        failures = self._check_schema(schema)

        self.assertTrue(
            any("unused_optional" in failure and "only local $ref" in failure for failure in failures),
            failures,
        )

    def test_missing_local_ref_in_unused_definition_fails_closed(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["$defs"]["unused_optional"] = {
            "type": "object",
            "properties": {"value": {"$ref": "#/$defs/not-present"}},
        }

        failures = self._check_schema(schema)

        self.assertTrue(
            any("unused_optional" in failure and "unresolvable $ref" in failure for failure in failures),
            failures,
        )

    def test_cyclic_local_refs_are_audited_without_recursing_forever(self) -> None:
        schema = {
            "$defs": {
                "node": {
                    "type": "object",
                    "properties": {"next": {"$ref": "#/$defs/node"}},
                }
            },
            "$ref": "#/$defs/node",
        }

        self.assertEqual([], vi._schema_keyword_errors(schema))

    def test_unproductive_ref_cycle_fails_validation_without_recursion_error(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["$ref"] = "#"

        failures = self._check_record(self.record, schema)

        self.assertTrue(
            any("cyclic schema evaluation made no instance progress" in error for error in failures),
            failures,
        )

    def test_root_dialect_is_required_and_pinned(self) -> None:
        cases = (
            (None, "missing required root $schema"),
            ("http://json-schema.org/draft-07/schema#", "unsupported root $schema"),
        )
        for dialect, expected in cases:
            with self.subTest(dialect=dialect):
                schema = copy.deepcopy(self.schema)
                if dialect is None:
                    del schema["$schema"]
                else:
                    schema["$schema"] = dialect

                failures = self._check_schema(schema)

                self.assertTrue(any(expected in error for error in failures), failures)

    def test_root_id_is_required_and_pinned(self) -> None:
        cases = (
            (None, "missing required root $id"),
            ("https://example.invalid/different.schema.json", "unsupported root $id"),
        )
        for schema_id, expected in cases:
            with self.subTest(schema_id=schema_id):
                schema = copy.deepcopy(self.schema)
                if schema_id is None:
                    del schema["$id"]
                else:
                    schema["$id"] = schema_id

                failures = self._check_schema(schema)

                self.assertTrue(any(expected in error for error in failures), failures)

    def test_nested_dialect_switch_fails_closed(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["properties"]["budget"]["$schema"] = (
            "http://json-schema.org/draft-07/schema#"
        )

        failures = self._check_schema(schema)

        self.assertTrue(
            any("properties/budget/$schema" in error and "dialect switch" in error for error in failures),
            failures,
        )

    def test_nested_id_fails_closed(self) -> None:
        schema = copy.deepcopy(self.schema)
        schema["properties"]["budget"]["$id"] = "https://example.invalid/nested-resource"

        failures = self._check_schema(schema)

        self.assertTrue(
            any("properties/budget/$id" in error and "nested $id" in error for error in failures),
            failures,
        )

    def test_local_ref_target_must_be_a_schema_object(self) -> None:
        schema = {"title": "metadata", "$ref": "#/title"}

        errors = vi._schema_keyword_errors(schema)

        self.assertTrue(
            any("does not point at a schema object" in error for error in errors),
            errors,
        )

    def test_local_ref_can_resolve_through_an_array_pointer(self) -> None:
        schema = {"allOf": [{"type": "string"}], "$ref": "#/allOf/0"}

        self.assertEqual([], vi._schema_keyword_errors(schema))

    def test_supported_keywords_with_unsupported_shapes_fail_closed(self) -> None:
        cases = (
            ({"type": "not-a-json-type"}, "type"),
            ({"type": "object", "additionalProperties": "no"}, "additionalProperties"),
            ({"type": "array", "uniqueItems": "yes"}, "uniqueItems"),
            ({"type": "string", "pattern": "["}, "pattern"),
            ({"anyOf": []}, "anyOf"),
        )
        for schema, keyword in cases:
            with self.subTest(keyword=keyword):
                errors = vi._schema_keyword_errors(schema)
                self.assertTrue(any(keyword in error for error in errors), errors)

    def test_pattern_audit_rejects_unicode_divergence_and_python_only_syntax(self) -> None:
        cases = (
            ({"type": "string", "pattern": r"^\d+$"}, "shorthand character class"),
            ({"type": "string", "pattern": r"(?P<word>[a-z]+)"}, "Python-only"),
        )
        for schema, expected in cases:
            with self.subTest(pattern=schema["pattern"]):
                errors = vi._schema_keyword_errors(schema)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_allowed_pattern_is_compiled_and_evaluated_with_ascii_semantics(self) -> None:
        schema = {"type": "string", "pattern": "^[0-9]+$"}
        self.assertEqual([], vi._schema_keyword_errors(schema))
        self.assertEqual([], vi._errors("123", schema, schema, "value"))
        errors = vi._errors("\u0661\u0662\u0663", schema, schema, "value")
        self.assertTrue(any("does not match" in error for error in errors), errors)

    def test_wildcard_uses_ecma_262_line_terminator_semantics(self) -> None:
        schema = {"type": "string", "pattern": "^.$"}
        self.assertEqual([], vi._schema_keyword_errors(schema))
        self.assertEqual([], vi._errors("x", schema, schema, "value"))
        for terminator in ("\n", "\r", "\u2028", "\u2029"):
            with self.subTest(terminator=repr(terminator)):
                errors = vi._errors(terminator, schema, schema, "value")
                self.assertTrue(any("does not match" in error for error in errors), errors)

    def test_end_anchor_requires_true_end_of_input(self) -> None:
        schema = {"type": "string", "pattern": "^x$"}
        self.assertEqual([], vi._errors("x", schema, schema, "value"))
        errors = vi._errors("x\n", schema, schema, "value")
        self.assertTrue(any("does not match" in error for error in errors), errors)

    def test_additional_properties_schema_is_enforced(self) -> None:
        schema = {
            "type": "object",
            "properties": {"known": {"type": "string"}},
            "additionalProperties": {"type": "integer", "minimum": 0},
        }
        self.assertEqual([], vi._schema_keyword_errors(schema))
        self.assertEqual([], vi._errors({"known": "ok", "extra": 1}, schema, schema, "record"))
        errors = vi._errors({"known": "ok", "extra": -1}, schema, schema, "record")
        self.assertTrue(any("record.extra" in error and "minimum" in error for error in errors), errors)

    def test_non_standard_nan_record_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schema_path = root / vi.SCHEMA.relative_to(ROOT)
            schema_path.parent.mkdir(parents=True)
            schema_path.write_text(json.dumps(self.schema), encoding="utf-8")
            rec_dir = root / "evals/improvements/fi_nan"
            rec_dir.mkdir(parents=True)
            bad = copy.deepcopy(self.record)
            bad["budget"]["max_cost_usd"] = float("nan")
            (rec_dir / "record.json").write_text(json.dumps(bad), encoding="utf-8")
            failures = vi.check(root)
        self.assertTrue(any("non-standard JSON numeric constant" in error for error in failures), failures)

    def test_a_parseable_but_wrong_record_on_disk_fails_check(self) -> None:
        # End-to-end through check(): a temp record tree with a broken record must fail.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills/agent-authoring/assets").mkdir(parents=True)
            (root / vi.SCHEMA.relative_to(ROOT)).write_text(
                vi.SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
            )
            rec_dir = root / "evals/improvements/fi_broken"
            rec_dir.mkdir(parents=True)
            bad = copy.deepcopy(self.record)
            del bad["owner"]
            (rec_dir / "record.json").write_text(json.dumps(bad), encoding="utf-8")
            failures = vi.check(root)
        self.assertTrue(any("missing required 'owner'" in e for e in failures), failures)


if __name__ == "__main__":
    unittest.main()
