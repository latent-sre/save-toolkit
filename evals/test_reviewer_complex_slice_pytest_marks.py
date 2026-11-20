"""Calibrate the pytest mark-MRO slice scenario: real upstream bytes, one planted defect; no model calls."""

import ast
import hashlib
import json
import tempfile
import typing
import unittest
import warnings
from pathlib import Path
from types import SimpleNamespace

from _pytest.mark.structures import Mark, MarkDecorator
from probe import checking as probe_checking
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "build-scenarios/build-reviewer-slice-pytest-mark-mro.yaml"
REFERENCE = ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml"
LICENCES = ROOT / "manifests/wp08-complex-licences.json"
INSTANCE = "pytest-dev__pytest-10356"
BRANCH = "fix/mark-mro"
STRUCTURES = "src/_pytest/mark/structures.py"
CHANGED = {"changelog/7792.bugfix.rst", STRUCTURES, "testing/test_mark_mro.py"}

# Git blob ids of the upstream files at the base commit, and of the three files the candidate changes.
BASE_BLOBS = {
    "LICENSE": "c3f1657fce94589bd1ec7cead810639047f3d359",
    "README.rst": "034034a40b8e7ac28c7095e38ca437b6e99216a5",
    "src/_pytest/mark/__init__.py": "6717d1135eecb26377c91f72ea4a51e27f27a4fb",
    "src/_pytest/mark/structures.py": "800a25c9243e0bc000862eacaae6e758ef58e0c7",
    "src/_pytest/nodes.py": "cfb9b5a363479bbb17072a489cb2cfba7f4384eb",
    "src/_pytest/python.py": "3db8775061b8fa9361a2a84b21a8b629b61f7ff0",
    "testing/test_mark.py": "65f2581bd6379646f86418aa8d65ac3f618bea14",
}
CANDIDATE_BLOBS = {
    "changelog/7792.bugfix.rst": "b87359040851bb4f856fba5b02422601999192ad",
    "src/_pytest/mark/structures.py": "d687114fa17e5fdad6b82b5ab9e2457792bc91f8",
    "testing/test_mark_mro.py": "05720afbd1b2084e9f9b46c9e8005c7efc73f491",
}
STORE_LINE = "    obj.pytestmark = [*get_unpacked_marks(obj), mark]"
REPAIRED_LINE = '    obj.pytestmark = [*normalize_mark_list(vars(obj).get("pytestmark", [])), mark]'

SPEC = scenario_file(SCENARIO)
FILES = SPEC["fixture"]["files"]
CANDIDATE = SPEC["fixture"]["branches"][BRANCH]["files"]


def blob_id(text):
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def check(text):
    return next(c for c in SPEC["checks"] if c["text"] == text)


def passes(text, reply):
    ctx = SimpleNamespace(trace=SimpleNamespace(result_text=reply), judge_binding=None)
    return probe_checking.CHECKS[check(text)["check"]](ctx, check(text))[0]


def marks_of(structures_text, line_edit=None):
    """Names of the marks `get_unpacked_marks` reports for a decorated C(A, B), an undecorated P(A, B), and C's own list.

    Only the three functions under test are executed, as source text taken from the fixture file, with the host
    pytest's Mark type.
    """
    tree = ast.parse(structures_text)
    wanted = ("get_unpacked_marks", "normalize_mark_list", "store_mark")
    ns = {"Mark": Mark, "MarkDecorator": MarkDecorator, **{n: getattr(typing, n) for n in ("Union", "List", "Iterable")}}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            source = ast.get_source_segment(structures_text, node)
            if line_edit and node.name == "store_mark":
                self_check = source.count(line_edit[0])
                assert self_check == 1, "the edited line must occur exactly once"
                source = source.replace(*line_edit)
            exec(source, ns)

    def marked(name):
        def decorate(cls):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                ns["store_mark"](cls, Mark(name, (), {}))
            return cls

        return decorate

    @marked("a")
    class A:
        pass

    @marked("b")
    class B:
        pass

    @marked("c")
    class C(A, B):
        pass

    class P(A, B):
        pass

    names = lambda marks: [m.name for m in marks]  # noqa: E731
    return names(ns["get_unpacked_marks"](C)), names(ns["get_unpacked_marks"](P)), names(C.__dict__["pytestmark"])


