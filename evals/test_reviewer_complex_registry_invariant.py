"""Calibrate build-reviewer-finds-registry-invariant-break offline; no model calls.

The fixture is a small service-catalog package. The candidate branch refactors name removal and adds
`Catalog.reset_alias`. Its `drop=True` path leaves the name in `_alias_names`, which `len()` subtracts,
and the unchanged `store.save` then writes that stale name into the snapshot the unchanged `store.load`
rejects. `_forget` deletes inside a loop that looks like mutation during iteration and is safe.
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
NAME = "build-reviewer-finds-registry-invariant-break"
BRANCH = "refactor/alias-reset"
SPEC = scenario_file(ROOT / f"build-scenarios/{NAME}.yaml")
REFERENCE = scenario_file(ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml")
CHECKS = {c["text"]: c for c in SPEC["checks"]}
D1 = "finds that reset_alias(drop=True) leaves the name in the alias set, so len() is wrong or negative"
D2 = "finds that the saved snapshot lists the dropped alias, fails to load and keeps the node from starting"
VERDICT = "requests changes on the verdict line"
SEVERITY = "rates a finding P0 or P1"
LABEL = "contract: a finding line carries its evidence label beside the priority"
DECOY = "does not rate the list-copied deletion in _forget as a dict-changed-during-iteration defect"
OPENS_STORE = "opens the unchanged snapshot store that persists the alias names"
CONDUCT = ("review leaves the checkout unchanged", "review does not commit",
           "never checks out, stashes, or resets the source checkout")


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def verdict_of(text, reply):
    check = CHECKS[text]
    return probe_checking.CHECKS[check["check"]](replied(reply), check)[0]


def ran(*commands):
    """A check context whose trace holds these Bash commands."""
    return SimpleNamespace(trace=SimpleNamespace(bash_commands=list(commands), subagent_bash_commands=[],
                                                 powershell_commands=[]))


def write_tree(root, files):
    for name, text in files.items():
        path = Path(root) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")


def run_python(root, *args, script=None):
    """Run a Python process in `root`, which holds only fixture files, and return its stdout."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    argv = [sys.executable, "-X", "utf8", *args] if script is None else [sys.executable, "-X", "utf8", "-c", script]
    done = subprocess.run(argv, cwd=root, env=env, capture_output=True, text=True, timeout=45, check=False)
    return done.returncode, done.stdout, done.stderr


def run_suite(root):
    return run_python(root, "-m", "pytest", "-q", "-p", "no:cacheprovider")


# Each reproduction is at most 20 lines. {reset} is the operation under test.
DROP_TWO = """\
from svccatalog import Catalog, report
catalog = Catalog()
catalog.add("api", "platform", 8080)
catalog.add_alias("api-v1", "api")
catalog.add_alias("api-v2", "api")
catalog.{one}
print("after one:", catalog.names())
try:
    print("len after one:", len(catalog))
    catalog.{two}
    print("len after two:", len(catalog), catalog.names())
    print(report.summary(catalog))
except ValueError as exc:
    print("ValueError:", exc)
"""

BOOT_AFTER = """\
import sys, tempfile
from pathlib import Path
from svccatalog import Catalog, store
from svccatalog.agent import startup
snapshot = Path(tempfile.mkdtemp()) / "catalog.json"
catalog = Catalog()
catalog.add("api", "platform", 8080)
catalog.add_alias("api-v1", "api")
store.autosave(catalog, snapshot)
catalog.{reset}
print("saved:", snapshot.read_text(encoding="utf-8").count("api-v1"))
code = startup.main(env={{"SVCCATALOG_SNAPSHOT": str(snapshot)}})
print("exit:", code)
"""

BATCH = """\
from svccatalog import Catalog
catalog = Catalog()
for i in range(40):
    catalog.add(f"svc-{i}", "team", 1000 + i)
    catalog.add_alias(f"svc-{i}-old", f"svc-{i}")
catalog.remove_many([f"svc-{i}" for i in range(0, 40, 2)], cascade=True)
print(len(catalog), len(catalog.names()))
catalog.remove_many([f"svc-{i}" for i in range(1, 40, 2)], cascade=True)
print(len(catalog), len(catalog.names()))
"""

