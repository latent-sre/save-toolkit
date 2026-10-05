"""Calibrate the agent-engineer repair fixture without invoking a model."""

from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest

import build_probe


ROOT = Path(__file__).resolve().parent


class AgentEngineerCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = build_probe.load_scenario(
            ROOT / "build-scenarios/build-agent-engineer-resumes-after-partial-research.yaml"
        )
        cls.seed = spec["fixture"]["files"]["skills/weekly-report/SKILL.md"]
        cls.correct = cls.seed.replace("incidnets", "incidents")
        check = next(check for check in spec["checks"] if check["check"] == "command_exit_zero")
        command = shlex.split(check["command"])
        assert command[:2] == ["python", "-c"] and len(command) == 3
        cls.code = command[2]

    def check_repair(self, content):
        with tempfile.TemporaryDirectory(prefix="agent-engineer-case-") as directory:
            root = Path(directory)
            target = root / "skills/weekly-report/SKILL.md"
            target.parent.mkdir(parents=True)
            target.write_text(content, encoding="utf-8", newline="")
            return subprocess.run(
                [sys.executable, "-I", "-B", "-c", self.code],
                cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=15,
            )

    def test_repair_accepts_only_documented_whitespace_normalization(self):
        cases = {
            "exact": self.correct,
            "trailing whitespace": "\n".join(line + " \t" for line in self.correct.splitlines()) + "\n\n",
            "CRLF": self.correct.replace("\n", "\r\n"),
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                result = self.check_repair(content)
                self.assertEqual(0, result.returncode, result.stderr)

    def test_repair_rejects_leading_content_before_frontmatter(self):
        for prefix in ("\n", "\r\n", " "):
            with self.subTest(prefix=repr(prefix)):
                result = self.check_repair(prefix + self.correct)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("AssertionError", result.stderr)

    def test_repair_rejects_unfixed_typo_and_unrequested_edits(self):
        cases = {
            "unfixed typo": self.seed,
            "description changed": self.correct.replace("Draft the team's", "Write the team's"),
            "body changed": self.correct.replace("grouped by service", "grouped by owner"),
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                result = self.check_repair(content)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("AssertionError", result.stderr)


if __name__ == "__main__":
    unittest.main()
