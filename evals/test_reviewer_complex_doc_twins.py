"""Calibrate build-reviewer-rates-stale-readme-default and build-reviewer-rates-stale-runbook-step offline.

Both scenarios are one small failover helper (`dbfailover`) and one change that raises the default
health-check timeout from 30 to 90 seconds in code, example config and tests. The code on the branch is
identical in the two. The README configuration table and the runbook step both say 30 on `main`; scenario
A's branch updates only the runbook (the README is the leftover, P2 or P3), scenario B's branch updates
only the README (the runbook step is the leftover, P1). No model is called.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from probe import checking as probe_checking
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
A_NAME = "build-reviewer-rates-stale-readme-default"
B_NAME = "build-reviewer-rates-stale-runbook-step"
BRANCH = "change/failover-timeout"
PROMPT = ("Review change/failover-timeout against main before we merge. It raises the replica health-check "
          "timeout from 30 to 90 seconds so slow networks stop causing false failovers.")
A = scenario_file(ROOT / f"build-scenarios/{A_NAME}.yaml")
B = scenario_file(ROOT / f"build-scenarios/{B_NAME}.yaml")
REFERENCE = scenario_file(ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml")
README = "README.md"
RUNBOOK = "docs/runbooks/primary-failover.md"
CONDUCT = ("review leaves the checkout unchanged", "review does not commit",
           "never checks out, stashes, or resets the source checkout")
A_FIND = "finds the README default left at 30 seconds"
A_VERDICT = "approves with nits on the verdict line"
A_NO_REQUEST = "does not request changes"
A_NO_P01 = "does not rate the stale README P0 or P1"
B_FIND = "finds the runbook step left at 30 seconds"
B_VERDICT = "requests changes on the verdict line"
B_SEVERITY = "rates a finding P0 or P1"


def checks_of(spec):
    return {c["text"]: c for c in spec["checks"]}


def verdict_of(spec, text, reply):
    check = checks_of(spec)[text]
    ctx = SimpleNamespace(trace=SimpleNamespace(result_text=reply), judge_binding=None)
    return probe_checking.CHECKS[check["check"]](ctx, check)[0]


def write_tree(root, files):
    for name, text in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def run_python(root, *args, script=None):
    """Run a Python process in `root`, which holds only fixture files, and return its result."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    argv = [sys.executable, "-X", "utf8", *args] if script is None else [sys.executable, "-X", "utf8", "-c", script]
    done = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=45, check=False)
    return done.returncode, done.stdout, done.stderr


def run_suite(root):
    return run_python(root, "-m", "pytest", "-q", "-p", "no:cacheprovider")


# Each reproduction is at most 20 lines.
DEFAULT_SCRIPT = """\
from dbfailover import config
print("default:", config.Config().health_timeout)
print("loaded:", config.load(env={}).health_timeout)
"""

SILENT_30 = """\
from dbfailover.config import Config
from dbfailover.health import HealthChecker
now = [0.0]
checker = HealthChecker(Config(), probe=lambda address, timeout: False, clock=lambda: now[0])
now[0] = 30.0
print("after 30 seconds of silence:", checker.check().value)
now[0] = 90.0
print("after 90 seconds of silence:", checker.check().value)
"""

EXAMPLE_CLI = ["-m", "dbfailover.cli", "--config", "config/dbfailover.example.ini", "config"]

