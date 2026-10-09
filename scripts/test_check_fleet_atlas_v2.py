"""The real-tree contract must not mistake empty/uncited/error responses for success."""
import contextlib
import io
import json
import subprocess
import unittest
from unittest import mock

import check_fleet_atlas_v2
from check_fleet_atlas_v2 import CASES, check_response


class RealTreeContractTests(unittest.TestCase):
    def response(self, body):
        return json.dumps(body, ensure_ascii=False).encode("utf-8")

    def test_ci_contract_run_fails_on_empty_flagship_queries(self):
        for body in ({"outcome": "empty", "results": []},
                     {"outcome": "results", "results": []},
                     {"outcome": "unverified", "results": []}):
            with self.subTest(body=body), self.assertRaises(ValueError):
                check_response(self.response(body), "results")

    def test_cited_answer_and_verified_empty_have_distinct_contracts(self):
        fact = {"label": "verified", "class": "STATIC_EXTRACTED", "citations": [{"path": "README.md"}]}
        check_response(self.response({"outcome": "results", "results": [fact]}), "results")
        check_response(self.response({"outcome": "empty", "results": []}), "empty")
        for key in fact:
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_response(self.response({"outcome": "results", "results": [{k: v for k, v in fact.items() if k != key}]}), "results")

    def test_limit_is_encoded_bytes_not_character_count(self):
        response = self.response({"outcome": "verified", "message": "\u2603" * 8000})
        with self.assertRaisesRegex(ValueError, "byte budget"):
            check_response(response, "verified")


class VerifyOnceTests(unittest.TestCase):
    """Each CLI call re-verifies the whole tree, so the contract run verifies once."""

    FACT = {"label": "verified", "class": "STATIC_EXTRACTED", "citations": [{"path": "README.md"}]}

    def answer(self, expected):
        body = {"outcome": expected, "results": [self.FACT] if expected == "results" else []}
        return json.dumps(body).encode("utf-8")

    def run_main(self, *, build=None, in_process=None, cli_status=0):
        document = object()
        expected = {(verb, tuple(terms)): outcome for verb, terms, outcome in CASES}
        build = build or mock.Mock(return_value=document)
        verify = mock.Mock(return_value=document)
        query = mock.Mock(side_effect=in_process or (
            lambda verified, verb, terms: self.answer(expected[verb, tuple(terms)])))
        process = mock.Mock(side_effect=lambda command, **_: subprocess.CompletedProcess(
            command, cli_status, self.answer(expected[command[-2], (command[-1],)]), b""))
        errors = io.StringIO()
        with mock.patch("fleet_atlas_v2_artifacts.build", build), \
                mock.patch("fleet_atlas_v2_artifacts.verify", verify), \
                mock.patch("fleet_atlas_v2.query", query), \
                mock.patch.object(check_fleet_atlas_v2.subprocess, "run", process), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            code = check_fleet_atlas_v2.main(["--build"])
        return code, document, build, verify, query, process, errors.getvalue()

    def test_contract_run_verifies_once_and_keeps_one_command_line_query(self):
        code, document, build, verify, query, process, _ = self.run_main()
        self.assertEqual(0, code)
        self.assertEqual(1, build.call_count)
        verify.assert_not_called()
        self.assertEqual(1, process.call_count)
        self.assertIn("query", process.call_args.args[0])
        self.assertEqual(len(CASES) - 1, query.call_count)
        for call in query.call_args_list:
            self.assertIs(document, call.args[0])

    def test_refused_build_and_empty_flagship_answer_fail_the_run(self):
        refused = mock.Mock(side_effect=ValueError("dirty canonical inputs: ['CHANGELOG.md']"))
        code, *_, errors = self.run_main(build=refused)
        self.assertEqual(1, code)
        self.assertIn("dirty canonical inputs", errors)
        code, *_, errors = self.run_main(in_process=lambda verified, verb, terms: self.answer("empty"))
        self.assertEqual(1, code)
        self.assertIn("expected results, received empty", errors)

    def test_failed_command_line_query_fails_the_run_despite_a_valid_body(self):
        code, *_, errors = self.run_main(cli_status=1)
        self.assertEqual(1, code)
        self.assertIn("atlas command failed (1)", errors)


if __name__ == "__main__":
    unittest.main()
