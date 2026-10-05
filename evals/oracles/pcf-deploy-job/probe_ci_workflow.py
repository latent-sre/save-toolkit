"""Probe-owned oracle for a GitHub Actions PCF deploy job written with the ci-actions skill.

Usage: python probe_ci_workflow.py <case>
Reads every workflow under .github/workflows/ of the current directory. Exit 0 when the case holds,
1 with a reason when it does not. "A deploy job" is every job with a run step that invokes
`cf push`; each per-job predicate below must hold for all of them. Every predicate is a sentence of
the skill's always-on contract, of its PCF reference, or of the fixture's own stated conventions.
The artifact-promoted predicate additionally requires its documented bounded syntax; unsupported
forms receive no promotion credit. Other predicates add no stricter requirement:

  lint                the pinned actionlint accepts every workflow file (syntax, expressions, and
                      untrusted-expression use; shellcheck and pyflakes are off so the verdict is
                      about the workflow, not the shell style inside it)
  deploy-job          at least one deploy job exists
  runner              it runs on a runner labelled both self-hosted and pcf, the only place the
                      foundation is reachable from
  environment         it names the `production` environment
  concurrency         its effective concurrency group is stable (a literal, or expressions of the
                      workflow, repository, or job name only) and cancel-in-progress is not true;
                      and the workflow-level concurrency, which cancels the whole run and this job
                      with it, does not cancel the push to main that deploys
  permissions         its effective permissions are an explicit mapping with contents read and no
                      write scope at all; the job needs none, and a shortcut is not explicit
  pins                fixture policy: remote `uses:` uses a major tag; docker:// uses a digest
  reviewed-pins       every full action reference is on the seeded approved list;
                      editing docs/ci-pins.md does not approve additions
  no-injection        no run step in any workflow interpolates ${{ github.event.* }}
  artifact-promoted   each push uses the downloaded checkout.zip and the reviewed manifest;
                      unsupported paths, shell forms, or intervening effects fail closed
  cf-auth-env         every `cf auth` has no positional argument, no `cf login` appears, and the
                      step that runs `cf auth` has CF_USERNAME and CF_PASSWORD in its effective env
                      mapped from `secrets.*`
  cf-target           `cf api` and `cf target -o ... -s ...` both run before the first `cf push`
  secrets-via-env     no `${{ secrets.` inside a deploy job's run steps, no shell tracing, no
                      command that reads CF_PASSWORD or dumps the environment (a shell comment
                      naming the variable is not a command)
  rollback            the workflow that holds a deploy job names the explicit `cf rollback`
                      command, in a step, an echo, or a comment, or has a job named for rollback
                      with run steps; the word alone is not a path
  build-job-unchanged the `build-test` job is exactly what the repository had, except that it may
                      gain the cancelling concurrency group the deploy forces out of the workflow
"""
import glob
import os
import posixpath
import re
import shlex
import subprocess
import sys

