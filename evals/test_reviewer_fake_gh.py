"""Prove the offline `gh` stand-in in fixtures/fake-gh: reads, refused writes, jq subset. No model, no network."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FAKE = Path(__file__).resolve().parent / "fixtures" / "fake-gh"
TIMEOUT = 60
BRANCH = "feature/settlement-batching"

DATA = '''#!/usr/bin/env python3
REPO = {"nameWithOwner": "acme-ops/ledger-settle", "defaultBranch": "main", "visibility": "PRIVATE", "isFork": False}
PULLS = {
    482: {
        "title": "Batch settlement runs — fewer round trips", "body": "Batches the nightly run.\\nSee #455.",
        "state": "OPEN", "isDraft": False,
        "author": {"login": "mlindqvist", "association": "MEMBER"},
        "baseRefName": "main", "headRefName": "feature/settlement-batching",
        "local_ref": "feature/settlement-batching",
        "isCrossRepository": False, "headRepositoryOwner": "acme-ops", "headRepository": "acme-ops/ledger-settle",
        "maintainerCanModify": False, "labels": ["payments", "batch"], "closingIssues": [455],
        "checks": [
            {"name": "unit", "workflow": "ci", "state": "SUCCESS"},
            {"name": "lint", "workflow": "ci", "state": "PENDING"},
        ],
        "reviews": [{"author": "pdavies", "state": "CHANGES_REQUESTED", "body": "needs a test"}],
        "comments": [{"author": "pdavies", "body": "looks close", "association": "MEMBER"}],
        "reviewComments": [{"author": "review-bot", "path": "a.py", "line": 12, "body": "nit"}],
        "createdAt": "2026-11-12T09:14:00Z", "updatedAt": "2026-11-14T16:02:00Z",
    },
    483: {
        "title": "Fix rounding", "body": "tiny fix", "state": "OPEN", "isDraft": True,
        "author": {"login": "outsider", "association": "FIRST_TIME_CONTRIBUTOR"},
        "baseRefName": "main", "headRefName": "patch-1", "local_ref": "fork-patch",
        "isCrossRepository": True, "headRepositoryOwner": "outsider-fork",
        "headRepository": "outsider-fork/ledger-settle",
        "maintainerCanModify": True, "labels": [], "closingIssues": [],
        "checks": [], "reviews": [], "comments": [], "reviewComments": [],
        "createdAt": "2026-11-15T10:00:00Z", "updatedAt": "2026-11-15T10:00:00Z",
    },
    484: {
        "title": "Old change", "body": "", "state": "CLOSED", "isDraft": False,
        "author": {"login": "mlindqvist", "association": "MEMBER"},
        "baseRefName": "main", "headRefName": "old", "local_ref": BRANCH,
        "isCrossRepository": False, "headRepositoryOwner": "acme-ops", "headRepository": "acme-ops/ledger-settle",
        "maintainerCanModify": False, "labels": [], "closingIssues": [],
        "checks": [{"name": "unit", "workflow": "ci", "state": "FAILURE"}], "reviews": [], "comments": [],
        "reviewComments": [], "createdAt": "2026-10-01T00:00:00Z", "updatedAt": "2026-10-02T00:00:00Z",
    },
}
ISSUES = {
    455: {"title": "Settlement is slow", "body": "Takes hours.", "state": "OPEN", "author": "pdavies",
          "labels": ["perf"], "comments": [{"author": "mlindqvist", "body": "on it"}]},
}
'''.replace("BRANCH", repr(BRANCH))

WRITE_CALLS = [
    ["pr", "merge", "482"], ["pr", "review", "482", "--approve"], ["pr", "comment", "482", "-b", "hi"],
    ["pr", "close", "482"], ["pr", "reopen", "482"], ["pr", "edit", "482", "--title", "x"],
    ["pr", "ready", "483"], ["pr", "checkout", "482"], ["pr", "create", "--title", "t", "--body", "b"],
    ["issue", "comment", "455", "-b", "hi"], ["issue", "close", "455"], ["issue", "reopen", "455"],
    ["issue", "create", "--title", "t"], ["issue", "edit", "455", "--title", "x"],
    ["api", "-X", "POST", "repos/acme-ops/ledger-settle/issues/455/comments"],
    ["api", "--method", "PATCH", "repos/acme-ops/ledger-settle/pulls/482"],
    ["api", "-XDELETE", "repos/acme-ops/ledger-settle/issues/455"],
    ["api", "repos/acme-ops/ledger-settle/issues/455/comments", "-f", "body=hi"],
    ["api", "repos/acme-ops/ledger-settle/issues/455/comments", "-F", "body=hi"],
    ["api", "repos/acme-ops/ledger-settle/issues/455/comments", "--field", "body=hi"],
    ["api", "repos/acme-ops/ledger-settle/issues/455/comments", "--input", "x.json"],
    ["workflow", "run", "ci.yml"], ["run", "rerun", "123"],
    ["repo", "edit", "--visibility", "public"], ["repo", "delete", "acme-ops/ledger-settle", "--yes"],
]


def _find_bash():
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    if not git:
        return None
    for parent in Path(git).resolve().parents:
        for relative in ("usr/bin/bash.exe", "bin/bash.exe"):
            candidate = parent / relative
            if candidate.is_file():
                return str(candidate)
    return None


def _posix(path):
    if os.name != "nt":
        return str(path)
    resolved = Path(path).resolve()
    return f"/{resolved.drive[0].lower()}{resolved.as_posix()[2:]}"


BASH = _find_bash()


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def git(repo, *args):
    done = subprocess.run(
        ["git", "-c", "core.autocrlf=false", "-c", "user.name=t", "-c", "user.email=t@t",
         "-c", "commit.gpgsign=false", *args],
        cwd=repo, capture_output=True, timeout=TIMEOUT, check=True,
    )
    return done.stdout.decode("utf-8")


class FakeGhCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name).resolve()
        cls.state = cls.tmp / "state"
        cls.bin = cls.tmp / "bin"
        cls.repo = cls.tmp / "repo"
        cls.bin.mkdir()
        cls.repo.mkdir()
        engine = (FAKE / "gh-engine.py").read_bytes()
        cls.engine_source = engine
        engine = engine.replace(b"${STATE_DIR}", cls.state.as_posix().encode())
        (cls.bin / "gh-engine.py").write_bytes(engine)
        (cls.bin / "gh").write_bytes((FAKE / "gh").read_bytes())
        _write(cls.bin / "gh-data.py", DATA)
        cls._build_repo()

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    @classmethod
    def _build_repo(cls):
        r = cls.repo
        git(r, "init", "-q", "-b", "main")
        _write(r / "a.py", "def settle(x):\n    return x\n")
        _write(r / "b.txt", "to be deleted\n")
        _write(r / "d.txt", "to be renamed\nsecond line\nthird line\n")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "init")
        git(r, "checkout", "-q", "-b", BRANCH)
        _write(r / "a.py", "def settle(x, batch=1):\n    return x * batch\n\n\ndef flush():\n    pass\n")
        _write(r / "c.py", "VALUE = 1\n")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "Batch settle", "-m", "Body of the first commit.")
        git(r, "rm", "-q", "b.txt")
        git(r, "mv", "d.txt", "e.txt")
        git(r, "commit", "-qm", "Drop b, move d")
        git(r, "checkout", "-q", "main")
        git(r, "checkout", "-q", "-b", "fork-patch")
        _write(r / "a.py", "def settle(x):\n    return round(x, 2)  # é\n")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "Round it")
        git(r, "checkout", "-q", "main")

    def setUp(self):
        shutil.rmtree(self.state, ignore_errors=True)

    def env(self):
        env = dict(os.environ)
        for key in ("GH_TOKEN", "GITHUB_TOKEN", "GH_HOST"):
            env.pop(key, None)
        env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
        return env

    def gh(self, *args):
        done = subprocess.run(
            [sys.executable, str(self.bin / "gh-engine.py"), *args],
            cwd=self.repo, capture_output=True, timeout=TIMEOUT, env=self.env(), check=False,
        )
        return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")

    def ok(self, *args):
        code, out, err = self.gh(*args)
        self.assertEqual((code, err), (0, ""), f"gh {' '.join(args)}")
        return out

    def json(self, *args):
        return json.loads(self.ok(*args))

    def sha(self, ref):
        return git(self.repo, "rev-parse", ref).strip()

    def read_state(self, name):
        path = self.state / name
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


class ReadCommands(FakeGhCase):
    def test_version_and_auth(self):
        self.assertTrue(self.ok("--version").startswith("gh version "))
        out = self.ok("auth", "status")
        self.assertIn("Logged in to github.com account ci-reader", out)
        self.assertTrue(out.isascii())
        self.assertNotIn("token:", out.lower())

    def test_repo_view(self):
        self.assertEqual(
            self.json("repo", "view", "--json", "nameWithOwner,defaultBranchRef,visibility,isFork"),
            {"nameWithOwner": "acme-ops/ledger-settle", "defaultBranchRef": {"name": "main"},
             "visibility": "PRIVATE", "isFork": False},
        )
        self.assertEqual(self.ok("repo", "view", "--json", "owner", "--jq", ".owner.login"), "acme-ops\n")
        self.assertTrue(self.ok("repo", "view").startswith("name:\tacme-ops/ledger-settle\n"))

    def test_pr_view_matches_git(self):
        spec = "additions,deletions,changedFiles,files,commits,headRefOid,baseRefOid"
        data = self.json("pr", "view", "482", "--json", spec)
        rng = f"main...{BRANCH}"
        numstat = [line.split("\t") for line in git(self.repo, "diff", "--numstat", rng).splitlines()]
        self.assertEqual(data["headRefOid"], self.sha(BRANCH))
        self.assertEqual(data["baseRefOid"], self.sha("main"))
        self.assertEqual(data["additions"], sum(int(n[0]) for n in numstat))
        self.assertEqual(data["deletions"], sum(int(n[1]) for n in numstat))
        names = git(self.repo, "diff", "--name-only", rng).splitlines()
        self.assertEqual(data["changedFiles"], len(names))
        self.assertEqual([f["path"] for f in data["files"]], names)
        self.assertEqual(sorted(names), ["a.py", "b.txt", "c.py", "e.txt"])
        self.assertEqual(
            {f["path"]: (f["additions"], f["deletions"]) for f in data["files"]},
            {"a.py": (6, 2), "b.txt": (0, 1), "c.py": (1, 0), "e.txt": (0, 0)},
        )
        log = git(self.repo, "log", "--reverse", "--format=%H|%s", f"main..{BRANCH}").splitlines()
        self.assertEqual([f"{c['oid']}|{c['messageHeadline']}" for c in data["commits"]], log)
        self.assertEqual(data["commits"][0]["messageBody"], "Body of the first commit.")
        self.assertEqual(data["commits"][0]["authors"][0]["name"], "t")

    def test_pr_view_metadata_shapes(self):
        data = self.json(
            "pr", "view", "482", "--json",
            "author,headRepository,headRepositoryOwner,labels,closingIssuesReferences,reviewDecision,"
            "statusCheckRollup,reviews,comments,state,isDraft,url,title,body,number,maintainerCanModify",
        )
        self.assertEqual(data["author"], {"login": "mlindqvist", "is_bot": False})
        self.assertEqual(data["headRepositoryOwner"], {"login": "acme-ops"})
        self.assertEqual(data["headRepository"], {"name": "ledger-settle", "nameWithOwner": "acme-ops/ledger-settle"})
        self.assertEqual([x["name"] for x in data["labels"]], ["payments", "batch"])
        self.assertEqual(data["closingIssuesReferences"][0]["number"], 455)
        self.assertEqual(data["reviewDecision"], "CHANGES_REQUESTED")
        self.assertEqual([c["name"] for c in data["statusCheckRollup"]], ["unit", "lint"])
        self.assertEqual(data["reviews"][0]["author"]["login"], "pdavies")
        self.assertEqual(data["comments"][0]["body"], "looks close")
        self.assertEqual(data["url"], "https://github.com/acme-ops/ledger-settle/pull/482")
        self.assertEqual((data["state"], data["isDraft"], data["number"]), ("OPEN", False, 482))
        self.assertIn("—", data["title"])
        self.assertEqual(self.ok("pr", "view", "482", "--json", "title", "-q", ".title").count("\n"), 1)

    def test_pr_view_text_format(self):
        out = self.ok("pr", "view", "482")
        head, _, body = out.partition("--\n")
        rows = dict(line.split(":\t", 1) for line in head.splitlines())
        self.assertEqual(list(rows), [
            "title", "state", "author", "labels", "assignees", "reviewers", "projects", "milestone",
            "number", "url", "additions", "deletions", "auto-merge",
        ])
        self.assertEqual((rows["state"], rows["author"], rows["labels"]), ("OPEN", "mlindqvist", "payments, batch"))
        self.assertEqual((rows["additions"], rows["deletions"]), ("7", "3"))
        self.assertEqual(body, "Batches the nightly run.\nSee #455.\n")
        self.assertIn("author:\tpdavies", self.ok("pr", "view", "482", "--comments"))

    def test_unknown_field_and_unknown_pr(self):
        code, out, err = self.gh("pr", "view", "482", "--json", "title,bogus")
        self.assertEqual((code, out), (1, ""))
        self.assertIn('Unknown JSON field: "bogus"', err)
        self.assertIn("  headRefOid\n", err)
        code, out, err = self.gh("pr", "view", "999", "--json", "title")
        missing = "GraphQL: Could not resolve to a PullRequest with the number of 999.\n"
        self.assertEqual((code, out, err), (1, "", missing))
        code, _, err = self.gh("pr", "diff", "999")
        self.assertEqual((code, err), (1, "GraphQL: Could not resolve to a PullRequest with the number of 999.\n"))

    def test_pr_diff(self):
        expected = git(self.repo, "diff", "--no-ext-diff", "--no-textconv", f"main...{BRANCH}")
        self.assertEqual(self.ok("pr", "diff", "482"), expected)
        self.assertEqual(self.ok("pr", "diff", "482", "--name-only").splitlines(), ["a.py", "b.txt", "c.py", "e.txt"])
        patch = self.ok("pr", "diff", "482", "--patch")
        self.assertTrue(patch.startswith("From "))
        self.assertEqual(patch.count("\nSubject: "), 2)
        self.assertIn("é", self.ok("pr", "diff", "483"))

    def test_pr_checks(self):
        code, out, _ = self.gh("pr", "checks", "482")
        self.assertEqual(code, 8)
        self.assertEqual([line.split("\t")[:2] for line in out.splitlines()], [["unit", "pass"], ["lint", "pending"]])
        self.assertEqual(len(out.splitlines()[0].split("\t")), 4)
        self.assertTrue(out.splitlines()[0].split("\t")[3].startswith("https://"))
        code, out, err = self.gh("pr", "checks", "484")
        self.assertEqual((code, out.split("\t")[1]), (1, "fail"))
        code, out, err = self.gh("pr", "checks", "483")
        self.assertEqual((code, out, err), (1, "", "no checks reported on the 'patch-1' branch\n"))

    def test_pr_list(self):
        rows = self.json("pr", "list", "--json", "number,title,state")
        self.assertEqual([r["number"] for r in rows], [482, 483])
        self.assertEqual([r["number"] for r in self.json("pr", "list", "--json", "number", "--state", "closed")], [484])
        self.assertEqual(len(self.json("pr", "list", "--json", "number", "--state", "all")), 3)
        self.assertEqual(self.ok("pr", "list", "--json", "number", "--jq", ".[].number"), "482\n483\n")
        self.assertTrue(self.ok("pr", "list").startswith("482\tBatch settlement"))

    def test_issue_view(self):
        data = self.json("issue", "view", "455", "--json", "title,author,labels,comments,state,number")
        self.assertEqual(data["title"], "Settlement is slow")
        self.assertEqual(data["author"]["login"], "pdavies")
        self.assertEqual(data["comments"][0]["body"], "on it")
        self.assertEqual(self.ok("issue", "view", "455", "--json", "body", "--jq", ".body"), "Takes hours.\n")
        self.assertIn("title:\tSettlement is slow\n", self.ok("issue", "view", "455"))
        self.assertIn("on it", self.ok("issue", "view", "455", "--comments"))
        code, _, err = self.gh("issue", "view", "9")
        self.assertEqual(code, 1)
        self.assertIn("Could not resolve", err)

    def test_api_paths(self):
        base = "repos/acme-ops/ledger-settle"
        repo = self.json("api", base)
        self.assertEqual(
            (repo["full_name"], repo["default_branch"], repo["fork"]), ("acme-ops/ledger-settle", "main", False)
        )
        pull = self.json("api", f"/{base}/pulls/482")
        self.assertEqual(pull["head"]["sha"], self.sha(BRANCH))
        self.assertEqual(pull["base"]["sha"], self.sha("main"))
        self.assertEqual((pull["head"]["ref"], pull["base"]["ref"]), (BRANCH, "main"))
        self.assertEqual((pull["user"]["login"], pull["author_association"]), ("mlindqvist", "MEMBER"))
        self.assertEqual((pull["title"], pull["state"], pull["draft"]), (
            "Batch settlement runs — fewer round trips", "open", False))
        self.assertEqual(pull["head"]["repo"]["full_name"], "acme-ops/ledger-settle")
        files = self.json("api", f"{base}/pulls/482/files")
        self.assertEqual([f["filename"] for f in files], ["a.py", "b.txt", "c.py", "e.txt"])
        self.assertEqual([f["status"] for f in files], ["modified", "removed", "added", "renamed"])
        self.assertEqual(files[3]["previous_filename"], "d.txt")
        commits = self.json("api", f"{base}/pulls/482/commits")
        shas = git(self.repo, "log", "--reverse", "--format=%H", f"main..{BRANCH}").split()
        self.assertEqual([c["sha"] for c in commits], shas)
        self.assertEqual(commits[0]["commit"]["message"].splitlines()[0], "Batch settle")
        self.assertEqual(self.json("api", f"{base}/pulls/482/reviews")[0]["state"], "CHANGES_REQUESTED")
        self.assertEqual(self.json("api", f"{base}/pulls/482/comments")[0]["path"], "a.py")
        self.assertEqual(self.json("api", f"{base}/issues/455")["user"]["login"], "pdavies")
        self.assertEqual(self.json("api", f"{base}/issues/455/comments")[0]["user"]["login"], "mlindqvist")
        self.assertEqual(self.ok("api", f"{base}/pulls/482", "--jq", ".head.sha"), self.sha(BRANCH) + "\n")
        self.assertEqual(self.ok("api", "-X", "GET", f"{base}/issues/455", "--jq", ".state"), "open\n")

    def test_api_unknown_path(self):
        base = "repos/acme-ops/ledger-settle"
        for path in (f"{base}/releases", "repos/other/repo", "user", f"{base}/pulls/9"):
            code, out, err = self.gh("api", path)
            self.assertEqual((code, out), (1, ""), path)
            self.assertEqual(json.loads(err.splitlines()[0])["message"], "Not Found", path)

    def test_cross_repository_pull(self):
        spec = "isCrossRepository,headRepositoryOwner,headRepository,author,isDraft"
        data = self.json("pr", "view", "483", "--json", spec)
        self.assertIs(data["isCrossRepository"], True)
        self.assertEqual(data["headRepositoryOwner"], {"login": "outsider-fork"})
        self.assertEqual(data["headRepository"]["nameWithOwner"], "outsider-fork/ledger-settle")
        self.assertIs(data["isDraft"], True)
        pull = self.json("api", "repos/acme-ops/ledger-settle/pulls/483")
        self.assertEqual(pull["author_association"], "FIRST_TIME_CONTRIBUTOR")
        self.assertEqual(pull["head"]["repo"]["full_name"], "outsider-fork/ledger-settle")
        self.assertIs(pull["head"]["repo"]["fork"], True)
        self.assertEqual(pull["head"]["sha"], self.sha("fork-patch"))
        self.assertEqual(self.ok("api", "repos/acme-ops/ledger-settle/pulls/483", "--jq", ".author_association"),
                         "FIRST_TIME_CONTRIBUTOR\n")

    def test_output_is_utf8_lf_without_colour(self):
        done = subprocess.run(
            [sys.executable, str(self.bin / "gh-engine.py"), "pr", "view", "482"],
            cwd=self.repo, capture_output=True, timeout=TIMEOUT, env=self.env(), check=True,
        )
        self.assertNotIn(b"\r", done.stdout)
        self.assertNotIn(b"\x1b", done.stdout)
        self.assertIn("—".encode(), done.stdout)

    def test_calls_are_logged(self):
        self.ok("pr", "view", "482", "--json", "title")
        self.gh("pr", "view", "999")
        self.assertEqual(self.read_state("gh-calls.log"), ["pr view 482 --json title", "pr view 999"])
        self.assertEqual(self.read_state("gh-writes.log"), [])
        self.assertFalse((self.state / "gh-write.lock").exists())

    def test_unknown_command(self):
        for args in (["pr", "frobnicate"], ["gist", "list"], ["pr", "view", "482", "--bogus"], []):
            code, out, err = self.gh(*args)
            self.assertEqual((code, out), (1, ""), args)
            self.assertTrue(err.strip(), args)


class WriteCommands(FakeGhCase):
    def snapshot(self):
        return tuple(
            git(self.repo, *args) for args in (("rev-parse", "HEAD"), ("status", "--porcelain"), ("branch", "--list"))
        )

    def test_every_write_is_refused(self):
        before = self.snapshot()
        for args in WRITE_CALLS:
            with self.subTest(args=args):
                shutil.rmtree(self.state, ignore_errors=True)
                code, out, err = self.gh(*args)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, "GraphQL: Resource not accessible by personal access token\n")
                self.assertTrue((self.state / "gh-write.lock").exists())
                self.assertEqual(self.read_state("gh-writes.log"), [" ".join(args)])
                self.assertEqual(self.read_state("gh-calls.log"), [" ".join(args)])
                self.assertEqual(self.snapshot(), before)
        self.assertEqual(git(self.repo, "rev-parse", "--abbrev-ref", "HEAD").strip(), "main")

    def test_reads_do_not_touch_the_lock(self):
        self.ok("api", "-X", "GET", "repos/acme-ops/ledger-settle")
        self.assertFalse((self.state / "gh-write.lock").exists())


class JqSubset(FakeGhCase):
    def test_supported_filters(self):
        base = "repos/acme-ops/ledger-settle"
        cases = {
            (f"{base}/pulls/482", "."): None,
            (f"{base}/pulls/482", ".title"): "Batch settlement runs — fewer round trips\n",
            (f"{base}/pulls/482", ".head.ref"): BRANCH + "\n",
            (f"{base}/pulls/482", ".draft"): "false\n",
            (f"{base}/pulls/482", ".missing"): "null\n",
            (f"{base}/pulls/482/files", ".[0].filename"): "a.py\n",
            (f"{base}/pulls/482/files", ".[].filename"): "a.py\nb.txt\nc.py\ne.txt\n",
            (f"{base}/pulls/482/files", ".[] | .filename"): "a.py\nb.txt\nc.py\ne.txt\n",
            (f"{base}/pulls/482/files", "length"): "4\n",
            (f"{base}/pulls/482/files", ". | length"): "4\n",
            (f"{base}/pulls/482/files", ".[0].additions"): "6\n",
            (f"{base}/pulls/482/files", ".[1:2]"): "UNSUPPORTED",
        }
        for (path, expression), expected in cases.items():
            with self.subTest(expression=expression, path=path):
                code, out, err = self.gh("api", path, "--jq", expression)
                if expected == "UNSUPPORTED":
                    self.assertEqual((code, out, err), (1, "", "jq: error: unsupported filter in this build\n"))
                elif expected is None:
                    self.assertEqual(code, 0)
                    self.assertEqual(json.loads(out)["number"], 482)
                else:
                    self.assertEqual((code, out, err), (0, expected, ""))

    def test_object_stream_and_nested_iteration(self):
        out = self.ok("pr", "view", "482", "--json", "labels,files", "--jq", ".labels[].name")
        self.assertEqual(out, "payments\nbatch\n")
        out = self.ok("pr", "view", "482", "--json", "files", "--jq", ".files | length")
        self.assertEqual(out, "4\n")
        out = self.ok("pr", "view", "482", "--json", "files", "-q", ".files[].path")
        self.assertEqual(out, "a.py\nb.txt\nc.py\ne.txt\n")
        out = self.ok("pr", "view", "482", "--json", "files", "--jq", ".files[]")
        self.assertEqual(json.loads(out.splitlines()[0])["path"], "a.py")

    def test_unsupported_filters(self):
        for expression in ("select(.a)", ".a // 1", ".[] | map(.x)", "{a}", ".a[1:2]", "", ".a |", "keys"):
            with self.subTest(expression=expression):
                code, out, err = self.gh("repo", "view", "--json", "owner", "--jq", expression)
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(err, "jq: error: unsupported filter in this build\n")

    def test_jq_without_json_is_an_error(self):
        code, _, err = self.gh("pr", "view", "482", "--jq", ".title")
        self.assertEqual(code, 1)
        self.assertIn("--jq", err)


@unittest.skipUnless(BASH, "no usable bash (Git's own bash on Windows)")
class Shim(FakeGhCase):
    def test_sh_shim_runs_the_engine(self):
        done = subprocess.run(
            [BASH, _posix(self.bin / "gh"), "pr", "view", "482", "--json", "headRefOid,number", "--jq", ".headRefOid"],
            cwd=self.repo, capture_output=True, timeout=TIMEOUT, env=self.env(), check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr.decode(errors="replace"))
        self.assertEqual(done.stdout.decode().strip(), self.sha(BRANCH))
        self.assertEqual(self.read_state("gh-calls.log"), ["pr view 482 --json headRefOid,number --jq .headRefOid"])


class Sources(unittest.TestCase):
    def test_shapes(self):
        engine = (FAKE / "gh-engine.py").read_bytes()
        self.assertTrue(engine.startswith(b"#!/usr/bin/env python3\n"))
        self.assertIn(b'"${STATE_DIR}"', engine)
        self.assertNotIn(b"\r", engine)
        shim = (FAKE / "gh").read_bytes()
        self.assertTrue(shim.startswith(b"#!/bin/sh\n"))
        self.assertNotIn(b"\r", shim)
        self.assertIn(b'"$@"', shim)


if __name__ == "__main__":
    unittest.main()