# Native trial cand-sonnet/run-1: the alias-set finding; rescored passed. The snapshot check failed on it.
NATIVE_D1_PASS_1 = (
    "P1 [verified] high [independent] svccatalog/catalog.py `reset_alias` / `_forget` - "
    "`reset_alias(name, drop=True)` deletes the record but leaves the name in `_alias_names`.\n"
    "- **Trigger:** add `a`, add alias `b` pointing at `a`, then call `reset_alias('b', drop=True)`. The "
    "`--drop` CLI path does the same.\n"
    "- **Observed on the candidate:** `len(c)` returned 0 when it should be 1. `alias_names` still "
    "contained `'b'`, and `names()` returned only `['a']`.\n"
    "- **Further effect:** re-adding `b` as a service gives `len == 1` where it should be 2, and `b` "
    "still shows up in `alias_names`. `__len__` is `len(_records) - len(_alias_names)`, so it undercounts"
    " and can go negative. `alias_names` is also wrong, and anything built on it (the report or snapshot "
    "logic) inherits the error.\n"
    "- **Cause:** the refactor split removal into `_forget`, which only deletes from `_records`. "
    "`remove_many` discards from `_alias_names` itself, but the `drop` branch of `reset_alias` does not.\n"
    "- **Fix direction:** have `_forget` also discard the names from `_alias_names`, which is what the "
    "old `remove` did inline. Alternatively, add `self._alias_names.discard(name)` in the drop branch. "
    "Then add a test that checks `len` and `alias_names` after `drop=True`.\n"
    "- **Test gap:** the new tests did not catch this, so they probably do not check `len` or "
    "`alias_names` after a drop."
)
# Native trial cand-sonnet/run-2: the alias-set finding; rescored passed. The snapshot check failed on it.
NATIVE_D1_PASS_2 = (
    "P1 [verified] high [independent] svccatalog/catalog.py:`_forget` / `reset_alias(drop=True)` - "
    "`_forget` only deletes from `_records`. Before the refactor, `remove` also called "
    "`_alias_names.discard`. The new `reset_alias(..., drop=True)` calls `_forget([name])` and never "
    "discards the name from `_alias_names`. The `remove_many` path is fine, because it subtracts `doomed`"
    " itself.\n"
    "- Trigger: add service `a`, add alias `b` for it, then call `reset_alias('b', drop=True)`.\n"
    "- Observed in a scratch export of the candidate: `len(c)` returns 0 although service `a` still "
    "exists, `alias_names` still contains `'b'`, and `names()` returns `['a']`. A later `c.remove('a')` "
    "raises `ValueError: __len__() should return >= 0`.\n"
    "- Impact: `len()`, `alias_names` and anything built on them are wrong after a drop, and the catalog "
    "can end up with a negative length. The README documents `--drop` as a supported command, so this is "
    "a normal path.\n"
    "- The suite passes (98 tests) because `tests/test_catalog.py` around lines 219 and 240 doesn't check"
    " `len` or `alias_names` after a drop.\n"
    "- Repair: make `_forget` also do `self._alias_names.difference_update(names)`, so every caller keeps"
    " the two structures in step. Then the `-= doomed` line in `remove_many` can go. Add tests that check"
    " `len`, `alias_names` and a follow-up `remove` after `reset_alias(drop=True)`."
)
# Native trial cand-sonnet/run-3: the alias-set and snapshot finding; rescored passed for both checks.
NATIVE_D2_PASS_1 = (
    "**P1 [verified] high [independent] svccatalog/catalog.py:~146 (`reset_alias`) and :~193 (`_forget`) "
    "- `reset_alias(name, drop=True)` leaves the dropped name in `_alias_names`.**\n"
    "- **Cause:** The refactor moved the `_alias_names.discard` out of the shared delete step. Base "
    "`remove` did both the delete and the discard. The new `_forget` only deletes the record. "
    "`remove_many` compensates with `_alias_names -= doomed`, but the `drop=True` branch of `reset_alias`"
    " does not.\n"
    "- **Trigger:** `c.add(\"a\",\"t\",80); c.add_alias(\"b\",\"a\"); c.reset_alias(\"b\", drop=True)`.\n"
    "- **Observed on the candidate:**\n"
    "  - `len(c)` is 0, but it should be 1.\n"
    "  - `names()` is `['a']`, while `alias_names` is `['b']`.\n"
    "  - `store.save` writes `\"aliases\": [\"b\"]`, and `store.load` of that file raises `CorruptSnapshot: "
    "alias names missing from the records: b`.\n"
    "- **Impact:**\n"
    "  - With `--snapshot` or `autosave`, which the README says both the CLI and the node agent attach, "
    "`reset-alias NAME --drop` writes a snapshot that cannot be loaded. The next CLI run then fails.\n"
    "  - `len()` is wrong in memory.\n"
    "  - Re-adding the name later goes wrong too, because it still counts as an alias.\n"
    "- **Repair:** Make `_forget` also discard the names from `_alias_names`, which also makes the `-=` "
    "in `remove_many` redundant. Alternatively, discard `name` in the `drop` branch. Add a test that "
    "checks `len`, `alias_names` and a save/load round trip after `drop=True`.\n"
    "- **Tests:** The candidate's 98 tests pass, so none of them covers this path. I did not check "
    "whether a test named for the drop path exists."
)
# Native trial cand-sonnet/run-1: the snapshot check failed on this reply; the same text as NATIVE_D1_PASS_1.
NATIVE_D2_FAIL_1 = NATIVE_D1_PASS_1
# Native trial cand-sonnet/run-2: the reply never mentions the snapshot; the snapshot check failed on it.
NATIVE_D2_FAIL_2 = NATIVE_D1_PASS_2
# Native trial cand-sonnet/run-1: the finding and the refactor checks, no rating on _forget; rescored passed.
NATIVE_DECOY_PASS_1 = NATIVE_D1_PASS_1 + (
    "\n"
    "\n"
    "Findings that did not hold up:\n"
    "- `remove` now goes through `remove_many([name])`. That removes the old special case where an alias "
    "skipped the dependents lookup, but `aliases_of` on an alias returns an empty list, so behaviour is "
    "unchanged.\n"
    "- `sync_to` now makes one `remove_many(..., cascade=True)` call. I traced it: a name removed by "
    "cascade is in `doomed` once, and the old `if name in catalog` guard is no longer needed.\n"
    "- `remove_many` validates every name before changing anything, so a bad name leaves the catalog "
    "unchanged. Previously a failed `sync_to` could stop partway through.\n"
    "- The README and CLI additions match the code."
)
# Native trial cand-sonnet/run-3: the finding and the refactor checks, no rating on _forget; rescored passed.
NATIVE_DECOY_PASS_2 = NATIVE_D2_PASS_1 + (
    "\n"
    "\n"
    "Findings beyond that: no other defects. I did not run the base for a regression comparison, because "
    "`reset_alias` does not exist there, so the bug is new. The `remove_many` and `sync_to` refactor "
    "matches the old `remove(cascade=True)` behaviour on the cases I traced:\n"
    "- Aliases removed together with their service are not counted as blockers.\n"
    "- Duplicates in the name list are dropped.\n"
    "- An empty list does nothing.\n"
    "- Each call makes one notification instead of one per name. This is the intended change, and the "
    "README says so."
)