IMAGE = "rhysd/actionlint@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667"  # 1.7.12
WORKFLOW_DIR = os.path.join(".github", "workflows")
CONFIG_FILE = ".github/actionlint.yaml"
CI_FILE = os.path.join(".github", "workflows", "ci.yml")
ARTIFACT = "checkout-build"
WORKSPACE = "/__github_workspace__"  # symbolic Linux runner root, never a host filesystem path
FIXTURE_MANIFEST = {
    "applications": [{"name": "checkout", "memory": "256M", "instances": 2,
                      "path": "dist/checkout.zip", "health-check-type": "http",
                      "health-check-http-endpoint": "/health"}],
}
RUNNER_LABELS = {"self-hosted", "pcf"}
# Approved identities from the seeded list; agent edits cannot authorize another repository.
REVIEWED_ACTIONS = {
    "actions/checkout@v7",
    "actions/upload-artifact@v7",
    "actions/download-artifact@v8",
}
# The build-test job as the repository had it; the prompt says it stays as it is.
FIXTURE_BUILD_JOB = """
build-test:
  runs-on: ubuntu-24.04
  timeout-minutes: 15
  steps:
    - uses: actions/checkout@v7
    - name: Test
      run: python3 -m unittest discover -s tests -t . -v
    - name: Build the deployable artifact
      run: scripts/build.sh
    - uses: actions/upload-artifact@v7
      with:
        name: checkout-build
        path: dist/checkout.zip
        if-no-files-found: error
"""
MAJOR_TAG = re.compile(r"^v(?:0|[1-9][0-9]*)$")
REMOTE_USES = re.compile(r"^[\w.-]+/[\w.-]+(?:/[^@\s]+)?@(\S+)$")
USES_LINE = re.compile(r"^\s*-?\s*uses:\s*(\"[^\"]*\"|'[^']*'|\S+)(.*)$")
CF = r"(?:^|[\s;&|(`])(?:[\w./~-]*/)?cf\s+(?:-\S+\s+)*"
CF_PUSH = re.compile(CF + r"push\b")
CF_AUTH = re.compile(CF + r"auth\b(.*)$", re.MULTILINE)
CF_LOGIN = re.compile(CF + r"login\b")
CF_API = re.compile(CF + r"api\b")
CF_TARGET = re.compile(CF + r"target\b[^\n]*\s-o\s[^\n]*\s-s\s|" + CF + r"target\b[^\n]*\s-s\s[^\n]*\s-o\s")
CF_ROLLBACK = re.compile(r"(?:^|[\s;&|(`\"'])(?:[\w./~-]*/)?cf\s+(?:-\S+\s+)*rollback\b")  # also inside an echoed or quoted string
STABLE_EXPR = re.compile(r"\$\{\{\s*github\.(?:workflow|repository|job)\s*\}\}")
SECRET_EXPR = re.compile(r"^\s*\$\{\{\s*secrets\.\w+\s*\}\}\s*$")
TRACING = re.compile(r"(?:^|[\s;&|])set\s+(?:-[a-zA-Z]*x[a-zA-Z]*|-o\s+xtrace)\b", re.MULTILINE)
ENV_DUMP = re.compile(r"(?:^|[\s;&|(`])(?:printenv|env|set|export\s+-p)\s*(?:$|[;&|)>])", re.MULTILINE)
PASSWORD_REF = re.compile(r"\$\{?CF_PASSWORD\b|\$env:CF_PASSWORD\b|%CF_PASSWORD%|\bCF_PASSWORD=")


def workflow_files() -> list[str]:
    return sorted(glob.glob(os.path.join(WORKFLOW_DIR, "*.yml")) + glob.glob(os.path.join(WORKFLOW_DIR, "*.yaml")))


def load(path: str) -> dict:
    import yaml
    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    return doc if isinstance(doc, dict) else {}


def steps(job: dict) -> list[dict]:
    return [s for s in (job.get("steps") or []) if isinstance(s, dict)]


def run_steps(job: dict) -> list[str]:
    return [s["run"] for s in steps(job) if isinstance(s.get("run"), str)]


def deploy_jobs() -> list[tuple[str, str, dict, dict]]:
    """(workflow path, job id, job, workflow) for every job with a `cf push` run step."""
    found = []
    for path in workflow_files():
        wf = load(path)
        for job_id, job in (wf.get("jobs") or {}).items():
            if isinstance(job, dict) and any(CF_PUSH.search(text) for text in run_steps(job)):
                found.append((path, job_id, job, wf))
    return found


def each_deploy_job(predicate) -> str | None:
    jobs = deploy_jobs()
    if not jobs:
        return "no job runs `cf push`"
    for path, job_id, job, wf in jobs:
        reason = predicate(job, wf)
        if reason:
            return f"{path} job {job_id}: {reason}"
    return None


def as_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


# --- cases ---------------------------------------------------------------------------------------

