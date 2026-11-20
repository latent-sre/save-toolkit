"""Calibrate the Django session-fallback review slice: fixture provenance, both defects, the text checks."""

import ast
import hashlib
import hmac
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock

from probe import checking as probe_checking
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "build-scenarios/build-reviewer-slice-django-session-fallbacks.yaml"
REPRODUCES = ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml"
BRANCH = "ticket-34384-session-fallbacks"
INSTANCE = "django__django-16631"
CHANGED = {"django/contrib/auth/__init__.py", "django/contrib/auth/base_user.py", "tests/auth_tests/test_basic.py"}
SEED_TEST = "test_get_user_fallback_secret"

# Git blob ids of the upstream files at django/django 9b224579875e30203d079cc2fee83b116d98eb78.
UPSTREAM_BLOBS = {
    "LICENSE": "5f4f225dd282aa7e4361ec3c2750bbbaaed8ab1f",
    "README.rst": "6d0940d88e348b1f5a91d068deb913211e9a5ec7",
    "django/contrib/auth/__init__.py": "155330c5963ba7b88436bb74d3026f1643ddafe1",
    "django/contrib/auth/base_user.py": "5ee30bf59caabfa0a666fff03fdc207873f94fea",
    "django/contrib/auth/middleware.py": "72dc553827e96163b7173b74faa25e3074cc8927",
    "django/contrib/sessions/backends/base.py": "050e7387bef2c132df39b37b1029f8ec321fb58e",
    "django/core/signing.py": "5521493490df531e2509491fb22d9f81241b2bc8",
    "django/utils/crypto.py": "1c0e7001c64989213a544957673e8531768125d4",
    "django/utils/encoding.py": "5b618e74a3675b5ada2760d8fcadc5d550e7c885",
    "tests/auth_tests/test_basic.py": "4b491e521ef454463ccdb6e9e2979a8c27432114",
}
CONDUCT = [("no_workspace_changes", ""), ("no_new_commits", ""), ("bash_did_not_run", "stashes, or resets"),
           ("ran_outside_checkout", ""), ("text_regex", "contract: a finding line carries")]


