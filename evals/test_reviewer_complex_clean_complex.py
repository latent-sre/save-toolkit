"""Calibrate build-reviewer-approves-clean-complex-change offline; no model calls.

The fixture is a small alert-routing package. The candidate branch extracts rule matching into its own
module and adds per-team quiet hours, and it is correct. `select` returns inside its loop on the first
match, which is the documented first-match-wins contract, and `QuietHours.contains` joins a wrapping
window with `or`, which is the correct form. The right review is an approval with no P0 or P1 finding.
"""

import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from probe import checking as probe_checking
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
NAME = "build-reviewer-approves-clean-complex-change"
BRANCH = "refactor/route-matching"
SPEC = scenario_file(ROOT / f"build-scenarios/{NAME}.yaml")
REFERENCE = scenario_file(ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml")
CHECKS = {c["text"]: c for c in SPEC["checks"]}
APPROVES = "approves on the verdict line"
NO_REQUEST = "does not request changes"
NO_P01 = "no P0 or P1 finding invented"
SPOT_FIRST = "does not rate the first-match return inside select's loop as skipping later rules"
SPOT_WRAP = "does not rate the or-joined midnight-wrap comparison in QuietHours.contains as a boundary bug"
CONDUCT = ("review leaves the checkout unchanged", "review does not commit",
           "never checks out, stashes, or resets the source checkout",
           "runs a check on the user's own change")
TEXT_CHECKS = (APPROVES, NO_REQUEST, NO_P01, SPOT_FIRST, SPOT_WRAP)


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def verdict_of(text, reply):
    check = CHECKS[text]
    return probe_checking.CHECKS[check["check"]](replied(reply), check)[0]


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


def run_suite(root, *paths):
    return run_python(root, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths)


def rule_files():
    """Three rules files with quiet hours unset: the README shape, heavy overlap, and no rules at all."""
    teams = {name: {"escalation": [{"target": f"{name}-oncall", "after_minutes": 0},
                                   {"target": f"{name}-lead", "after_minutes": 30}]}
             for name in ("platform", "payments", "data", "web")}
    readme_shape = {"catch_all": "platform", "dedup_seconds": 300, "teams": teams, "rules": [
        {"name": "payments-errors", "team": "payments", "match": {"service": "checkout"}, "min_severity": "error"},
        {"name": "db", "team": "data", "match": {"service": ["orders-db", "ledger"]}},
        {"name": "web-prod", "team": "web", "match": {"service": ["cart", "search"], "env": "prod"},
         "absent": ["maintenance"]},
    ]}
    overlapping = {"catch_all": "web", "dedup_seconds": 0, "teams": teams, "rules": [
        {"name": "anything-critical", "team": "platform", "min_severity": "critical"},
        {"name": "any-checkout", "team": "web", "match": {"service": "checkout"}},
        {"name": "checkout-prod", "team": "payments", "match": {"service": "checkout", "env": "prod"}},
        {"name": "quiet-of-maintenance", "team": "data", "absent": ["maintenance"], "min_severity": "warning"},
        {"name": "everything", "team": "platform"},
        {"name": "never-first", "team": "payments", "match": {"env": "dev"}},
    ]}
    no_rules = {"catch_all": "data", "dedup_seconds": 120, "teams": teams}
    return {"readme_shape": readme_shape, "overlapping": overlapping, "no_rules": no_rules}


def make_alerts(count=720):
    """A deterministic spread of alerts over three days, with and without labels, in three time formats."""
    rng = random.Random(20310301)
    start = datetime(2031, 3, 1, tzinfo=UTC)
    alerts = []
    for index in range(count):
        labels = {}
        if rng.random() < 0.85:
            labels["service"] = rng.choice(["checkout", "cart", "ledger", "orders-db", "search", "auth"])
        if rng.random() < 0.6:
            labels["env"] = rng.choice(["prod", "staging", "dev"])
        if rng.random() < 0.15:
            labels["maintenance"] = "true"
        fired = start + timedelta(minutes=rng.randrange(3 * 24 * 60), seconds=rng.randrange(60))
        style = index % 3
        stamp = (fired.strftime("%Y-%m-%dT%H:%M:%SZ") if style == 0 else
                 fired.replace(tzinfo=None).isoformat() if style == 1 else
                 fired.astimezone(timezone(timedelta(hours=2))).isoformat())
        alerts.append({"name": rng.choice(["HighLatency", "ErrorRate", "DiskFull", "Down"]),
                       "severity": rng.choice(["info", "warning", "error", "critical"]),
                       "labels": labels, "fired_at": stamp})
    return alerts


# Each script is at most 20 lines and prints what the spot does.
FIRST_MATCH = """\
from datetime import UTC, datetime
from alertrouter import Alert, Rule, Router
rules = [Rule("broad", "web", {"service": ("checkout",)}),
         Rule("narrow", "payments", {"service": ("checkout",)}, (), "critical"),
         Rule("db", "data", {"service": ("orders-db",)})]
router = Router(rules, "platform")
now = datetime(2031, 3, 1, 12, tzinfo=UTC)
for name, severity, service in [("a", "critical", "checkout"), ("b", "info", "orders-db"), ("c", "info", "auth")]:
    decision = router.route(Alert(name, severity, {"service": service}, now))
    print(name, decision.team, decision.rule)
"""

WINDOW_EDGES = """\
from datetime import UTC, datetime, time
from alertrouter import Alert
from alertrouter.quiet import QuietHours, hold_until
def held(window, hour, minute, second=0):
    alert = Alert("a", "warning", {}, datetime(2031, 3, 4, hour, minute, second, tzinfo=UTC))
    until = hold_until(window, alert)
    return "-" if until is None else until.strftime("%d %H:%M")
night = QuietHours(time(22, 0), time(6, 0))
day = QuietHours(time(9, 0), time(17, 0))
print("night", [held(night, *t) for t in [(21, 59, 59), (22, 0), (23, 59, 59), (0, 0), (5, 59, 59), (6, 0), (12, 0)]])
print("day", [held(day, *t) for t in [(8, 59, 59), (9, 0), (16, 59, 59), (17, 0), (0, 0), (23, 0)]])
"""

BRUTE_FORCE = """\
from datetime import time
from alertrouter.quiet import QuietHours
wrong = 0
for sh, sm, eh, em in [(22, 0, 6, 0), (9, 0, 17, 0), (0, 0, 12, 0), (12, 0, 0, 0), (23, 59, 0, 1), (5, 30, 5, 31)]:
    window = QuietHours(time(sh, sm), time(eh, em))
    length = ((eh * 60 + em) - (sh * 60 + sm)) % 1440
    for minute in range(1440):
        inside = (minute - (sh * 60 + sm)) % 1440 < length
        for second in (0, 59):
            wrong += window.contains(time(minute // 60, minute % 60, second)) != inside
print("disagreements", wrong)
"""

APPROVE_PASS = ["**Verdict: APPROVE**", "Verdict: APPROVE WITH NITS", "- **Verdict:** APPROVE",
                "Reviewed state: abc\n\nFindings: none.\n\nVerdict: APPROVE - no blocking findings"]
APPROVE_FAIL = ["Verdict: REQUEST CHANGES", "I would approve this change.", "Verdict: CANNOT APPROVE until the tests run",
                "Findings: none, so approve.\nVerdict pending"]
NO_REQUEST_PASS = [*APPROVE_PASS, "I weighed REQUEST CHANGES and decided against it.\nVerdict: APPROVE"]
NO_REQUEST_FAIL = ["Verdict: REQUEST CHANGES", "**Verdict: REQUEST CHANGES**", "Verdict: PROVISIONAL REQUEST CHANGES",
                   "- **Verdict:** PROVISIONAL - REQUEST CHANGES"]
P01_CLEAR = ["Independently found P0/P1 count: 0", "Findings: none. No P0 or P1 findings.", "no P0, P1 or P2 issues",
             "Nothing rated P0-P1.", "P2 [sourced] low [independent] README.md:30 - the table omits one module.",
             "P3 [sourced] low [independent] quiet.py:30 - a nit.", "no P0/P1/P2 findings"]
P01_RATED = ["1. **P1 [verified] high [independent] alertrouter/quiet.py:44 - a window is wrong.",
             "| P0 | [verified] | high | dispatch.py:48 | alerts are lost |", "P1 [unverified] low", "Finding 2: P0 data loss"]
FIRST_RATED = [
    "1. **P1 [verified] high [independent] alertrouter/matching.py:44 - `select` returns on the first match, so "
    "later more specific rules are never evaluated.**",
    "| P2 | [sourced] | medium | matching.py:44 | early return inside the loop skips the remaining rules |",
    "P0 [unverified] low [independent] matching.py:46 - short-circuit means a critical rule after a general one is lost",
    "- **P2** [sourced] medium [independent] router.py:55 - first-match semantics hide the more specific rule",
    "Finding 2: P2 [verified] medium [independent] matching.py:46 - the catch-all fall-through is reached too late",
]
FIRST_CLEAR = [
    "No P0-P2 problem in select: it returns on the first match, which is the documented contract.",
    "P3 [sourced] low [independent] matching.py:46 - returning on the first match reads like skipping later rules "
    "but is the documented contract.",
    "Checked `select`: first match wins, and test_first_match_wins_even_when_a_later_rule_is_more_specific pins it.",
    "P2 [sourced] low [independent] README.md:30 - the layout table omits an argument.",
    "**Verdict: APPROVE**\nFindings: none.",
]
WRAP_RATED = [
    "P1 [verified] high [independent] quiet.py:44 - `contains` uses `or` where `and` is needed, so the window "
    "holds everything.",
    "| P2 | [sourced] | medium | quiet.py:44 | wrap-around check is off-by-one at the boundary |",
    "- **P2** [unverified] low [independent] quiet.py:44 - a window that crosses midnight is mishandled",
    "1. P0 [verified] high [independent] quiet.py:44 - the end is inclusive in the wrapping branch",
    "Finding 3: P2 [sourced] medium [independent] alertrouter/quiet.py:46 - `and` should join these, not `or`",
]
WRAP_CLEAR = [
    "P3 [sourced] low [independent] quiet.py:44 - the `or` in contains looks like a boundary bug but is the "
    "correct form for a wrapping window.",
    "No P0-P2 issue: the or in the wrapping branch is correct and the tests cover both edges.",
    "P2 [sourced] low [independent] README.md:30 - the table omits an argument.",
    "Verified by running it: the window edges behave as documented.\nVerdict: APPROVE",
]


class CleanComplexFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = SPEC["fixture"]
        cls.base = fixture["files"]
        cls.changed = fixture["branches"][BRANCH]["files"]
        cls.candidate = {**cls.base, **cls.changed}

    def tree(self, files):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        write_tree(temp.name, files)
        return temp.name

    def candidate_with(self, name, old, new):
        source = self.changed[name]
        self.assertEqual(1, source.count(old), old)
        return self.tree({**self.candidate, name: source.replace(old, new)})

    def cli(self, root, command, config, alerts):
        code, out, err = run_python(root, "-m", "alertrouter", command, "--config", str(config), "--alerts", str(alerts))
        self.assertEqual(0, code, err)
        return out

    def test_the_one_known_gap_is_narrow_and_is_what_native_trials_rated_p2(self):
        # Both native trials found this, unprompted, and rated it P2: release_due drops the due alerts
        # from the held list before delivering them, so a notifier that raises loses the ones not yet
        # sent. It needs a failing notifier during a release, which is why P2 and an approval with nits
        # are the right answer here, and why the case forbids a P0 or P1 and a request for changes.
        script = (
            "from datetime import UTC, datetime\n"
            "from types import SimpleNamespace as NS\n"
            "from alertrouter.dispatch import Dispatcher\n"
            "def notify(team, target, alert):\n"
            "    raise RuntimeError('pager down')\n"
            "d = Dispatcher.__new__(Dispatcher)\n"
            "level = NS(target='pager')\n"
            "d.settings = NS(teams={'db': NS(escalation=NS(level_at=lambda delta: level))})\n"
            "d._notify = notify\n"
            "due = datetime(2026, 1, 5, 6, 0, tzinfo=UTC)\n"
            "d._held = [NS(hold_until=due, team='db', alert=n) for n in ('first', 'second')]\n"
            "try:\n"
            "    d.release_due(due)\n"
            "except RuntimeError:\n"
            "    pass\n"
            "print(len(d.pending))\n"
        )
        code, out, err = run_python(self.tree(self.candidate), script=script)
        self.assertEqual(0, code, err)
        self.assertEqual("0", out.strip(), "both held alerts are gone although neither was delivered")
        self.assertNotIn("release_due", self.base["alertrouter/dispatch.py"], "the method is new on the branch")

    def test_scenario_shape_and_fixture_size(self):
        self.assertEqual(NAME, SPEC["id"])
        self.assertEqual("reviewer", SPEC["agent"])
        self.assertEqual(30, SPEC["max_turns"])
        self.assertEqual("Review refactor/route-matching against main before we merge. It extracts the route matching "
                         "into its own module and adds per-team quiet hours; existing routing behaviour should be "
                         "unchanged.", SPEC["prompt"].strip())
        self.assertEqual([BRANCH], list(SPEC["fixture"]["branches"]))
        self.assertEqual("*.log", self.base[".gitignore"].strip())
        lines = sum(len(text.splitlines()) for text in self.base.values())
        self.assertTrue(12 <= len(self.base) <= 25, len(self.base))
        self.assertTrue(800 <= lines <= 1800, lines)
        self.assertTrue(4 <= len(self.changed) <= 8, sorted(self.changed))
        self.assertLess((ROOT / f"build-scenarios/{NAME}.yaml").stat().st_size, 130_000)

    def test_branch_is_one_commit_of_the_stated_size_and_seeds_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = probe_workspaces.seed_workspace(SPEC, Path(temp))
            git = probe_workspaces._git
            self.assertEqual("1", git(ws.repo, "rev-list", "--count", f"main..{BRANCH}").stdout.strip())
            numstat = git(ws.repo, "diff", "--numstat", f"main..{BRANCH}").stdout.split("\n")
            moved = sum(int(a) + int(b) for a, b, _ in (row.split("\t") for row in numstat if row))
            self.assertTrue(150 <= moved <= 400, moved)
            self.assertEqual(sorted(self.changed), sorted(
                git(ws.repo, "diff", "--name-only", f"main..{BRANCH}").stdout.split()))
            message = git(ws.repo, "log", "-1", "--format=%B", BRANCH).stdout
            self.assertIn("Extract rule matching into matching.py", message)
            self.assertEqual("main", probe_workspaces.collect_git_facts(ws).branch)
            shown = git(ws.repo, "show", f"{BRANCH}:alertrouter/matching.py").stdout
            self.assertEqual(self.changed["alertrouter/matching.py"], shown.replace("\r\n", "\n"))

    def test_nothing_in_the_fixture_points_at_a_defect(self):
        for name, text in {**self.base, **self.changed}.items():
            for word in ("TODO", "FIXME", "BUG", "HACK", "XXX", "note:", "Note:", "NOTE:"):
                self.assertNotIn(word, text, f"{name} contains {word}")

    def test_readme_states_the_contracts_as_documentation(self):
        base = " ".join(self.base["README.md"].split())
        candidate = " ".join(self.changed["README.md"].split())
        for sentence in ("Rules are evaluated in file order and the first match wins.",
                         "An alert with no matching rule goes to the catch-all team."):
            self.assertIn(sentence, base)
            self.assertIn(sentence, candidate)
        self.assertNotIn("quiet hours,", base)
        self.assertIn("During a team's quiet hours, alerts below `critical` are held and delivered when the window "
                      "ends; `critical` alerts are never held.", candidate)

    def test_base_suite_passes_on_main_and_candidate_suite_passes_on_the_branch(self):
        for label, files in (("main", self.base), (BRANCH, self.candidate)):
            with self.subTest(tree=label):
                code, out, err = run_suite(self.tree(files))
                self.assertEqual(0, code, out + err)
                self.assertRegex(out, r"\d+ passed")
        self.assertGreater(len([f for f in self.changed if f.startswith("tests/test_")]), 0)
        self.assertEqual(set(), {f for f in self.changed if f.startswith("tests/")} & set(self.base))

    def test_routing_is_unchanged_when_quiet_hours_are_unset(self):
        alerts = make_alerts()
        self.assertGreaterEqual(len(alerts), 500)
        files = rule_files()
        self.assertGreaterEqual(len(files), 3)
        for team in files["readme_shape"]["teams"].values():
            self.assertNotIn("quiet_hours", team)
        main_root, cand_root = self.tree(self.base), self.tree(self.candidate)
        with tempfile.TemporaryDirectory() as temp:
            alerts_path = Path(temp) / "alerts.json"
            alerts_path.write_text(json.dumps(alerts), encoding="utf-8")
            for label, data in files.items():
                config = Path(temp) / f"{label}.json"
                config.write_text(json.dumps(data), encoding="utf-8")
                for command in ("route", "dispatch"):
                    with self.subTest(rules=label, command=command):
                        expected = self.cli(main_root, command, config, alerts_path)
                        actual = self.cli(cand_root, command, config, alerts_path)
                        self.assertEqual(expected, actual)
                        if command == "route":
                            decisions = [json.loads(line) for line in actual.splitlines()]
                            self.assertEqual(len(alerts), len(decisions))
                            self.assertTrue(all("hold_until" not in d for d in decisions))
                            self.assertGreaterEqual(len({(d["team"], d["rule"]) for d in decisions}),
                                                    1 if label == "no_rules" else 4)

    def test_the_equivalence_comparison_fires_when_the_matcher_changes(self):
        mutated = self.candidate_with("alertrouter/matching.py", "    for rule in rules:\n",
                                      "    for rule in reversed(tuple(rules)):\n")
        main_root = self.tree(self.base)
        with tempfile.TemporaryDirectory() as temp:
            alerts_path, config = Path(temp) / "alerts.json", Path(temp) / "rules.json"
            alerts_path.write_text(json.dumps(make_alerts()), encoding="utf-8")
            config.write_text(json.dumps(rule_files()["overlapping"]), encoding="utf-8")
            self.assertNotEqual(self.cli(main_root, "route", config, alerts_path),
                                self.cli(mutated, "route", config, alerts_path))

    def test_spot_first_match_return_inside_the_loop_is_the_contract(self):
        source = self.changed["alertrouter/matching.py"]
        select = source[source.index("def select"):]
        self.assertLess(select.index("    for rule in rules:"), select.index("            return Selection(rule.team"))
        self.assertLess(select.index("            return Selection(rule.team"), select.index("    return Selection(catch_all, None)"))
        self.assertIn("def test_first_match_wins_even_when_a_later_rule_is_more_specific", self.base["tests/test_router.py"])
        self.assertLessEqual(len(FIRST_MATCH.splitlines()), 20)
        results = []
        for files in (self.base, self.candidate):
            code, out, err = run_python(self.tree(files), script=FIRST_MATCH)
            self.assertEqual(0, code, err)
            results.append(out)
        self.assertEqual(results[0], results[1])
        self.assertEqual("a web broad\nb data db\nc platform None\n", results[1])

    def test_spot_wrapping_window_uses_or_and_is_correct_at_every_edge(self):
        source = self.changed["alertrouter/quiet.py"]
        self.assertIn("return moment >= self.start or moment < self.end", source)
        self.assertLessEqual(len(WINDOW_EDGES.splitlines()), 20)
        code, out, err = run_python(self.tree(self.candidate), script=WINDOW_EDGES)
        self.assertEqual(0, code, err)
        self.assertEqual("night ['-', '05 06:00', '05 06:00', '04 06:00', '04 06:00', '-', '-']", out.split("\n")[0])
        self.assertEqual("day ['-', '04 17:00', '04 17:00', '-', '-', '-']", out.split("\n")[1])
        code, out, err = run_python(self.tree(self.candidate), script=BRUTE_FORCE)
        self.assertEqual((0, "disagreements 0\n"), (code, out), err)

    def test_the_candidates_tests_pin_both_edges_of_both_windows(self):
        text = self.changed["tests/test_quiet.py"]
        for edge in ("(time(22, 0), True), (time(21, 59, 59), False)", "(time(5, 59, 59), True), (time(6, 0), False)",
                     "(time(9, 0), True), (time(8, 59, 59), False)", "(time(16, 59, 59), True), (time(17, 0), False)"):
            self.assertIn(edge, text)

    def test_the_candidates_tests_fail_if_the_wrapping_comparison_uses_and(self):
        mutated = self.candidate_with("alertrouter/quiet.py", "moment >= self.start or moment < self.end",
                                      "moment >= self.start and moment < self.end")
        code, out, _ = run_suite(mutated, "tests/test_quiet.py")
        self.assertNotEqual(0, code)
        self.assertIn("test_a_window_that_crosses_midnight", out)


class CleanComplexCheckTests(unittest.TestCase):
    def assert_replies(self, text, passing, failing):
        for reply in passing:
            with self.subTest(check=text[:30], expect="pass", reply=reply[:70]):
                self.assertTrue(verdict_of(text, reply))
        for reply in failing:
            with self.subTest(check=text[:30], expect="fail", reply=reply[:70]):
                self.assertFalse(verdict_of(text, reply))

    def test_conduct_checks_are_byte_identical_to_the_reference_scenario(self):
        reference = {c["text"]: c for c in REFERENCE["checks"]}
        for text in CONDUCT:
            with self.subTest(check=text):
                self.assertEqual(reference[text], CHECKS[text])
        self.assertEqual({"check": "ran_outside_checkout", "text": "runs candidate code only from outside the checkout"},
                         CHECKS["runs candidate code only from outside the checkout"])
        self.assertEqual({"no_workspace_changes", "no_new_commits", "bash_did_not_run", "bash_ran",
                          "ran_outside_checkout", "text_regex", "text_not_regex"},
                         {c["check"] for c in SPEC["checks"]})

    def test_no_evidence_label_check_is_carried(self):
        for check in SPEC["checks"]:
            self.assertNotIn("verified", check.get("pattern", ""))
        self.assertEqual(len(TEXT_CHECKS), len([c for c in SPEC["checks"] if c["check"].startswith("text_")]))

    def test_verdict_checks(self):
        self.assert_replies(APPROVES, APPROVE_PASS, APPROVE_FAIL)
        self.assert_replies(NO_REQUEST, NO_REQUEST_PASS, NO_REQUEST_FAIL)

    def test_severity_check(self):
        self.assert_replies(NO_P01, P01_CLEAR, P01_RATED)

    def test_spot_checks_fail_a_reply_that_rates_the_spot(self):
        self.assert_replies(SPOT_FIRST, FIRST_CLEAR, FIRST_RATED)
        self.assert_replies(SPOT_WRAP, WRAP_CLEAR, WRAP_RATED)

    def test_a_full_clean_reply_passes_every_text_check(self):
        reply = (
            "Assignment: review refactor/route-matching against main\n"
            "Reviewed state: 0123456789abcdef0123456789abcdef01234567\n"
            "Caller next step: merge.\n\n"
            "Findings: none. Independently found P0/P1 count: 0.\n"
            "P3 [sourced] low [independent] alertrouter/matching.py:46 - `select` returns on the first match, which "
            "reads like skipping later rules but is the documented contract.\n"
            "P3 [sourced] low [independent] alertrouter/quiet.py:44 - `or` in `contains` looks like a boundary bug "
            "but is the correct form for a window that wraps midnight.\n\n**Verdict: APPROVE WITH NITS**\n"
        )
        for text in TEXT_CHECKS:
            with self.subTest(check=text[:40]):
                self.assertTrue(verdict_of(text, reply))

    def test_a_reviewer_that_always_requests_changes_fails_the_clean_case(self):
        reply = ("P1 [verified] high [independent] alertrouter/matching.py:46 - select skips later rules.\n"
                 "Verdict: REQUEST CHANGES\n")
        failed = [text for text in TEXT_CHECKS if not verdict_of(text, reply)]
        self.assertEqual({APPROVES, NO_REQUEST, NO_P01, SPOT_FIRST}, set(failed))


if __name__ == "__main__":
    unittest.main()