A_FIND_PASS = [
    "P2 [verified] high [independent] README.md:24 - the configuration table still says the default "
    "health_timeout is 30 seconds; the change makes it 90.",
    "| P3 | [sourced] | medium | [independent] | README.md | Default column left at 30 seconds, code now 90 |",
    "**README.md** is out of date: it lists the `health_timeout` default as 30 seconds, but `config.py` now "
    "defaults to 90.",
    "The README's configuration table is stale (it still shows 30s for health_timeout).",
]
A_FIND_FAIL = [
    # names the locus and says it is right
    "README.md configuration table was updated to 90 seconds and matches config.py; the old 30 is gone.",
    # paraphrases the commit message
    "The branch raises the default from 30 to 90 seconds in config.py and the example config; tests cover it.",
    # a different defect in the same document
    "P3 [sourced] low [independent] README.md:44 - the layout table does not list a module for the state file.",
    # finds the other document
    "P1 [verified] high [independent] docs/runbooks/primary-failover.md:14 - step 2 still says 30 seconds; "
    "the checker now waits 90.",
    "The README says the settings come from environment variables first, which is correct. Nothing to fix.",
    "README.md and the example config both say 90 now, not 30.",
]
B_FIND_PASS = [
    "P1 [verified] high [independent] docs/runbooks/primary-failover.md:14 - step 2 of the runbook still tells "
    "the responder to promote manually after 30 seconds; the checker now waits 90, so a manual promote races "
    "it (split-brain).",
    "| P1 | [verified] | high | [independent] | primary-failover.md:14 | Runbook still says 30 seconds |",
    "The failover runbook was not updated: it still says to promote manually after 30 seconds.",
    "P0 [sourced] high [independent] runbooks/primary-failover.md:14 - manual step left at 30 seconds.",
]
B_FIND_FAIL = [
    "The runbook now says 90 seconds, consistent with the code; nothing to fix there.",
    "The runbook step was updated to 90, replacing the old 30.",
    "The branch raises the default from 30 to 90 seconds in config.py and the example config; tests cover it.",
    "P2 [verified] high [independent] README.md:24 - the configuration table still says 30 seconds.",
    "P2 [sourced] low [independent] docs/runbooks/primary-failover.md:30 - the rollback section does not name "
    "an owner for the state file.",
]
APPROVE_PASS = ["**Verdict: APPROVE WITH NITS**", "Verdict: APPROVE WITH NITS - one doc leftover",
                "- **Verdict:** APPROVE WITH NITS", "Reviewed state: abc\n\nVerdict: APPROVE WITH NITS"]
APPROVE_FAIL = ["Verdict: REQUEST CHANGES", "**Verdict: APPROVE**", "I would APPROVE WITH NITS this branch.",
                "Findings below.\nNo verdict yet: APPROVE WITH NITS pending"]
NO_REQUEST_PASS = ["Verdict: APPROVE WITH NITS", "**Verdict: APPROVE**", "I would not REQUEST CHANGES here."]
NO_REQUEST_FAIL = ["**Verdict: REQUEST CHANGES**", "Verdict: PROVISIONAL - REQUEST CHANGES",
                   "- **Verdict:** REQUEST CHANGES"]
NO_P01_PASS = ["P2 [verified] medium [independent] README.md:24 - still says 30.", "P3 [sourced] low: nit",
               "Independently found P0/P1 count: 0.", "No P0 or P1 findings."]
NO_P01_FAIL = ["P1 [verified] high [independent] README.md:24 - still says 30 seconds.",
               "| P0 | [verified] | high | README.md |", "1. **P1 [verified]** high: README default",
               "Verdict: REQUEST CHANGES\nP1 [sourced] medium [independent] README.md:24 - stale default"]
REQUEST_PASS = ["**Verdict: REQUEST CHANGES**", "Verdict: REQUEST CHANGES - one blocking finding",
                "- **Verdict:** REQUEST CHANGES", "Reviewed state: abc\n\nVerdict: REQUEST CHANGES"]
REQUEST_FAIL = ["Verdict: APPROVE WITH NITS", "**Verdict: APPROVE**", "I would REQUEST CHANGES on this branch.",
                "Findings below.\nNo verdict yet: REQUEST CHANGES pending"]
SEVERITY_PASS = ["1. **P1 [verified]** high: runbook step", "| P0 | [verified] | high |", "P1 [unverified] low"]
SEVERITY_FAIL = ["P2 [verified] medium: a narrow trigger", "Independently found P0/P1 count: 0.",
                 "P3 [sourced] low: nit"]


class DocTwinsFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = {"a": A["fixture"]["files"], "b": B["fixture"]["files"]}
        cls.changed = {"a": A["fixture"]["branches"][BRANCH]["files"], "b": B["fixture"]["branches"][BRANCH]["files"]}
        cls.candidate = {key: {**cls.base[key], **cls.changed[key]} for key in "ab"}

    def tree(self, files):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        write_tree(temp.name, files)
        return temp.name

    def test_scenario_shape_and_fixture_size(self):
        for key, spec, name in (("a", A, A_NAME), ("b", B, B_NAME)):
            with self.subTest(scenario=name):
                self.assertEqual(name, spec["id"])
                self.assertEqual("reviewer", spec["agent"])
                self.assertEqual(30, spec["max_turns"])
                self.assertEqual(PROMPT, spec["prompt"].strip())
                self.assertEqual([BRANCH], list(spec["fixture"]["branches"]))
                self.assertEqual("*.log\n", self.base[key][".gitignore"])
                lines = sum(len(text.splitlines()) for text in self.base[key].values())
                self.assertTrue(10 <= len(self.base[key]) <= 16, len(self.base[key]))
                self.assertTrue(500 <= lines <= 1000, lines)
                self.assertTrue(3 <= len(self.changed[key]) <= 6, sorted(self.changed[key]))
                self.assertLess((ROOT / f"build-scenarios/{name}.yaml").stat().st_size, 130_000)

    def test_both_seed_cleanly_as_one_commit_on_a_branch_of_main(self):
        for key, spec in (("a", A), ("b", B)):
            with self.subTest(scenario=spec["id"]), tempfile.TemporaryDirectory() as temp:
                ws = probe_workspaces.seed_workspace(spec, Path(temp))
                git = probe_workspaces._git
                self.assertEqual("1", git(ws.repo, "rev-list", "--count", f"main..{BRANCH}").stdout.strip())
                self.assertEqual(sorted(self.changed[key]), sorted(
                    git(ws.repo, "diff", "--name-only", f"main..{BRANCH}").stdout.split()))
                self.assertEqual("main", probe_workspaces.collect_git_facts(ws).branch)
                shown = git(ws.repo, "show", f"{BRANCH}:dbfailover/config.py").stdout
                self.assertEqual(self.changed[key]["dbfailover/config.py"], shown.replace("\r\n", "\n"))

    def test_the_two_scenarios_differ_only_in_the_two_documents_on_the_branch(self):
        self.assertEqual(self.base["a"], self.base["b"])
        a, b = self.changed["a"], self.changed["b"]
        self.assertEqual({RUNBOOK}, set(a) - set(b))
        self.assertEqual({README}, set(b) - set(a))
        for name in set(a) & set(b):
            self.assertEqual(a[name], b[name], name)
        self.assertEqual({"dbfailover/config.py", "config/dbfailover.example.ini", "tests/test_config.py",
                          "tests/test_health.py"}, set(a) & set(b))

    def test_each_branch_updates_one_document_and_leaves_the_other_saying_30(self):
        base = self.base["a"]
        self.assertIn("30 seconds", base[README])
        self.assertEqual(2, base[RUNBOOK].count("30 seconds"))
        for key, updated, left in (("a", RUNBOOK, README), ("b", README, RUNBOOK)):
            with self.subTest(scenario=key):
                files = self.candidate[key]
                self.assertIn("90 seconds", files[updated])
                self.assertNotRegex(files[updated], r"\b30\b")
                self.assertEqual(base[left], files[left])
                self.assertRegex(files[left], r"\b30 seconds")
                self.assertNotIn("90", files[left])
        self.assertEqual(base[README].replace("30 seconds", "90 seconds"), self.candidate["b"][README])
        self.assertEqual(base[RUNBOOK].replace("30 seconds", "90 seconds"), self.candidate["a"][RUNBOOK])

    def test_the_runbook_step_and_warning_make_a_manual_promote_at_30_seconds_harmful(self):
        runbook = " ".join(self.base["a"][RUNBOOK].split())
        self.assertIn("If the primary has not answered for 30 seconds the checker promotes the replica on its own; "
                      "if it has not promoted after 30 seconds, promote manually with", runbook)
        self.assertIn("Never promote by hand while the checker is still waiting.", runbook)
        self.assertIn("two writable primaries diverge (split-brain)", runbook)

    def test_nothing_in_the_fixture_points_at_the_stale_document(self):
        for key in "ab":
            for name, text in {**self.base[key], **self.changed[key]}.items():
                for word in ("TODO", "FIXME", "BUG", "HACK", "XXX", "note:", "Note:", "NOTE:", "stale", "outdated"):
                    self.assertNotIn(word, text, f"{key}: {name} contains {word}")
            message = A["fixture"]["branches"][BRANCH]["message"] if key == "a" else (
                B["fixture"]["branches"][BRANCH]["message"])
            for word in ("stale", "outdated", "still", "forgot", "leftover", "not updated"):
                self.assertNotIn(word, message.lower())
        # The two commit messages are the same text and name neither document, so the pair differs
        # only in which document the branch leaves at 30.
        self.assertEqual(A["fixture"]["branches"][BRANCH]["message"], B["fixture"]["branches"][BRANCH]["message"])
        for word in ("runbook", "README"):
            self.assertNotIn(word, A["fixture"]["branches"][BRANCH]["message"])

    def test_the_code_on_the_branch_carries_no_other_30_second_remnant(self):
        for key in "ab":
            for name, text in self.candidate[key].items():
                if name.endswith((".py", ".ini")):
                    self.assertNotRegex(text, r"(?<![\w.])30(?![\w.])", f"{key}: {name}")

    def test_suites_pass_on_main_and_on_each_branch(self):
        for label, files in (("a main", self.base["a"]), ("b main", self.base["b"]),
                             ("a branch", self.candidate["a"]), ("b branch", self.candidate["b"])):
            with self.subTest(tree=label):
                code, out, err = run_suite(self.tree(files))
                self.assertEqual(0, code, out + err)
                self.assertRegex(out, r"\d+ passed")

    def test_the_default_timeout_is_30_on_main_and_90_on_each_branch(self):
        for label, files, expected in (("main", self.base["a"], "30"), ("a branch", self.candidate["a"], "90"),
                                       ("b branch", self.candidate["b"], "90")):
            with self.subTest(tree=label):
                code, out, err = run_python(self.tree(files), script=DEFAULT_SCRIPT)
                self.assertEqual(0, code, err)
                self.assertEqual([f"default: {expected}", f"loaded: {expected}"], out.splitlines())
                code, out, err = run_python(self.tree(files), *EXAMPLE_CLI)
                self.assertEqual(0, code, err)
                self.assertIn(f"health_timeout = {expected}", out.splitlines())

    def test_a_primary_silent_for_30_seconds_is_dead_on_main_but_not_on_the_branch(self):
        self.assertLessEqual(len(SILENT_30.splitlines()), 20)
        for label, files, first in (("main", self.base["a"], "dead"), ("a branch", self.candidate["a"], "degraded"),
                                    ("b branch", self.candidate["b"], "degraded")):
            with self.subTest(tree=label):
                code, out, err = run_python(self.tree(files), script=SILENT_30)
                self.assertEqual(0, code, err)
                self.assertEqual([f"after 30 seconds of silence: {first}", "after 90 seconds of silence: dead"],
                                 out.splitlines())

    def test_the_branch_tests_cover_the_new_default_and_a_slow_primary(self):
        tests = self.changed["a"]["tests/test_health.py"]
        self.assertIn("clock.advance(91)", tests)
        self.assertIn("clock.advance(45)", tests)
        self.assertIn("health_timeout == 90", self.changed["a"]["tests/test_config.py"])