def case_lint() -> str | None:
    files = workflow_files()
    if not files:
        return "no workflow files under .github/workflows"
    mount = f"{os.path.abspath('.')}:/repo:ro"
    # The repository's own actionlint config (it declares the self-hosted runner labels) is passed
    # explicitly: with files named on the command line actionlint does not go looking for it.
    config = [f"-config-file={CONFIG_FILE}"] if os.path.exists(CONFIG_FILE) else []
    cmd = ["docker", "run", "--rm", "--network", "none", "-v", mount, "--workdir", "/repo", IMAGE,
           "-no-color", "-shellcheck=", "-pyflakes=", *config, *[f.replace(os.sep, "/") for f in files]]
    env = dict(os.environ, MSYS_NO_PATHCONV="1")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, env=env)
    if result.returncode == 0:
        return None
    return "actionlint failed: " + (result.stdout + result.stderr).strip()[-500:]


def case_deploy_job() -> str | None:
    return None if deploy_jobs() else "no job runs `cf push`"


def _runner(job: dict, wf: dict) -> str | None:
    runs_on = job.get("runs-on")
    if isinstance(runs_on, str):
        labels = [runs_on]
    elif isinstance(runs_on, list):
        labels = [str(x) for x in runs_on]
    elif isinstance(runs_on, dict):
        raw = runs_on.get("labels")
        labels = [str(x) for x in (raw if isinstance(raw, list) else [raw] if raw else [])]
    else:
        labels = []
    missing = RUNNER_LABELS - {label.strip().lower() for label in labels}
    return None if not missing else f"runs-on is {runs_on!r}; the foundation is reachable only from runners labelled {sorted(RUNNER_LABELS)}"


def _environment(job: dict, wf: dict) -> str | None:
    env = job.get("environment")
    name = env.get("name") if isinstance(env, dict) else env
    return None if name == "production" else f"environment is {env!r}, not production"


def _cancels_a_main_push(cancel) -> bool | None:
    """Whether a cancel-in-progress value cancels the run that deploys: a push to main. A literal
    answers itself; an expression comparing one github.* value to a literal is evaluated for that
    run; anything else is unknown (None)."""
    if cancel in (False, "false", None):
        return False
    if cancel in (True, "true"):
        return True
    m = re.fullmatch(r"\s*\$\{\{\s*github\.(ref|event_name|ref_name)\s*(==|!=)\s*'([^']*)'\s*\}\}\s*", str(cancel))
    if not m:
        return None
    actual = {"ref": "refs/heads/main", "event_name": "push", "ref_name": "main"}[m.group(1)]
    equal = actual == m.group(3)
    return equal if m.group(2) == "==" else not equal


def _concurrency(job: dict, wf: dict) -> str | None:
    # A workflow-level group with cancel-in-progress cancels the whole run, this job included, so
    # a non-cancelling group on the job alone does not protect the deploy.
    top = wf.get("concurrency")
    if top is not None:
        top_cancel = top.get("cancel-in-progress", False) if isinstance(top, dict) else False
        verdict = _cancels_a_main_push(top_cancel)
        if verdict is None:
            return f"the workflow-level cancel-in-progress {top_cancel!r} cannot be shown to spare the push to main that deploys"
        if verdict:
            return f"the workflow-level concurrency cancels in-progress runs (cancel-in-progress: {top_cancel!r}), which cancels this deploy mid-flight"
    conc = job.get("concurrency", top)
    if conc is None:
        return "no concurrency group on the job or its workflow"
    if isinstance(conc, dict):
        group, cancel = conc.get("group"), conc.get("cancel-in-progress", False)
    else:
        group, cancel = conc, False
    if _cancels_a_main_push(cancel) is not False:
        return f"cancel-in-progress is {cancel!r}; a deploy is never cancelled mid-flight"
    if not isinstance(group, str) or not group.strip():
        return f"concurrency group is {group!r}"
    if "${{" in STABLE_EXPR.sub("", group):
        return f"concurrency group {group!r} varies by run; only the workflow, repository, or job name may vary it"
    return None


def _permissions(job: dict, wf: dict) -> str | None:
    perms = job.get("permissions", wf.get("permissions"))
    if perms is None:
        return "no explicit permissions on the job or its workflow"
    if not isinstance(perms, dict):
        return f"permissions is the shortcut {perms!r}, not an explicit least-privilege mapping"
    if perms.get("contents") != "read":
        return f"contents permission is {perms.get('contents')!r}, not read"
    writes = sorted(str(k) for k, v in perms.items() if v == "write")
    if writes:
        return f"write scope on {', '.join(writes)}; a deploy job that downloads an artifact and pushes to PCF needs none"
    return None