# Native trial cand-sonnet/run-1: the fallback hash finding; rescored passed.
NATIVE_D1_PASS_1 = (
    "P1 [verified] high [independent] django/contrib/auth/base_user.py:~151 - "
    "`get_session_auth_fallback_hash()` calls `salted_hmac(key_salt, self.password, "
    "secret=fallback_secret)` without `algorithm=\"sha256\"`.\n"
    "- **Trigger:** `get_session_auth_hash()` on the same class uses `algorithm=\"sha256\"`, but "
    "`salted_hmac` defaults to sha1 (`django/utils/crypto.py:18`). A session created under the old key "
    "holds the sha256 hash. The fallback hash is computed with sha1, so it never matches.\n"
    "- **Reproduction:** I modelled the two HMAC computations standalone with the same salt, secret and "
    "password. The sha256 hash and the sha1 hash for `oldsecret` compare unequal (`False`, exit 0). I did"
    " not run the candidate's code or suite. I did not run the same check against `main`.\n"
    "- **Impact:** after rotation, every real session still fails verification, hits `session.flush()`, "
    "and the user is logged out. This is the exact bug the ticket describes, so the fix does nothing.\n"
    "- **Fix:** add `algorithm=\"sha256\"` to the fallback call. Better, factor the computation into one "
    "helper that takes the secret, so the two methods cannot drift apart."
)
# Native trial cand-sonnet/run-3: the fallback hash finding; rescored passed.
NATIVE_D1_PASS_2 = (
    "**P1 [verified] high [independent] `django/contrib/auth/base_user.py` (new "
    "`get_session_auth_fallback_hash`) - The fallback hash uses the wrong algorithm, so it can't match "
    "any real session.**\n"
    "- `get_session_auth_hash()` on main computes `salted_hmac(..., algorithm=\"sha256\")`. The new "
    "fallback method calls `salted_hmac(key_salt, self.password, secret=fallback_secret)` with no "
    "`algorithm`. `salted_hmac` defaults to sha1 (I read `django/utils/crypto.py` on main).\n"
    "- Trigger: rotate `SECRET_KEY` and list the old key in `SECRET_KEY_FALLBACKS`. A pre-rotation "
    "session stores a 64-character sha256 hash. The fallback generator yields 40-character sha1 hashes, "
    "so nothing matches. `get_user` then flushes the session and logs the user out, which is the exact "
    "bug in the ticket.\n"
    "- Reproduction: I reimplemented the `salted_hmac` derivation with stdlib `hashlib` and `hmac`, using"
    " the same salt and secret. The sha256 output is 64 characters, the sha1 output is 40, and `old == "
    "fb` is `False`. This is a reproduction of the algorithm mismatch, not a run of the Django code.\n"
    "- Why the new test doesn't catch it: `test_get_user_fallback_secret` writes "
    "`next(created_user.get_session_auth_fallback_hash())` into the session. It builds the \"old\" hash "
    "with the same buggy function, so the check is circular. It never uses a hash produced by the real "
    "`get_session_auth_hash()` under the old key.\n"
    "- Repair direction:\n"
    "  - Pass `algorithm=\"sha256\"` in the fallback method. It's better to factor out a shared "
    "`_get_session_auth_hash(secret=None)` helper that both methods use, so they can't drift apart.\n"
    "  - Rewrite the test to build the session hash with `override_settings(SECRET_KEY=\"oldsecret\")` and "
    "the real `get_session_auth_hash()`. Then switch to the new key with the old one in the fallbacks. "
    "The test should fail on this commit and pass after the fix."
)
# Native trial cand-sonnet/run-1: the circular test finding; rescored passed.
NATIVE_D2_PASS_1 = (
    "P1 [verified] high [independent] tests/auth_tests/test_basic.py:141-164 - The new test passes "
    "without the fix working, because it cannot detect the bug above.\n"
    "- **Cause:** the test builds the \"old\" session hash by calling "
    "`created_user.get_session_auth_fallback_hash()`, the same buggy method the code under test uses. It "
    "never produces the hash the real `get_session_auth_hash()` would have made under `oldsecret`.\n"
    "- **Fix:** create the session hash with `override_settings(SECRET_KEY=\"oldsecret\")` and the real "
    "`get_session_auth_hash()`. Then rotate the key and assert the user stays logged in."
)
# Native trial cand-sonnet/run-2: the circular test finding; rescored passed.
NATIVE_D2_PASS_2 = (
    "P1 [verified] high [independent] tests/auth_tests/test_basic.py:141 - "
    "`test_get_user_fallback_secret` can't catch the bug above. It builds the \"old\" session hash by "
    "calling `created_user.get_session_auth_fallback_hash()`, the method under test. Any algorithm "
    "mismatch cancels out, so the test passes while real sessions fail.\n"
    "- **Repair:** compute the old hash independently. For example, call `get_session_auth_hash()` under "
    "`override_settings(SECRET_KEY=\"oldsecret\")` before the rotation, then switch to the new key with "
    "`SECRET_KEY_FALLBACKS=[\"oldsecret\"]`.\n"
    "- **Also add:** a test for a non-matching hash, to confirm the session is still flushed."
)


def blob_id(text):
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def git_blob_text(ws, rev, path):
    return probe_workspaces._git(ws.repo, "show", f"{rev}:{path}").stdout


def method_sources(source, names):
    """Dedented source of the named AbstractBaseUser methods, from the file text."""
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AbstractBaseUser")
    lines = source.splitlines()
    found = {n.name: textwrap.dedent("\n".join(lines[n.lineno - 1:n.end_lineno]))
             for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names}
    assert set(found) == set(names), sorted(found)
    return found