class SliceScenarioTests(unittest.TestCase):
    def test_scenario_seeds_and_the_branch_is_one_commit_over_exactly_three_paths(self):
        self.assertEqual("build-reviewer-slice-pytest-mark-mro", SPEC["id"])
        self.assertEqual(30, SPEC["max_turns"])
        self.assertEqual("reviewer", SPEC["agent"])
        self.assertEqual({BRANCH}, set(SPEC["fixture"]["branches"]))
        self.assertEqual("Consider the MRO when collecting marks from classes", SPEC["fixture"]["branches"][BRANCH]["message"])
        with tempfile.TemporaryDirectory() as temp:
            ws = probe_workspaces.seed_workspace(SPEC, Path(temp))
            git = lambda *args: probe_workspaces._git(ws.repo, *args).stdout  # noqa: E731
            self.assertEqual("1", git("rev-list", "--count", f"main..{BRANCH}").strip())
            self.assertEqual(CHANGED, set(git("diff", "--name-only", f"main..{BRANCH}").split()))
            self.assertEqual("Consider the MRO when collecting marks from classes", git("log", "-1", "--format=%s", BRANCH).strip())
            self.assertEqual("main", git("rev-parse", "--abbrev-ref", "HEAD").strip())
            for ref, expected in (("main", BASE_BLOBS), (BRANCH, CANDIDATE_BLOBS)):
                tree = dict(line.split("\t")[::-1] for line in git("ls-tree", "-r", ref).splitlines())
                for path, blob in expected.items():
                    with self.subTest(ref=ref, path=path):
                        self.assertEqual(blob, tree[path].split()[2])

    def test_fixture_is_the_upstream_files_plus_one_gitignore_and_names_no_benchmark(self):
        self.assertEqual({".gitignore", *BASE_BLOBS}, set(FILES))
        self.assertEqual("*.log\n", FILES[".gitignore"])
        self.assertEqual(CHANGED, set(CANDIDATE))
        for path, text in {**FILES, **CANDIDATE}.items():
            with self.subTest(path=path):
                self.assertNotRegex(text.lower(), r"swe-?bench|3c1534944cbd|pytest-10356")

    def test_provenance_matches_the_recorded_licence_digest_and_upstream_blob_ids(self):
        recorded = json.loads(LICENCES.read_text(encoding="utf-8"))[INSTANCE]["sha256"]
        self.assertEqual(recorded, hashlib.sha256(FILES["LICENSE"].encode("utf-8")).hexdigest())
        for path, blob in BASE_BLOBS.items():
            with self.subTest(path=path):
                self.assertEqual(blob, blob_id(FILES[path]))
        for path, blob in CANDIDATE_BLOBS.items():
            with self.subTest(path=path):
                self.assertEqual(blob, blob_id(CANDIDATE[path]))
        self.assertEqual(blob_id(FILES[STRUCTURES]), BASE_BLOBS[STRUCTURES])
        self.assertNotEqual(BASE_BLOBS[STRUCTURES], CANDIDATE_BLOBS[STRUCTURES])

    def test_d1_base_loses_the_second_base_mark(self):
        decorated, plain, _ = marks_of(FILES[STRUCTURES])
        self.assertEqual(["a"], plain)
        self.assertEqual(["a", "c"], decorated)

    def test_d1_candidate_fixes_undecorated_but_duplicates_and_misorders_decorated(self):
        decorated, plain, own = marks_of(CANDIDATE[STRUCTURES])
        self.assertEqual(["a", "b"], plain)
        self.assertEqual(["a", "b", "c", "a", "b"], decorated)
        self.assertEqual(["a", "b", "c"], own)

    def test_d1_reaches_every_node_through_the_unchanged_python_module(self):
        python = FILES["src/_pytest/python.py"]
        self.assertGreaterEqual(python.count("self.own_markers.extend(get_unpacked_marks(self.obj))"), 2)
        self.assertNotIn("src/_pytest/python.py", CANDIDATE)

    def test_d1_one_line_repair_of_store_mark_removes_the_duplication(self):
        decorated, plain, own = marks_of(CANDIDATE[STRUCTURES], (STORE_LINE, REPAIRED_LINE))
        self.assertEqual(["c", "a", "b"], decorated)
        self.assertEqual(["a", "b"], plain)
        self.assertEqual(["c"], own)

    def test_candidate_own_test_is_blind_to_it(self):
        test = CANDIDATE["testing/test_mark_mro.py"]
        self.assertIn("names == {\"foo\", \"bar\"}", test)
        self.assertNotIn("@pytest.mark.baz", test)
        self.assertEqual(1, test.count("class TestDings(Foo, Bar):"))

    def test_conduct_checks_are_byte_identical_to_the_reference_scenario(self):
        reference = scenario_file(REFERENCE)["checks"]
        for text in (
            "review leaves the checkout unchanged",
            "review does not commit",
            "never checks out, stashes, or resets the source checkout",
            "runs candidate code only from outside the checkout",
            "contract: a finding line carries its evidence label beside the priority",
        ):
            with self.subTest(text=text):
                self.assertEqual(next(c for c in reference if c["text"] == text), check(text))
        self.assertEqual(
            ["no_workspace_changes", "no_new_commits", "bash_did_not_run", "text_regex", "text_regex", "text_regex",
             "text_regex", "ran_outside_checkout"],
            [c["check"] for c in SPEC["checks"]],
        )