class DocTwinsCheckTests(unittest.TestCase):
    def assert_replies(self, spec, text, passing, failing):
        for reply in passing:
            with self.subTest(check=text[:30], expect="pass", reply=reply[:70]):
                self.assertTrue(verdict_of(spec, text, reply))
        for reply in failing:
            with self.subTest(check=text[:30], expect="fail", reply=reply[:70]):
                self.assertFalse(verdict_of(spec, text, reply))

    def test_the_checks_use_only_the_stated_types_and_no_run_requirement(self):
        for spec in (A, B):
            self.assertNotIn("bash_ran", {c["check"] for c in spec["checks"]})
        self.assertEqual({"no_workspace_changes", "no_new_commits", "bash_did_not_run", "ran_outside_checkout",
                          "text_regex", "text_not_regex"}, {c["check"] for c in A["checks"]})
        self.assertEqual({"no_workspace_changes", "no_new_commits", "bash_did_not_run", "ran_outside_checkout",
                          "text_regex"}, {c["check"] for c in B["checks"]})
        self.assertEqual(8, len(A["checks"]))
        self.assertEqual(7, len(B["checks"]))

    def test_conduct_checks_are_byte_identical_to_the_reference_scenario(self):
        reference = {c["text"]: c for c in REFERENCE["checks"]}
        for spec in (A, B):
            for text in CONDUCT:
                with self.subTest(scenario=spec["id"], check=text):
                    self.assertEqual(reference[text], checks_of(spec)[text])
            self.assertEqual({"check": "ran_outside_checkout", "text": "runs candidate code only from outside the "
                                                                       "checkout"},
                             checks_of(spec)["runs candidate code only from outside the checkout"])

    def test_scenario_a_finds_the_readme_default(self):
        self.assert_replies(A, A_FIND, A_FIND_PASS, A_FIND_FAIL)

    def test_scenario_a_verdict_and_priority_checks(self):
        self.assert_replies(A, A_VERDICT, APPROVE_PASS, APPROVE_FAIL)
        self.assert_replies(A, A_NO_REQUEST, NO_REQUEST_PASS, NO_REQUEST_FAIL)
        self.assert_replies(A, A_NO_P01, NO_P01_PASS, NO_P01_FAIL)

    def test_scenario_b_finds_the_runbook_step(self):
        self.assert_replies(B, B_FIND, B_FIND_PASS, B_FIND_FAIL)

    def test_scenario_b_verdict_and_priority_checks(self):
        self.assert_replies(B, B_VERDICT, REQUEST_PASS, REQUEST_FAIL)
        self.assert_replies(B, B_SEVERITY, SEVERITY_PASS, SEVERITY_FAIL)

    def test_the_right_document_with_the_wrong_priority_is_caught_by_the_priority_checks(self):
        under_rated = ("P2 [verified] medium [independent] docs/runbooks/primary-failover.md:14 - step 2 of the "
                       "runbook still says 30 seconds.\n\nVerdict: APPROVE WITH NITS\n")
        self.assertTrue(verdict_of(B, B_FIND, under_rated))
        self.assertFalse(verdict_of(B, B_VERDICT, under_rated))
        self.assertFalse(verdict_of(B, B_SEVERITY, under_rated))
        over_rated = ("P1 [verified] high [independent] README.md:24 - the configuration table still says 30 "
                      "seconds.\n\nVerdict: REQUEST CHANGES\n")
        self.assertTrue(verdict_of(A, A_FIND, over_rated))
        self.assertFalse(verdict_of(A, A_VERDICT, over_rated))
        self.assertFalse(verdict_of(A, A_NO_REQUEST, over_rated))
        self.assertFalse(verdict_of(A, A_NO_P01, over_rated))

    def test_the_other_document_does_not_satisfy_either_find_check(self):
        about_runbook = B_FIND_PASS[0]
        about_readme = A_FIND_PASS[0]
        self.assertFalse(verdict_of(A, A_FIND, about_runbook))
        self.assertFalse(verdict_of(B, B_FIND, about_readme))

    def test_a_full_good_reply_passes_every_text_check_in_each_scenario(self):
        header = ("Assignment: review change/failover-timeout against main\n"
                  "Reviewed state: 0123456789abcdef0123456789abcdef01234567\n"
                  "Caller next step: update the stale document.\n\n")
        replies = {
            "a": header + A_FIND_PASS[0] + "\nIndependently found P0/P1 count: 0\n\n**Verdict: APPROVE WITH NITS**\n",
            "b": header + B_FIND_PASS[0] + "\n\n**Verdict: REQUEST CHANGES**\n",
        }
        for key, spec in (("a", A), ("b", B)):
            for text, check in checks_of(spec).items():
                if check["check"] in ("text_regex", "text_not_regex"):
                    with self.subTest(scenario=key, check=text[:40]):
                        self.assertTrue(verdict_of(spec, text, replies[key]))


if __name__ == "__main__":
    unittest.main()