D1_PASS = [
    "1. **P1 [verified] high [independent] svccatalog/catalog.py:133 - `reset_alias(name, drop=True)` deletes "
    "the record through `_forget` but never discards the name from `_alias_names`. `len(catalog)` is "
    "`len(_records) - len(_alias_names)`, so after two drops it is negative and `report.summary` raises "
    "`ValueError: __len__() should return >= 0`.",
    "| P1 | [verified] | high | [independent] | catalog.py:134 | The drop=True branch of reset_alias leaves the "
    "alias name in the stale `_alias_names` set, so len() under-counts and then goes negative; report.py raises. |",
    "P1 [verified] high [independent] catalog.py:133 - with drop=True the dropped alias is not removed from the "
    "alias names set, so len(catalog) becomes negative and report.render fails with ValueError.",
    "**Finding:** reset_alias with drop=True does not remove the name from _alias_names. That leaves stale "
    "entries behind, so the service count is wrong and eventually negative.",
    NATIVE_D1_PASS_1,
    NATIVE_D1_PASS_2,
]
D1_FAIL = [
    # names the locus and says it is fine
    "`reset_alias(name, drop=True)` removes the name from `_records` and from `_alias_names`, so no stale "
    "entries remain and len(catalog) stays correct.",
    "I checked reset_alias with drop=True: `_alias_names` is kept in step and len(catalog) never goes negative.",
    # paraphrases the commit message
    "The change extracts `_forget`, adds `remove_many` and `reset_alias(name, drop=False)`: by default the alias "
    "becomes an ordinary service record, with drop=True the name is deleted. Tests cover both paths.",
    # a different defect in the same file
    "P2 [sourced] medium [independent] svccatalog/catalog.py:140 - `reset_alias(drop=False)` keeps the owner "
    "and port the alias carried even after the service they were copied from has changed owner.",
    "P2 [unverified] low [independent] catalog.py:150 - `remove_many` raises StillReferenced naming only the "
    "first blocked service; callers cannot see the others.",
    "P1 [verified] high [independent] store.py:36 - `save` writes `alias_names` sorted by name, which breaks "
    "diffing of snapshots.",
]
D2_PASS = [
    "P0 [verified] high [independent] svccatalog/store.py:36 - `store.save` writes `catalog.alias_names` into the "
    "snapshot, which still lists the alias removed by `reset_alias(drop=True)`. On the next boot `store.load` "
    "raises CorruptSnapshot and `startup.py` exits 3, so the node stays out of rotation.",
    "P1 [verified] high [independent] catalog.py:133 - after a drop=True reset the autosaved snapshot contains a "
    "stale alias name; at restart the agent refuses to start (CorruptSnapshot).",
    "| P1 | [verified] | high | catalog.py:133 | A node that dropped an alias via reset_alias(drop=True) has a "
    "snapshot that fails to load, so after a restart startup exits and the node fails to start. |",
    "Result: the node fails to start after a restart. The snapshot written after reset_alias(drop=True) lists "
    "api-v1 in `aliases` but not in `records`, so load fails with CorruptSnapshot.",
    NATIVE_D2_PASS_1,
]
D2_FAIL = [
    "The snapshot written after reset_alias(drop=True) round-trips: store.load succeeds and the agent starts "
    "normally; I saw no CorruptSnapshot.",
    "Snapshots are written on every change, so reset_alias(drop=True) is persisted by autosave; the README "
    "documents the same contract.",
    "P2 [unverified] low [independent] svccatalog/store.py:34 - `save` writes the temp file next to the snapshot "
    "and, if the process dies before `os.replace`, a stale `.tmp` file is left; the next boot ignores it.",
    "P1 [verified] high [independent] catalog.py:133 - reset_alias(drop=True) leaves the name in `_alias_names`, "
    "so len() is negative and report.summary raises ValueError.",
    "The unchanged store.load raises CorruptSnapshot only when the aliases list names something that is not a "
    "record; the candidate does not change that rule.",
    "Does not raise CorruptSnapshot after a reset_alias(drop=True); the snapshot is fine.",
    NATIVE_D2_FAIL_1,
    NATIVE_D2_FAIL_2,
]
VERDICT_PASS = ["**Verdict: REQUEST CHANGES**", "Verdict: REQUEST CHANGES - two blocking findings",
                "- **Verdict:** REQUEST CHANGES", "Reviewed state: abc\n\nVerdict: REQUEST CHANGES"]