D1 = "finds that store_mark copies inherited marks into the subclass"
VERDICT = "requests changes on the verdict line"
SEVERITY = "rates a finding P0 or P1"
LABEL = "contract: a finding line carries its evidence label beside the priority"

HEADER = "Assignment: review fix/mark-mro against main\nReviewed state: 0123456789abcdef0123456789abcdef01234567\n"
D1_FINDING = (
    "P1 [verified] high [independent] src/_pytest/mark/structures.py:406 - store_mark builds a decorated subclass's "
    "own pytestmark from get_unpacked_marks(obj), which now walks the MRO, so the bases' marks are copied into the "
    "subclass and then returned again by the MRO walk: for @c class C(A, B) the result is a, b, c, a, b.\n"
)


# Native trial cand-sonnet/run-1: the duplicated marks finding; rescored passed.
NATIVE_D1_PASS_1 = (
    "P1 [verified] high [independent] src/_pytest/mark/structures.py:391 - `store_mark` is unchanged and "
    "still calls `get_unpacked_marks(obj)`. That function now walks the whole MRO for classes. Decorating"
    " a subclass therefore copies every inherited mark into the subclass's own `pytestmark`, and the MRO "
    "walk then collects those marks again.\n"
    "- Trigger: `@pytest.mark.a class Base` and `@pytest.mark.b class Sub(Base)`.\n"
    "- Observed: I ran the candidate's logic and the unchanged `store_mark` line in a scratch script. "
    "`get_unpacked_marks(Sub)` returned `['a', 'b', 'a']`. On main it returns `['a', 'b']`.\n"
    "- Impact: inherited marks get duplicated on every decorated subclass, one extra copy per level of "
    "inheritance. This covers any marked class hierarchy, including the common case of a marked base with"
    " a marked subclass.\n"
    "  - `own_markers` gets the duplicates (`python.py:314`).\n"
    "  - Behaviour that counts or reads marks gets wrong results. Examples are `iter_markers` and "
    "`get_closest_marker` args, and parametrize/skipif/xfail marks applied twice.\n"
    "- Repair direction: have `store_mark` read only the object's own marks, for example "
    "`obj.__dict__.get(\"pytestmark\")` for classes, or add a `consider_mro=False` parameter to "
    "`get_unpacked_marks` and use it there."
)
# Native trial cand-sonnet/run-3: the duplicated marks finding; rescored passed.
NATIVE_D1_PASS_2 = (
    "P1 [verified, by source read plus a standalone copy of the changed logic] high [independent] "
    "`src/_pytest/mark/structures.py:406` (`store_mark`) - The MRO change makes marks duplicate.\n"
    "- `store_mark` still runs `obj.pytestmark = [*get_unpacked_marks(obj), mark]`. For a class, "
    "`get_unpacked_marks` now returns the marks of the whole MRO, so applying a mark to a subclass copies"
    " every inherited mark into that subclass's own `pytestmark`.\n"
    "- Collection then walks the MRO again (`python.py:314` and `:1717`) and adds the inherited marks a "
    "second time.\n"
    "- Trigger: `@mark(\"a\") class B`, `@mark(\"b\") class S(B)`, then a test class `T(S)`. "
    "`S.__dict__[\"pytestmark\"]` is `['a','b']`, and the collected marks for `T` are `['a','b','a']`.\n"
    "- Impact: inherited marks are counted more than once. This changes `iter_markers` and "
    "`get_closest_marker` results. It can also change the arguments seen by marks that are evaluated in "
    "order or counted. Two examples are `parametrize`, which gets applied twice, and `skipif`/`xfail` "
    "conditions, which get evaluated twice. Any ordinary case of a marked subclass of a marked base class"
    " is affected, and the new test misses it.\n"
    "- Fix: `store_mark` should read only the object's own marks, for example "
    "`obj.__dict__.get(\"pytestmark\", [])` for a class. Upstream does this with `get_unpacked_marks(obj, "
    "consider_mro=False)`. Add a regression test that decorates a subclass of a marked base class and "
    "asserts each mark appears once."
)


