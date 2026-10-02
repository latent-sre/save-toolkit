"""The real-tree contract must not mistake empty/uncited/error responses for success."""
import json
import subprocess
import unittest

from check_fleet_atlas_v2 import check_response


class RealTreeContractTests(unittest.TestCase):
    def response(self, body, code=0):
        return subprocess.CompletedProcess([], code, json.dumps(body, ensure_ascii=False).encode("utf-8"), b"")

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
        with self.assertRaises(ValueError):
            check_response(self.response({"outcome": "verified"}, 1), "verified")

    def test_limit_is_encoded_bytes_not_character_count(self):
        response = self.response({"outcome": "verified", "message": "\u2603" * 8000})
        with self.assertRaisesRegex(ValueError, "byte budget"):
            check_response(response, "verified")


if __name__ == "__main__":
    unittest.main()