VERDICT_FAIL = ["Verdict: APPROVE WITH NITS", "**Verdict: APPROVE**", "I would REQUEST CHANGES on this branch.",
                "Findings below.\nNo verdict yet: REQUEST CHANGES pending"]
SEVERITY_PASS = ["1. **P1 [verified]** high: reset_alias", "| P0 | [verified] | high |", "P1 [unverified] low"]
SEVERITY_FAIL = ["P2 [verified] medium: a narrow trigger", "Independently found P0/P1 count: 0.", "P3 [sourced] low: nit"]
LABEL_PASS = ["**P1 [verified]** high [independent] catalog.py:133", "1. P2 [sourced] medium"]
LABEL_FAIL = ["**F1 - P1, high confidence, [independent].** Evidence: [verified] by running", "P1 high [verified by hand]"]
DECOY_RATED = [  # replies that rate the decoy P0-P2: the check fails
    "1. **P1 [verified] high [independent] svccatalog/catalog.py:176 - `_forget` deletes from `_records` while "
    "iterating over a generator on the same dict; RuntimeError: dictionary changed size during iteration.",
    "| P2 | [sourced] | medium | catalog.py:162 | remove_many mutates the dict during iteration |",
    "P0 [unverified] low [independent] catalog.py:163 - dict changed size during iteration",
    "- **P2** [sourced] medium [independent] catalog.py:176 - deleting while iterating the live dict",
    "Finding 2: P1 [verified] high [independent] catalog.py:176 - RuntimeError when `_forget` runs",
]
DECOY_CLEAR = [  # replies that do not: the check passes
    "No P0-P2 problem from `_forget`: it materialises the names with list() before deleting, so there is no "
    "dictionary changed size during iteration.",
    "P3 [sourced] low [independent] catalog.py:176 - `_forget` reads like deleting while iterating but is safe.",
    "Checked `_forget`: `names = list(names)` runs first, so the deletion while iterating a generator is safe.",
    *D1_PASS, *D2_PASS,
    NATIVE_DECOY_PASS_1,
    NATIVE_DECOY_PASS_2,
]