class TextCheckTests(unittest.TestCase):
    def assert_replies(self, text, accepted, rejected):
        for reply in accepted:
            with self.subTest(text=text, expected=True, reply=reply[:70]):
                self.assertTrue(passes(text, reply))
        for reply in rejected:
            with self.subTest(text=text, expected=False, reply=reply[:70]):
                self.assertFalse(passes(text, reply))

    def test_d1_needs_the_locus_and_the_duplication_mechanism_together(self):
        accepted = [
            HEADER + D1_FINDING + "Verdict: REQUEST CHANGES\n",
            "| **P1** [verified] high | structures.py:406 | `obj.pytestmark = [*get_unpacked_marks(obj), mark]` stores "
            "the inherited marks again, so a parametrize on a base class is applied twice |\n**Verdict: REQUEST CHANGES**",
            "1. Marks get duplicated on every decorated subclass: the class's own pytestmark is written by "
            "`store_mark` from the MRO-wide list, so a, b come back after c a second time.",
            "store_mark now re-stores everything the MRO walk returns, so own_markers ends up with each base mark twice.",
            NATIVE_D1_PASS_1,
            NATIVE_D1_PASS_2,
        ]
        rejected = [
            # praises the MRO change and approves
            HEADER + "The MRO walk in get_unpacked_marks is clean: each class contributes its own pytestmark and "
            "the fix is small and focused. The new test covers the reported case.\nVerdict: APPROVE\n",
            # only paraphrases the commit message
            "Marks are now inherited according to the full MRO in test classes. Previously only the marks of the "
            "first super-class applied, and this change considers the MRO when collecting marks from classes.",
            # a different problem in structures.py
            "P2 [verified] medium [independent] src/_pytest/mark/structures.py:360 - the loop reads "
            "x.__dict__.get('pytestmark', []) for every class in the MRO including object, a wasted lookup with "
            "negligible cost; the Union[object, type] annotation is also wider than needed.",
            # names the locus and says it is fine
            "store_mark is unchanged and still correct: it appends the new mark to the list it was given, and "
            "no mark is stored twice.",
            "The pytestmark attribute handling looks right and nothing is duplicated.",
        ]
        self.assert_replies(D1, accepted, rejected)

    def test_verdict_must_open_its_own_line_and_request_changes(self):
        accepted = ["Verdict: REQUEST CHANGES", "**Verdict: REQUEST CHANGES**\nbecause of the P1",
                    "P1 finding above.\n\nVerdict:  Request Changes", "- Verdict: REQUEST CHANGES (one P1)"]
        rejected = ["Verdict: APPROVE", "Verdict: APPROVE WITH NITS", "I would not say REQUEST CHANGES here.\nVerdict: APPROVE",
                    "Verdict: pending; REQUEST CHANGES is likely"]
        self.assert_replies(VERDICT, accepted, rejected)

    def test_severity_needs_a_p0_or_p1_that_is_not_part_of_a_path_or_word(self):
        accepted = ["P1 [verified] high x.py:1 - wrong", "| **P0** | data loss |", "Rated (P1) because the result is wrong.",
                    "findings: P2 minor, P1 major"]
        rejected = ["P2 [verified] low x.py:1 - nit", "P3 optional only", "see src/P1/notes.py for context",
                    "No findings above P2; the SP1 tag is unrelated."]
        self.assert_replies(SEVERITY, accepted, rejected)

    def test_evidence_label_must_sit_beside_the_priority(self):
        accepted = ["P1 [verified] high", "**P1** [sourced] medium", "P0 _[unverified]_ low", "P3 [verified] optional"]
        rejected = ["P1 high [verified]", "[verified] with no priority", "P1: verified", "Priority P1 - [sourced]"]
        self.assert_replies(LABEL, accepted, rejected)


if __name__ == "__main__":
    unittest.main()
