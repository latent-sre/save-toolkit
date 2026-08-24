"""Mutation-oriented tests for the versioned evidence envelope."""

from __future__ import annotations

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

import evidence_envelope


ROOT = Path(__file__).resolve().parents[1]


class EvidenceEnvelopeTests(unittest.TestCase):
    def _valid(self) -> dict[str, object]:
        started = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
        return evidence_envelope.new_envelope(
            producer="fleet_doctor",
            role="fleet-health",
            target_root="F:/work/repo",
            target_revision="a" * 40,
            criterion="generated adapters match canonical source",
            status="pass",
            started_at=started,
            ended_at=started + timedelta(seconds=2),
            command_argv=["python", "scripts/validate_fleet.py"],
            command_cwd="F:/work/repo",
            exit_code=0,
            run_id="doctor-1",
            task_id="generated-adapters",
            attempt_id="attempt-1",
            isolation={"network": "not-used", "source_access": "read-only"},
        )

    def test_valid_envelope_has_a_valid_generated_id(self) -> None:
        envelope = self._valid()
        evidence_envelope.validate_envelope(envelope)
        self.assertRegex(envelope["evidence_id"], r"^ev_[0-9a-f]{32}$")

    def test_cli_rejects_duplicate_json_object_keys(self) -> None:
        envelope = self._valid()
        rendered = json.dumps(envelope)
        expected = '"status": "pass"'
        self.assertEqual(1, rendered.count(expected))
        rendered = rendered.replace(
            expected,
            '"status": "shadowed", ' + expected,
            1,
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "duplicate-key.json"
            path.write_text(rendered, encoding="utf-8")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = evidence_envelope.main(["validate", str(path)])

        self.assertEqual(1, result)
        self.assertRegex(stderr.getvalue(), "duplicate JSON object key.*status")
        self.assertNotIn("Valid evidence envelope", stdout.getvalue())

    def test_command_must_be_direct_argv_not_a_shell_string(self) -> None:
        envelope = self._valid()
        envelope["command"]["argv"] = "python scripts/validate_fleet.py"  # type: ignore[index]
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "command.argv"):
            evidence_envelope.validate_envelope(envelope)

    def test_obvious_credential_arguments_are_rejected(self) -> None:
        for argument in (
            "--api-token=abc",
            "--password",
            "https://user:pass@example.test/",
            "--endpoint=https://user:pass@example.test/",
        ):
            with self.subTest(argument=argument):
                envelope = self._valid()
                envelope["command"]["argv"].append(argument)  # type: ignore[index]
                with self.assertRaisesRegex(
                    evidence_envelope.EnvelopeValidationError,
                    "credential-bearing",
                ):
                    evidence_envelope.validate_envelope(envelope)

    def test_inverted_timestamps_are_rejected(self) -> None:
        envelope = self._valid()
        envelope["ended_at"] = "2026-07-31T11:59:59Z"
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "cannot precede"):
            evidence_envelope.validate_envelope(envelope)

    def test_space_separated_timestamp_is_rejected(self) -> None:
        envelope = self._valid()
        envelope["started_at"] = "2026-07-31 12:00:00Z"
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "started_at must be an RFC3339 UTC timestamp",
        ):
            evidence_envelope.validate_envelope(envelope)

    def test_secret_bearing_keys_are_rejected_recursively(self) -> None:
        envelope = self._valid()
        envelope["environment"]["service"] = {"api_token": "do-not-record"}  # type: ignore[index]
        with self.assertRaisesRegex(
            evidence_envelope.EnvelopeValidationError,
            "must not contain credentials",
        ):
            evidence_envelope.validate_envelope(envelope)

    def test_numeric_usage_tokens_are_allowed_only_in_typed_usage_source(self) -> None:
        envelope = self._valid()
        envelope["source"] = {
            "reservation": {"tokens": 1200},
            "actual_usage": {"tokens": 900},
        }
        evidence_envelope.validate_envelope(envelope)

        for path, value in (
            (("source", "reservation", "tokens"), "credential-like-value"),
            (("source", "tokens"), 900),
            (("environment", "tokens"), 900),
        ):
            invalid = self._valid()
            if path[0] == "source" and len(path) == 3:
                invalid["source"] = {path[1]: {path[2]: value}}
            elif path[0] == "source":
                invalid["source"] = {path[1]: value}
            else:
                invalid[path[0]][path[1]] = value  # type: ignore[index]
            with self.subTest(path=path), self.assertRaisesRegex(
                evidence_envelope.EnvelopeValidationError,
                "must not contain credentials",
            ):
                evidence_envelope.validate_envelope(invalid)

    def test_invalid_status_unknown_fields_and_missing_fields_are_rejected(self) -> None:
        invalid_status = self._valid()
        invalid_status["status"] = "probably"
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "unknown evidence status"):
            evidence_envelope.validate_envelope(invalid_status)

        unknown = self._valid()
        unknown["confidence"] = "high"
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "unknown evidence fields"):
            evidence_envelope.validate_envelope(unknown)

        missing = self._valid()
        del missing["limitations"]
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "missing evidence fields"):
            evidence_envelope.validate_envelope(missing)

    def test_context_identifiers_are_bounded(self) -> None:
        envelope = self._valid()
        invalid = copy.deepcopy(envelope)
        invalid["context"]["run_id"] = " contains spaces "  # type: ignore[index]
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "invalid identifier"):
            evidence_envelope.validate_envelope(invalid)

    def test_json_schema_contract_tracks_executable_validator(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/evidence-envelope-v1.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(1, schema["properties"]["schema_version"]["const"])
        self.assertEqual(evidence_envelope.TOP_LEVEL_FIELDS, set(schema["properties"]))
        self.assertEqual(evidence_envelope.TOP_LEVEL_FIELDS, set(schema["required"]))
        self.assertEqual(evidence_envelope.STATUSES, set(schema["properties"]["status"]["enum"]))
        self.assertEqual(
            evidence_envelope.RFC3339_UTC_TIMESTAMP_RE.pattern,
            schema["properties"]["started_at"]["pattern"],
        )
        self.assertEqual(
            evidence_envelope.RFC3339_UTC_TIMESTAMP_RE.pattern,
            schema["properties"]["ended_at"]["pattern"],
        )
        self.assertFalse(schema["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