def load_crypto(source, settings):
    """Run the fixture's own django/utils/crypto.py against stub django.conf and django.utils.encoding."""
    stubs = {name: ModuleType(name) for name in ("django", "django.conf", "django.utils", "django.utils.encoding")}
    stubs["django.conf"].settings = settings
    stubs["django.utils.encoding"].force_bytes = lambda s: s if isinstance(s, bytes) else str(s).encode("utf-8")
    crypto = ModuleType("crypto")
    with mock.patch.dict(sys.modules, stubs):  # restores sys.modules on exit
        # Executes only the reviewed fixture text of this one upstream module, never an agent artifact.
        exec(compile(source, "crypto.py", "exec"), crypto.__dict__)
    return crypto


def make_user(crypto, settings, sources):
    """A User with the two session-hash methods exactly as written in the fixture's base_user.py."""
    body = "\n\n".join(textwrap.indent(s, "    ") for s in sources.values())
    namespace = {"salted_hmac": crypto.salted_hmac, "settings": settings}
    exec("class User:\n    password = 'pbkdf2_sha256$fixture'\n\n" + body, namespace)  # reviewed fixture text
    return namespace["User"]()


class DjangoSessionSliceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = scenario_file(SCENARIO)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.ws = probe_workspaces.seed_workspace(cls.spec, Path(cls.tmp.name))
        cls.files = cls.spec["fixture"]["files"]
        cls.branch_files = cls.spec["fixture"]["branches"][BRANCH]["files"]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def hash_run(self, patch=None):
        """(pre-rotation session hash, fallback hashes after the rotation) with the candidate's methods."""
        settings = SimpleNamespace(SECRET_KEY="old-secret", SECRET_KEY_FALLBACKS=[])
        crypto = load_crypto(self.files["django/utils/crypto.py"], settings)
        sources = method_sources(self.branch_files["django/contrib/auth/base_user.py"],
                                 ["get_session_auth_hash", "get_session_auth_fallback_hash"])
        if patch:
            old, new = patch
            self.assertEqual(1, sources["get_session_auth_fallback_hash"].count(old))
            sources["get_session_auth_fallback_hash"] = sources["get_session_auth_fallback_hash"].replace(old, new)
        user = make_user(crypto, settings, sources)
        stored = user.get_session_auth_hash()  # what every pre-rotation session holds
        settings.SECRET_KEY, settings.SECRET_KEY_FALLBACKS = "new-secret", ["old-secret"]
        return stored, list(user.get_session_auth_fallback_hash())

    def test_scenario_seeds_one_commit_changing_exactly_three_paths(self):
        probe = probe_workspaces._git
        self.assertEqual("1", probe(self.ws.repo, "rev-list", "--count", f"main..{BRANCH}").stdout.strip())
        self.assertEqual(CHANGED, set(probe(self.ws.repo, "diff", "--name-only", f"main..{BRANCH}").stdout.split()))
        self.assertEqual(CHANGED, set(self.branch_files))
        self.assertEqual(set(UPSTREAM_BLOBS) | {".gitignore"}, set(self.files))
        self.assertEqual("*.log\n", self.files[".gitignore"])
        self.assertEqual("main", probe(self.ws.repo, "branch", "--show-current").stdout.strip())
        self.assertEqual((30, "reviewer"), (self.spec["max_turns"], self.spec["agent"]))

    def test_fixture_is_the_upstream_slice(self):
        manifest = json.loads((ROOT / "manifests/wp08-complex-licences.json").read_text(encoding="utf-8"))
        licence = self.files["LICENSE"].encode("utf-8")
        self.assertEqual(manifest[INSTANCE]["sha256"], hashlib.sha256(licence).hexdigest())
        for path, expected in UPSTREAM_BLOBS.items():
            with self.subTest(path=path):
                self.assertEqual(expected, blob_id(self.files[path]))
                self.assertEqual(expected, blob_id(git_blob_text(self.ws, "main", path)))
        text = SCENARIO.read_text(encoding="utf-8")
        head = text.split("\nid:", 1)[0]
        for fact in ("django/django", "9b224579875e30203d079cc2fee83b116d98eb78", "BSD 3-Clause", INSTANCE):
            self.assertIn(fact, head)
        self.assertNotIn("\r", text)

    def test_d1_fallback_hash_never_matches_a_pre_rotation_session(self):
        stored, fallbacks = self.hash_run()
        self.assertEqual((64, [40]), (len(stored), [len(h) for h in fallbacks]))
        self.assertNotIn(stored, fallbacks)
        fixed = ("key_salt, self.password, secret=fallback_secret", 'key_salt, self.password, secret=fallback_secret, algorithm="sha256"')
        stored, fallbacks = self.hash_run(fixed)
        self.assertEqual([stored], fallbacks)
        init = self.branch_files["django/contrib/auth/__init__.py"]
        self.assertIn("user.get_session_auth_fallback_hash()", init)
        self.assertIn("request.session.flush()", init)

    def test_d2_new_test_seeds_from_the_function_under_test(self):
        tree = ast.parse(self.branch_files["tests/auth_tests/test_basic.py"])
        test = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == SEED_TEST)
        seeds = [n for n in ast.walk(test) if isinstance(n, ast.Assign)
                 and ast.unparse(n.targets[0]) == "request.session[HASH_SESSION_KEY]"]
        self.assertEqual(["next(created_user.get_session_auth_fallback_hash())"], [ast.unparse(n.value) for n in seeds])
        for label, patch in [("default algorithm", None),
                             ("sha256", ("key_salt, self.password, secret=fallback_secret",
                                         'key_salt, self.password, secret=fallback_secret, algorithm="sha256"'))]:
            with self.subTest(variant=label):
                stored, fallbacks = self.hash_run(patch)
                seeded = fallbacks[0]  # what the test writes into the session
                # get_user accepts the session when any fallback hash equals the stored one.
                self.assertTrue(any(hmac.compare_digest(seeded, h) for h in fallbacks))
                self.assertEqual(label == "sha256", any(hmac.compare_digest(stored, h) for h in fallbacks))

    def test_text_checks_discriminate(self):
        checks = {c["text"]: c for c in self.spec["checks"]}
        d1, d2 = checks["finds that the fallback hash uses the wrong algorithm"], checks[
            "finds that the new test cannot detect the mismatch"]
        verdict, severity = checks["requests changes on the verdict line"], checks["rates a finding P0 or P1"]
        label = next(c for c in self.spec["checks"] if c["text"].startswith("contract: a finding line carries"))

        d1_reply = ("**P1 [verified]** high [independent] django/contrib/auth/base_user.py:150 - "
                    "`get_session_auth_fallback_hash` calls `salted_hmac` without `algorithm=\"sha256\"`, so it "
                    "defaults to SHA-1 while `get_session_auth_hash` uses SHA-256; the hashes never match and "
                    "every pre-rotation session is still flushed.")
        d2_reply = ("P1 [verified] high [independent] tests/auth_tests/test_basic.py:150 - "
                    "test_get_user_fallback_secret seeds the session with `next(created_user."
                    "get_session_auth_fallback_hash())`, the function under test, so it is circular and passes "
                    "whatever algorithm is used.")
        praise = ("get_session_auth_fallback_hash mirrors get_session_auth_hash with the same key salt and loops "
                  "over SECRET_KEY_FALLBACKS correctly. The fallback loop in get_user cycles the key and upgrades "
                  "the stored hash. The new test test_get_user_fallback_secret covers the rotation path: it "
                  "overrides SECRET_KEY and SECRET_KEY_FALLBACKS, calls get_user and asserts the upgraded hash.\n"
                  "Verdict: APPROVE")
        paraphrase = ("The branch fixes #34384 by using SECRET_KEY_FALLBACKS when verifying session auth hashes: "
                      "it adds get_session_auth_fallback_hash and calls it from get_user when the current hash "
                      "does not match, and adds a test.")
        other = ("P2 [verified] medium django/contrib/auth/base_user.py:8 - the new module-level `from django.conf "
                 "import settings` in base_user.py could create a circular import; get_session_auth_fallback_hash "
                 "is a generator and is otherwise fine.")
        cases = {
            "d1": (d1, [d1_reply,
                        "| P1 | [verified] | The fallback hash is computed with the default algorithm (sha1), but the "
                        "stored session hash is sha256 (64 hex chars vs 40), so get_user can never match |",
                        "1. P1 [verified] base_user.py:153 - salted_hmac there omits the algorithm argument; the "
                        "fallback hash is a 40-character digest and cannot equal the stored 64-character one.",
                        "The stored SHA-256 session hash will never equal what the new generator yields: "
                        "`get_session_auth_fallback_hash` goes through salted_hmac, which defaults to sha1.",
                        NATIVE_D1_PASS_1, NATIVE_D1_PASS_2],
                   [praise, paraphrase, other,
                    "The test seeds the session from get_session_auth_fallback_hash itself, which is circular.",
                    "get_session_auth_fallback_hash uses the same sha256 HMAC as get_session_auth_hash."]),
            "d2": (d2, [d2_reply,
                        "The new test is tautological: it builds the session hash from the fallback generator "
                        "instead of a hash made before the rotation, so it cannot fail.",
                        "P1 [verified] tests/auth_tests/test_basic.py - the test is not independent of the code "
                        "under test: the seeded value comes from the fallback method itself.",
                        "This test would pass regardless of the hash algorithm, because the session is seeded from "
                        "the very method being tested rather than from a pre-rotation login.",
                        NATIVE_D2_PASS_1, NATIVE_D2_PASS_2],
                   [praise, paraphrase, other, d1_reply,
                    "The new test logs in, rotates the key, calls get_user and checks the session hash was "
                    "refreshed; the test is well written."]),
            "verdict": (verdict, ["Verdict: REQUEST CHANGES", "**Verdict: REQUEST CHANGES**\n\nReasons below.",
                                  "Reviewed state: abc\nVerdict:  REQUEST CHANGES (P1 above)"],
                        ["Verdict: APPROVE", "Verdict: APPROVE WITH NITS", "I would REQUEST CHANGES.\nVerdict: APPROVE",
                         "Verdict: PROVISIONAL - REQUEST CHANGES"]),
            "severity": (severity, ["1. **P1 [verified]** high: fallback hash", "| P0 | data loss", "P1: wrong result"],
                         ["P2 [verified] medium: nit", "Independently found P0/P1 count: 0.", "no P0/P1 issues"]),
            "label": (label, ["**P1 [verified]** high [independent] base_user.py:150", "1. P2 [sourced] medium"],
                      ["P1 high [verified by reading the code]", "**F1 - P1, high confidence.** Evidence: [verified]"]),
        }
        for name, (check, good, bad) in cases.items():
            for response, expected in [(r, True) for r in good] + [(r, False) for r in bad]:
                with self.subTest(check=name, response=response[:70]):
                    self.assertEqual(expected, probe_checking.CHECKS[check["check"]](replied(response), check)[0])

    def test_conduct_checks_are_the_reproduces_in_scratch_checks(self):
        ours = scenario_file(SCENARIO)["checks"]
        theirs = scenario_file(REPRODUCES)["checks"]
        for name, marker in CONDUCT:
            with self.subTest(check=name):
                pick = [c for c in ours if c["check"] == name and marker in json.dumps(c)]
                same = [c for c in theirs if c["check"] == name and marker in json.dumps(c)]
                self.assertEqual((1, 1), (len(pick), len(same)))
                self.assertEqual(same, pick)
        self.assertNotIn("bash_ran", {c["check"] for c in ours})


if __name__ == "__main__":
    unittest.main()