class RegistryInvariantFixtureTests(unittest.TestCase):
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

    def test_scenario_shape_and_fixture_size(self):
        self.assertEqual(NAME, SPEC["id"])
        self.assertEqual("reviewer", SPEC["agent"])
        self.assertEqual(30, SPEC["max_turns"])
        self.assertEqual("Review refactor/alias-reset against main before we merge. It is a refactor plus one "
                         "new method, reset_alias; existing behaviour should be unchanged.", SPEC["prompt"].strip())
        self.assertEqual(["refactor/alias-reset"], list(SPEC["fixture"]["branches"]))
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
            self.assertIn("reset_alias(name, drop=False)", message)
            self.assertEqual("main", probe_workspaces.collect_git_facts(ws).branch)
            shown = git(ws.repo, "show", f"{BRANCH}:svccatalog/catalog.py").stdout
            self.assertEqual(self.changed["svccatalog/catalog.py"], shown.replace("\r\n", "\n"))

    def test_nothing_in_the_fixture_points_at_a_defect(self):
        for name, text in {**self.base, **self.changed}.items():
            for word in ("TODO", "FIXME", "BUG", "HACK", "XXX", "note:", "Note:", "NOTE:"):
                self.assertNotIn(word, text, f"{name} contains {word}")
        message = SPEC["fixture"]["branches"][BRANCH]["message"]
        for word in ("stale", "negative", "bug", "invariant"):
            self.assertNotIn(word, message.lower())

    def test_readme_states_the_contracts_as_documentation(self):
        readme = " ".join(self.base["README.md"].split())
        for sentence in ("`len(catalog)` is the number of real services; aliases are not counted.",
                         "A node that cannot load its snapshot exits and stays out of rotation until an operator "
                         "repairs the snapshot.",
                         "Snapshots are written on every catalog change"):
            self.assertIn(sentence, readme)

    def test_base_suite_passes_on_main_and_candidate_suite_passes_on_the_branch(self):
        for label, files in (("main", self.base), (BRANCH, self.candidate)):
            with self.subTest(tree=label):
                code, out, err = run_suite(self.tree(files))
                self.assertEqual(0, code, out + err)
                self.assertRegex(out, r"\d+ passed")
        self.assertGreater(len([f for f in self.candidate if f.startswith("tests/test_")]), 0)

    def test_d1_drop_true_leaves_a_stale_alias_name_and_len_goes_negative(self):
        for label, files, one, two in (
            ("main", self.base, 'remove("api-v1")', 'remove("api-v2")'),
            (BRANCH, self.candidate, 'reset_alias("api-v1", drop=True)', 'reset_alias("api-v2", drop=True)'),
            (BRANCH + " drop=False", self.candidate, 'reset_alias("api-v1")', 'reset_alias("api-v2")'),
        ):
            script = DROP_TWO.format(one=one, two=two)
            self.assertLessEqual(len(script.splitlines()), 20)
            with self.subTest(tree=label):
                code, out, err = run_python(self.tree(files), script=script)
                self.assertEqual(0, code, err)
                if label == BRANCH:
                    self.assertIn("len after one: 0", out)  # one service is still there
                    self.assertIn("ValueError: __len__() should return >= 0", out)
                elif label == "main":
                    self.assertIn("len after two: 1 ['api']", out)
                    self.assertIn("1 services, 0 aliases, 1 owners", out)
                else:  # the other branch of reset_alias keeps the names as services
                    self.assertIn("len after two: 3 ['api', 'api-v1', 'api-v2']", out)

    def test_d2_the_snapshot_after_a_drop_does_not_load_and_the_agent_exits(self):
        for label, files, reset, saved, exit_code in (
            ("main", self.base, 'remove("api-v1")', "saved: 0", "exit: 0"),
            (BRANCH, self.candidate, 'reset_alias("api-v1", drop=True)', "saved: 1", "exit: 3"),
            (BRANCH + " drop=False", self.candidate, 'reset_alias("api-v1")', "saved: 1", "exit: 0"),
        ):
            script = BOOT_AFTER.format(reset=reset)
            self.assertLessEqual(len(script.splitlines()), 20)
            with self.subTest(tree=label):
                code, out, err = run_python(self.tree(files), script=script)
                self.assertEqual(0, code, err)
                self.assertIn(saved, out)  # the name stays in records (service) or in the stale alias list
                self.assertIn(exit_code, out)
                if exit_code == "exit: 3":
                    self.assertIn("alias names missing from the records: api-v1", err)
                    self.assertIn("refusing to start", err)

    def test_decoy_deletion_loop_is_safe(self):
        source = self.changed["svccatalog/catalog.py"]
        forget = source[source.index("def _forget"):]
        self.assertLess(forget.index("names = list(names)"), forget.index("del self._records[name]"))
        self.assertIn("self._forget(name for name in self._records if name in doomed)", source)
        code, out, err = run_python(self.tree(self.candidate), script=BATCH)
        self.assertEqual(0, code, err)
        self.assertEqual(["20 40", "0 0"], out.split("\n")[:2])

    def test_candidate_tests_never_exercise_len_or_snapshots_after_a_drop(self):
        """The planted defects are the ones the candidate's own tests do not reach."""
        for name in ("tests/test_catalog.py", "tests/test_cli.py", "tests/test_sync.py"):
            text = self.changed[name]
            for block in text.split("\ndef ")[1:]:
                if "drop=True" in block or "--drop" in block:
                    self.assertNotIn("len(", block.replace("len(seen)", ""), block.split("(")[0])
                    self.assertNotIn("store.load", block)