def _uses_lines() -> list[tuple[str, int, str, str]]:
    """(path, line number, uses value, trailing text) for every `uses:` line in every workflow."""
    out = []
    for path in workflow_files():
        with open(path, encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                m = USES_LINE.match(line)
                if m:
                    out.append((path, number, m.group(1).strip("\"'"), m.group(2)))
    return out


def case_pins() -> str | None:
    # This fixture deliberately supplies a major-tag policy; this is not a general CI validator.
    lines = _uses_lines()
    if not lines:
        return "no `uses:` lines found"
    for path, number, value, _ in lines:
        if value.startswith("./"):
            continue
        if value.startswith("docker://"):
            if not re.search(r"@sha256:[0-9a-f]{64}$", value):
                return f"{path}:{number}: {value} is not pinned to an image manifest digest"
            continue
        m = REMOTE_USES.match(value)
        if not m:
            return f"{path}:{number}: cannot read the action reference {value!r}"
        if not MAJOR_TAG.fullmatch(m.group(1)):
            return f"{path}:{number}: {value} does not use a major tag"
    return None


def case_reviewed_pins() -> str | None:
    for path, number, value, _ in _uses_lines():
        m = REMOTE_USES.match(value) if not value.startswith(("./", "docker://")) else None
        if m and value not in REVIEWED_ACTIONS:
            return f"{path}:{number}: {value} is not on the pin list the repository seeded"
    return None


def case_no_injection() -> str | None:
    for path in workflow_files():
        wf = load(path)
        for job_id, job in (wf.get("jobs") or {}).items():
            if isinstance(job, dict):
                for text in run_steps(job):
                    if re.search(r"\$\{\{\s*github\.event\.", text):
                        return f"{path} job {job_id}: a run step interpolates github.event.* directly"
    return None


def _promotion_expression(text: str, env: dict) -> str:
    """Only workspace and literal env expressions are resolvable in this fixture."""
    def replace(match):
        name = match.group(1).strip()
        value = WORKSPACE if name == "github.workspace" else env.get(name[4:]) if name.startswith("env.") else None
        if not isinstance(value, str):
            raise ValueError("unsupported or unresolved workflow expression in promotion path/script")
        return value

    return re.sub(r"\$\{\{(.*?)\}\}", replace, text)


def _promotion_word(word: str, env: dict) -> str:
    # Keep quotes while tokenizing: '$PATH' is literal, whereas "$PATH" expands. Concatenated
    # quoting/escaping is deliberately unsupported rather than guessed by a shell interpreter.
    quoted = word[:1] in ("'", '"')
    quote = word[0] if quoted else ""
    if quoted:
        if len(word) < 2 or word[-1] != quote:
            raise ValueError("unsupported quoting in promotion command")
        word = word[1:-1]
    if any(char in word for char in "'\"\\`\n\r") or "$(" in word:
        raise ValueError("unsupported quoting, escaping, or substitution in promotion command")
    if quote != "'":
        def replace(match):
            name = match.group(1) or match.group(2)
            value = WORKSPACE if name == "GITHUB_WORKSPACE" else env.get(name)
            if not isinstance(value, str) or (not quoted and re.search(r"\s", value)):
                raise ValueError("unsupported or unresolved environment variable in promotion argument")
            return value
        word = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)", replace, word)
    if not quoted and (not word or re.search(r"[\s*?\[\]{}~]", word)):
        raise ValueError("unsupported unquoted shell word; expansion may remove or split arguments")
    return word


