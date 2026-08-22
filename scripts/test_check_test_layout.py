#!/usr/bin/env python3
"""Focused tests for the test-entrypoint layout validator."""

import tempfile
import unittest
from pathlib import Path

import check_test_layout


class TestLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "scripts").mkdir()

    def _write(self, body: str) -> None:
        (self.root / "scripts" / "test_example.py").write_text(body, encoding="utf-8")

    def test_class_before_entrypoint_is_reachable(self) -> None:
        self._write(
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    pass\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        )
        self.assertEqual([], check_test_layout.validate(self.root))

    def test_class_after_entrypoint_is_rejected(self) -> None:
        self._write(
            "import unittest\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
            "class Hidden(unittest.TestCase):\n"
            "    pass\n"
        )
        failures = check_test_layout.validate(self.root)
        self.assertEqual(1, len(failures))
        self.assertIn("class Hidden is unreachable", failures[0])

    def test_missing_script_entrypoint_is_rejected(self) -> None:
        self._write(
            "import unittest\n"
            "class Silent(unittest.TestCase):\n"
            "    pass\n"
        )
        failures = check_test_layout.validate(self.root)
        self.assertEqual(1, len(failures))
        self.assertIn("missing executable test entrypoint", failures[0])

    def test_main_guard_without_a_test_runner_is_rejected(self) -> None:
        self._write(
            "import unittest\n"
            "class Silent(unittest.TestCase):\n"
            "    pass\n"
            "if __name__ == '__main__':\n"
            "    print('defined tests but ran none')\n"
        )
        failures = check_test_layout.validate(self.root)
        self.assertEqual(1, len(failures))
        self.assertIn("missing executable test entrypoint", failures[0])

    def test_runner_call_inside_an_uncalled_definition_is_rejected(self) -> None:
        self._write(
            "import unittest\n"
            "class Silent(unittest.TestCase):\n"
            "    pass\n"
            "if __name__ == '__main__':\n"
            "    def never_called():\n"
            "        unittest.main()\n"
        )
        failures = check_test_layout.validate(self.root)
        self.assertEqual(1, len(failures))
        self.assertIn("missing executable test entrypoint", failures[0])

    def test_entrypoint_text_inside_a_fixture_is_not_code(self) -> None:
        self._write(
            "FIXTURE = \"if __name__ == '__main__':\"\n"
            "class T:\n"
            "    pass\n"
        )
        failures = check_test_layout.validate(self.root)
        self.assertEqual(1, len(failures))
        self.assertIn("missing executable test entrypoint", failures[0])

    def test_empty_test_corpus_is_not_a_vacuous_pass(self) -> None:
        self.assertEqual(
            ["test corpus not found; test-layout validation would prove nothing"],
            check_test_layout.validate(self.root),
        )


if __name__ == "__main__":
    raise SystemExit(unittest.main())