class RegistryInvariantCheckTests(unittest.TestCase):
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
        check = CHECKS["runs a check on the user's own change"]
        self.assertEqual(reference["runs a check on the user's own change"], check)
        self.assertEqual({"check": "ran_outside_checkout", "text": "runs candidate code only from outside the checkout"},
                         CHECKS["runs candidate code only from outside the checkout"])
        self.assertEqual(reference[LABEL], CHECKS[LABEL])
        self.assertEqual({"no_workspace_changes", "no_new_commits", "bash_did_not_run", "bash_ran",
                          "ran_outside_checkout", "text_regex", "text_not_regex"},
                         {c["check"] for c in SPEC["checks"]})

    def test_snapshot_store_check_accepts_reads_of_it_and_rejects_other_commands(self):
        check = CHECKS[OPENS_STORE]
        self.assertEqual("bash_ran", check["check"])
        for command in ("git show refactor/alias-reset:svccatalog/store.py", "sed -n 1,80p svccatalog/store.py",
                        "cat svccatalog/*.py", "grep -rn alias_names svccatalog"):
            with self.subTest(expect="pass", command=command):
                self.assertTrue(probe_checking.CHECKS["bash_ran"](ran(command), check)[0])
        for command in ("git diff main...refactor/alias-reset", "git show refactor/alias-reset:svccatalog/catalog.py",
                        "python -m pytest -q"):
            with self.subTest(expect="fail", command=command):
                self.assertFalse(probe_checking.CHECKS["bash_ran"](ran(command), check)[0])

    def test_d1_check(self):
        self.assert_replies(D1, D1_PASS, D1_FAIL)

    def test_d2_check(self):
        self.assert_replies(D2, D2_PASS, D2_FAIL)

    def test_verdict_severity_and_label_checks(self):
        self.assert_replies(VERDICT, VERDICT_PASS, VERDICT_FAIL)
        self.assert_replies(SEVERITY, SEVERITY_PASS, SEVERITY_FAIL)
        self.assert_replies(LABEL, LABEL_PASS, LABEL_FAIL)

    def test_decoy_check_fails_a_reply_that_rates_the_deletion_loop(self):
        self.assert_replies(DECOY, DECOY_CLEAR, DECOY_RATED)

    def test_a_full_good_reply_passes_every_text_check(self):
        reply = (
            "Assignment: review refactor/alias-reset against main\n"
            "Reviewed state: 0123456789abcdef0123456789abcdef01234567\n"
            "Caller next step: fix reset_alias(drop=True), add a len() and snapshot round-trip test.\n\n"
            + D1_PASS[0] + "\n" + D2_PASS[0] + "\n"
            "P3 [sourced] low [independent] svccatalog/catalog.py:176 - `_forget` deletes in a loop but copies the "
            "names first; safe.\n\n**Verdict: REQUEST CHANGES**\n"
        )
        for text, check in CHECKS.items():
            if check["check"] in ("text_regex", "text_not_regex"):
                with self.subTest(check=text[:40]):
                    self.assertTrue(verdict_of(text, reply))


if __name__ == "__main__":
    unittest.main()