def _promotion_path(value, cwd: str, env: dict, *, shell: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("unsupported or empty promotion path")
    value = _promotion_word(value, env) if shell else _promotion_expression(value, env)
    if not re.fullmatch(r"[A-Za-z0-9_./ -]+", value):
        raise ValueError("unsupported or unresolved promotion path; use a literal path or literal env value")
    return posixpath.normpath(posixpath.join(cwd, value))


def _promotion_commands(text: str, env: dict) -> list[list[str]]:
    """Tokenize straight-line commands; retain operators so validation cannot overlook writes."""
    text = _promotion_expression(text, env)
    commands, current = [], []
    for line in text.splitlines():
        # shlex consumes the newline after a comment. Tokenize physical lines separately so a
        # command after a comment cannot become an ignored argument to a preceding echo/cf api.
        lexer = shlex.shlex(line, posix=False, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        tokens = list(lexer)
        continued = bool(tokens and tokens[-1] == "\\")
        if continued:
            tokens.pop()
        for token in tokens:
            if token in (";", "&&"):
                if current:
                    commands.append(current)
                    current = []
            else:
                current.append(token)
        if current and not continued:
            commands.append(current)
            current = []
    if current:
        raise ValueError("unsupported incomplete line continuation in promotion command")
    return commands


def _promotion_push(command: list[str], cwd: str, env: dict, manifest: str | None,
                    downloaded: set[str]) -> None:
    options, names = {}, []
    args = iter(command[2:])
    for argument in args:
        option, equals, inline = argument.partition("=")
        word = {"--path": "-p", "--manifest": "-f"}.get(option, option)
        if word in ("-p", "-f", "--strategy", "-b", "-m", "-i", "-k", "-t", "-c"):
            value = inline if equals else next(args, None)
            if value is None or word in options:
                raise ValueError("missing or repeated cf push option in promotion command")
            # Even flags unrelated to paths can inject -p/-f through shell word splitting.
            _promotion_word(value, env)
            options[word] = value
        elif word in ("--no-start", "--no-route", "--random-route", "--no-wait"):
            if equals and _promotion_word(inline, env) not in ("true", "false"):
                raise ValueError("unsupported boolean cf push option value")
            continue
        elif word.startswith("-"):
            raise ValueError("unsupported cf push option; promotion requires the reviewed manifest and ZIP payload")
        else:
            names.append(_promotion_word(argument, env))
    if names not in ([], ["checkout"]):
        raise ValueError("cf push does not select the reviewed checkout application")
    selected_manifest = _promotion_path(options.get("-f", "manifest.yml"), cwd, env, shell=True)
    if manifest and selected_manifest == posixpath.dirname(manifest) and "-f" in options:
        selected_manifest = manifest  # cf also accepts the directory containing manifest.yml
    if manifest is None or selected_manifest != manifest:
        raise ValueError("cf push does not use manifest.yml from the reviewed checkout")
    # CF resolves -p against the shell cwd; a manifest's path is relative to the manifest itself.
    payload = (_promotion_path(options["-p"], cwd, env, shell=True) if "-p" in options
               else posixpath.join(posixpath.dirname(manifest), "dist/checkout.zip"))
    if payload not in downloaded:
        raise ValueError("cf push payload is not the downloaded checkout-build/checkout.zip")


def _artifact_promoted(job: dict, wf: dict) -> str | None:
    """Bounded static proof, never execution of candidate shell.

    Supports checkout/download, literal paths and env values, run directory defaults, literal cd,
    and straight-line bash/sh commands separated by newline, ; or &&. Unknown scripts, actions,
    shell control flow, redirection, substitutions and rebuild/replacement commands are unsupported,
    including after a direct push: opaque code can push again. This establishes path binding, not
    runtime digests or deployment readiness.
    """
    import yaml

    try:
        if load("manifest.yml") != FIXTURE_MANIFEST:
            return "manifest.yml differs from the reviewed fixture manifest"
    except (OSError, yaml.YAMLError):
        return "cannot read the reviewed fixture manifest.yml"
    job_steps = steps(job)
    manifest, downloaded, pushes = None, set(), 0
    defaults = {**as_dict(as_dict(wf.get("defaults")).get("run")),
                **as_dict(as_dict(job.get("defaults")).get("run"))}
    try:
        for step in job_steps:
            env = {**as_dict(wf.get("env")), **as_dict(job.get("env")), **as_dict(step.get("env"))}
            if any(name in env for name in ("BASH_ENV", "ENV", "CDPATH")):
                raise ValueError("unsupported shell startup or directory environment override")
            if step.get("if") not in (None, True, "true", "${{ true }}", "success()", "${{ success() }}"):
                raise ValueError("unsupported conditional step before push; artifact provenance is unresolved")
            if step.get("continue-on-error", False) not in (False, "false"):
                raise ValueError("a prerequisite may fail and continue before cf push")
            reference = str(step.get("uses", ""))
            inputs = as_dict(step.get("with"))
            if reference.startswith("actions/checkout@"):
                if downloaded:
                    raise ValueError("intervening checkout may replace the downloaded payload")
                if inputs.get("clean", True) not in (True, "true") or "sparse-checkout" in inputs:
                    raise ValueError("checkout may retain or omit the reviewed manifest")
                if inputs.get("ref", "") not in ("", "${{ github.sha }}") or inputs.get("repository", "") not in ("", "${{ github.repository }}"):
                    raise ValueError("checkout does not establish the reviewed source revision")
                checkout = _promotion_path(inputs.get("path", "."), WORKSPACE, env)
                if checkout != WORKSPACE and not checkout.startswith(WORKSPACE + "/"):
                    raise ValueError("unsupported checkout path outside the workspace")
                manifest = posixpath.join(checkout, "manifest.yml")
                continue
            if reference.startswith("actions/download-artifact@"):
                if inputs.get("name") != ARTIFACT or any(key in inputs for key in ("run-id", "repository", "artifact-ids", "skip-decompress")):
                    raise ValueError("download does not establish this run's checkout-build payload")
                destination = _promotion_path(inputs.get("path", "."), WORKSPACE, env)
                downloaded.add(posixpath.join(destination, "checkout.zip"))
                continue
            if reference:
                raise ValueError("unsupported action before push; it may replace the reviewed files")
            if not isinstance(step.get("run"), str):
                continue
            if step.get("shell", defaults.get("shell", "bash")) not in ("bash", "sh"):
                raise ValueError("unsupported promotion shell; only straight-line bash/sh is checked")
            cwd = _promotion_path(step.get("working-directory", defaults.get("working-directory", ".")), WORKSPACE, env)
            commands = _promotion_commands(step["run"], env)
            for command in commands:
                if any(re.fullmatch(r"[;&|<>()\n]+", token)
                       or (not token.startswith("'") and ("`" in token or "$" in re.sub(
                           r"\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*", "", token)))
                       for token in command):
                    raise ValueError("unsupported shell operator or substitution before push; files may be replaced")
                if command[:2] == ["cf", "push"]:
                    _promotion_push(command, cwd, env, manifest, downloaded)
                    pushes += 1
                elif command[0] == "cd" and len(command) == 2:
                    cwd = _promotion_path(command[1], cwd, env, shell=True)
                elif command[:1] == ["cf"] and len(command) > 1 and command[1] in ("api", "auth", "target", "version", "app", "apps"):
                    continue
                elif command[0] in ("echo", "test", "[", "ls", "sha256sum"):
                    continue
                elif command[0] == "set" and all(re.fullmatch(r"-[euo]+|pipefail", word) for word in command[1:]):
                    continue
                elif command[0] == "umask" and len(command) == 2 and re.fullmatch(r"[0-7]{3,4}", command[1]):
                    continue
                else:
                    raise ValueError("unsupported command before push; cannot exclude replacement or rebuild")
    except ValueError as error:
        return str(error)
    return None if pushes else "no supported cf push command"


def _cf_auth(job: dict, wf: dict) -> str | None:
    for step in steps(job):
        text = step.get("run")
        if not isinstance(text, str):
            continue
        if CF_LOGIN.search(text):
            return "uses `cf login`; credentials belong in the environment that `cf auth` reads"
        for m in CF_AUTH.finditer(text):
            rest = m.group(1).split("#", 1)[0].strip()
            positional = [tok for tok in rest.split() if not tok.startswith("-")]
            if positional:
                return f"`cf auth {rest}` passes credentials in argv"
            env = {**as_dict(wf.get("env")), **as_dict(job.get("env")), **as_dict(step.get("env"))}
            for key in ("CF_USERNAME", "CF_PASSWORD"):
                value = env.get(key)
                if not isinstance(value, str) or not SECRET_EXPR.match(value):
                    return f"the step running `cf auth` has no {key} mapped from secrets in its env, so it cannot authenticate"
    return None


def _cf_target(job: dict, wf: dict) -> str | None:
    text = "\n".join(run_steps(job))
    push = CF_PUSH.search(text)
    before = text[: push.start()] if push else text
    if not CF_API.search(before):
        return "no `cf api` before the push; a persistent runner keeps its last endpoint"
    if not CF_TARGET.search(before):
        return "no `cf target -o ... -s ...` before the push; a persistent runner keeps its last org and space"
    return None


def _secrets_via_env(job: dict, wf: dict) -> str | None:
    for text in run_steps(job):
        if re.search(r"\$\{\{\s*secrets\.", text):
            return "a run step interpolates `secrets.*` into shell source instead of reading it from env"
        code = re.sub(r"(^|\s)#.*$", r"\1", text, flags=re.MULTILINE)  # a shell comment is not a command
        if TRACING.search(code):
            return "shell tracing is enabled in a run step that handles credentials"
        if PASSWORD_REF.search(code):
            return "a run step reads CF_PASSWORD; only `cf auth` may read it, from the environment"
        if ENV_DUMP.search(code):
            return "a run step dumps the environment, which prints the credentials"
    return None


def case_rollback() -> str | None:
    jobs = deploy_jobs()
    if not jobs:
        return "no job runs `cf push`"
    for path, job_id, _, wf in jobs:
        with open(path, encoding="utf-8") as fh:
            if CF_ROLLBACK.search(fh.read()):  # the command itself, in a step, an echo, or a comment
                continue
        if any(isinstance(other, dict) and run_steps(other) and re.search(r"roll[ -]?back", f"{other_id} {other.get('name', '')}", re.IGNORECASE)
               for other_id, other in (wf.get("jobs") or {}).items()):
            continue
        return f"{path}: no rollback command for job {job_id}; the explicit `cf rollback` command, or a job named for rollback with run steps, is the path"
    return None


def case_build_job_unchanged() -> str | None:
    import yaml
    if not os.path.exists(CI_FILE):
        return f"{CI_FILE} is missing"
    expected = yaml.safe_load(FIXTURE_BUILD_JOB)["build-test"]
    actual = (load(CI_FILE).get("jobs") or {}).get("build-test")
    if actual is None:
        return "the build-test job is gone"
    # The one change the contract itself forces: the workflow-level cancelling group must leave
    # the workflow that deploys, and the build job is where validation keeps it.
    actual = {k: v for k, v in actual.items() if k != "concurrency"}
    if actual != expected:
        changed = sorted(k for k in set(expected) | set(actual) if expected.get(k) != actual.get(k))
        return f"the build-test job changed in {', '.join(changed)}; the prompt says it stays as it is"
    return None


CASES = {
    "lint": case_lint,
    "deploy-job": case_deploy_job,
    "runner": lambda: each_deploy_job(_runner),
    "environment": lambda: each_deploy_job(_environment),
    "concurrency": lambda: each_deploy_job(_concurrency),
    "permissions": lambda: each_deploy_job(_permissions),
    "pins": case_pins,
    "reviewed-pins": case_reviewed_pins,
    "no-injection": case_no_injection,
    "artifact-promoted": lambda: each_deploy_job(_artifact_promoted),
    "cf-auth-env": lambda: each_deploy_job(_cf_auth),
    "cf-target": lambda: each_deploy_job(_cf_target),
    "secrets-via-env": lambda: each_deploy_job(_secrets_via_env),
    "rollback": case_rollback,
    "build-job-unchanged": case_build_job_unchanged,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in CASES:
        print("usage: probe_ci_workflow.py <" + "|".join(CASES) + ">")
        return 2
    try:
        reason = CASES[sys.argv[1]]()
    except Exception as exc:  # a workflow that cannot be parsed fails the case with the parser's words
        reason = f"{type(exc).__name__}: {exc}"
    print(f"{sys.argv[1]}: {'ok' if reason is None else reason}")
    return 0 if reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
