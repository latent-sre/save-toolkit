#!/usr/bin/env python3
"""PreToolUse guard — enforce read-only agents at the command level, by ALLOWLIST.

Wired in THIS repo at plugin scope: `hooks/hooks.json` receives every Bash `PreToolUse` event and
this guard acts only when `agent_type` identifies `sre` or `observability-engineer`. Claude Code silently
ignores hooks embedded in plugin-shipped agent frontmatter, so the session hook is load-bearing.
The guard scopes ITSELF on the payload's agent identity and no-ops for everything else.

Why it cannot simply live on the agent, as it used to: a plugin-shipped agent's `hooks:` frontmatter
is SILENTLY IGNORED ("For security reasons, `hooks`, `mcpServers`, and `permissionMode` are not
supported for plugin-shipped agents" — code.claude.com/docs/en/plugins-reference). Probed on CLI
2.1.200: a plugin agent's frontmatter hook never fired, while a byte-identical hook on a
project-scope agent did. Leaving `hooks:` on a plugin agent would read as armor and provide none, so
validate_fleet.py now rejects that key outright.

Nor can the `tools:` field do this job. A scoped grant like `tools: Bash(git diff:*)` LOOKS like it
narrows Bash, and does nothing: probed on CLI 2.1.200, agents granted `Bash(git diff:*)` and
`Bash(git diff *)` both ran `git status` exactly like an agent granted a bare `Bash`. Scoped
specifiers are real, but only in settings.json permission rules — which are session-wide and would
restrict the USER's Bash too. There is no native per-agent command scoping. This hook is not a
workaround for a better mechanism; it is the only mechanism.

ALLOWLIST, NOT DENYLIST — the load-bearing design decision.

  This guard used to enumerate the state-changing verbs and deny them. That is an unbounded problem
  and it lost: `git clone`, `git submodule update`, `git lfs pull`, `npm ci`, `uv sync`,
  `gh api -f` (which POSTs) and `curl --json` all sailed through, while `rg "gh pr create" docs/` —
  a harmless search whose TEXT contained a verb — was denied. Every new tool ships new ways to
  write, so a denylist is permanently behind, and its failure mode is SILENT: an unlisted writer
  simply runs.

  So it is inverted. We enumerate what a read-only reviewer actually NEEDS — a bounded, knowable
  set — and deny everything else. Failure now means a legitimate read gets blocked: loud, obvious,
  and fixed by adding one entry. That is the right direction to fail in.

  It also means the guard no longer has to out-parse a hostile shell. Anything it cannot confidently
  understand — command substitution, a subshell, an unbalanced quote — is simply not on the list,
  and is denied. Redirection is judged at the token layer using the same posix lexer the guard
  already trusts for segmentation: unquoted redirects are denied except the two shapes that cannot
  touch a real file (`>/dev/null` on any fd, and `2>&1`-style stream duplication), while a `>`
  inside a quoted argument (a Logging filter, a search pattern) is data and never trips anything.
  Every denial names the rule that fired — a guard that can only say "no" trains people to work
  around it; one that says "no, because X, do Y instead" is policy.

NO CODE EXECUTION, DELIBERATELY. There is no `python`, `pytest`, `npm`, or `make` on the allowlist,
and no exemption for any script — not even this repository's own validator. Running a repo's test
suite executes that repo's code under your account; no command filter can make that read-only, and
pretending otherwise is the dishonest part. A reviewer cites the builder's test evidence or CI
instead. This also dissolves, rather than fixes, the old relative-path exemption for
`scripts/validate_fleet.py`, which a repository under review could have supplied itself.

Honest boundary — this is still NOT a sandbox. An allowlisted command with a flag combination we
did not consider may yet do something surprising, and a reviewer that can read files can read
secrets. The LOAD-BEARING control remains OS-level least privilege. What this now guarantees is far
narrower and far more defensible than before: nothing outside a short, reviewed list of readers ever
runs.

SCOPING CONTRACT (probed, not assumed): the stdin payload carries `agent_type` — namespaced for a
plugin agent (`save-toolkit:sre`), bare for a project/user-scope one. THE MAIN LOOP CARRIES
NO `agent_type` KEY AT ALL, which is what makes a session-wide hook safe: the user's own Bash can
never match GUARDED_AGENTS and is never inspected. `agent_type` is UNDOCUMENTED, so if it is ever
renamed upstream the guard would silently stop guarding — see the contract canary in main().

Decision transport: a deny is the permissionDecision JSON on stdout with exit EXIT_DENY (43); an
allow is empty stdout with exit EXIT_ALLOW (42). The distinctive codes are how the hook tells THIS
guard's answer from a stand-in interpreter that merely exits 0 — see the comment at EXIT_ALLOW.
The hook shell string translates them back to the documented exit-0 contract
(https://code.claude.com/docs/en/hooks) before Claude Code sees anything.

Covered by scripts/test_readonly_guard.py (pure-stdlib, runs offline in CI via gate_a.py).
"""
import json
import re
import shlex
import sys

# The namespace Claude Code would prepend if this repo were ever installed as a plugin; guarding
# both forms means the guard cannot be sidestepped by installing the agents a different way.
PLUGIN_NAME = "save-toolkit"
# Agents this guard applies to — the read-only-Bash agents. `sde` is deliberately unguarded (its
# job is running builds and tests for team-authored code); `reviewer` and `researcher` hold no
# Bash at all, which is a stronger control than any hook.
GUARDED_AGENT_NAMES = frozenset({"sre", "observability-engineer"})
GUARDED_AGENTS = frozenset(
    set(GUARDED_AGENT_NAMES) | {f"{PLUGIN_NAME}:{name}" for name in GUARDED_AGENT_NAMES}
)

# Exit codes AUTHENTICATE the guard's answer to the hook — they are not decoration.
#
# The hook must locate a Python at runtime (the plugin has no install step that could pin an
# absolute interpreter, and on Windows the Microsoft Store `python3` stub wins the PATH lookup).
# If the hook simply took "exit 0 + empty stdout" as ALLOW, then ANY binary named `python3` that
# exits 0 — a PATH-planted shim, the Store stub on a bad day — would be accepted as the guard and
# would silently allow every command. So an ALLOW must be positively asserted with a code no
# accidental or hostile stand-in produces; the hook treats anything else as "this was not my guard"
# and moves to the next candidate interpreter, failing closed if none answers correctly.
EXIT_ALLOW = 42
EXIT_DENY = 43
# The third answer, deliberately NOT authoritative: "this input is not something I can vouch for."
# Input the guard cannot parse must never earn EXIT_ALLOW — 42 stops the hook cold, so a truncated
# GUARDED payload would silently be permitted (GOV-001: reproduced — the same guarded push that
# denies intact flipped to allow when the JSON was cut and `except: _allow()` vouched for it).
# Exiting with neither sentinel makes the hook treat this run like a stand-in interpreter's: it
# walks to the next candidate and, finding none that answers 42/43, lands on its blanket deny. So a
# malformed payload denies Bash rather than allowing it. The value only needs to be
# not-42-and-not-43; it is pinned so the tests can tell a deliberate indeterminate from an uncaught
# crash's exit 1. Trade-off, accepted: a malformed payload denies session-wide, not only for
# guarded agents — the same stance the hook already takes when no interpreter answers.
EXIT_INDETERMINATE = 44

# --- shell constructs we refuse to reason about ---------------------------------------------
# An allowlist only means something if the string really is the commands we think it is. Command
# substitution and backgrounding smuggle in a second command past the token inspection below, and
# `$(`/backticks execute even INSIDE double quotes — so for those, mere PRESENCE in the raw string
# is disqualifying, quoted or not. That is not guessing at shell quoting; it is refusing to.
#
# Redirection (`>`, `<`) is different: quotes DO neutralize it, and the same posix `shlex` lexer
# this guard already trusts for command segmentation reports exactly that — an unquoted redirect
# always surfaces as its own pure-punctuation token, while a quoted one stays data inside its
# argument. So redirects are judged at the token layer (see _line_reason): denied by default, with
# two harmless shapes permitted because they cannot touch a real file — `>/dev/null` (any fd) and
# stream duplication `2>&1`/`>&2`. This resolves the old quoted-filter false positive
# (`gcloud logging read "severity>=ERROR"`) without weakening the substitution rules above.
#
# `${NAME}` (a plain identifier in braces) is byte-for-byte equivalent to `$NAME` and is normalized
# to it before this scan; every other `${...}` form (defaults, slicing, indirection) stays denied —
# not because each is dangerous, but because vouching for them means parsing them.
_STRUCTURE_DENY = re.compile(
    r"\$\(|`|\$\{"           # command substitution, non-trivial ${...} (post-normalization)
    r"|(?<![&>])&(?!&)"      # a lone & (background); && separates, >& is judged at token level
)
# The one `${...}` shape we vouch for: braces around a bare identifier, rewritten to `$NAME` before
# any other inspection so the structure scan and tokenizer see the equivalent simple form.
_SIMPLE_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
# Operator tokens that separate one command from the next. Every resulting segment must stand on its
# own as an allowed read — `git log; rm -rf /` gets no free pass from its harmless first half.
_SEPARATORS = {"|", "||", "&&", ";", "\n"}
# Any run of separator punctuation counts, not just the four spellings above. `shlex` with
# punctuation_chars emits `;;` and `&&&` as SINGLE tokens, and neither was in _SEPARATORS — so
# `git log ;; git push` collapsed into one segment whose command was the allowed reader and whose
# `git push` became an inert trailing argument. Both spellings are shell syntax errors, so nothing
# ever executed, but a fail-open inside a fail-closed control is not something to leave sitting.
_SEPARATOR_CHARS = frozenset(";|&")
# The characters shlex(punctuation_chars=True) emits as operator tokens. A token made ONLY of these
# is an unquoted shell operator; a token that merely contains one arrived quoted and is data.
_PUNCTUATION = frozenset("();<>|&")
# `timeout <duration> <allowed command>` bounds a stream (the allowlist permits `cf logs` and
# `tail -f`, which otherwise never return). Only the flagless form is vouched for: `-k`/`-s` take
# separate values that would misalign the wrapped-command check, so they fail closed.
_TIMEOUT_DURATION = re.compile(r"^\d+(\.\d+)?[smhd]?$")
# `date` earns its slot because the packet convention demands UTC timestamps and the timeline is
# incident work's core artifact — but it is gated by ALLOWLIST, not by denying `--set`/`-s`.
# `date(1)` has a SECOND synopsis form, `date [-u] [MMDDhhmm[[CC]YY][.ss]]`, in which a bare numeric
# OPERAND (no flag at all) sets the system clock: `date 081319002026` is a write. Gating only the
# set FLAGS let that through — the exact silent-writer failure this file's allowlist doctrine
# exists to prevent, reintroduced by treating one command as "obviously a reader". So: a format
# string (`+...`) and known display flags are permitted, and anything else — a bare operand, an
# unrecognized flag — denies.
_DATE_DISPLAY_BARE = frozenset({
    "-u", "--utc", "--universal", "-R", "--rfc-email", "--debug", "--resolution",
})
# Flags whose value may arrive attached (`--date=yesterday`) or as the next token (`-d yesterday`);
# the value is consumed so it is never mistaken for a clock-setting operand.
_DATE_DISPLAY_WITH_VALUE = frozenset({
    "-d", "--date", "-r", "--reference", "-f", "--file", "--rfc-3339",
})
# `-I`/`--iso-8601` take an OPTIONAL timespec, which getopt only accepts ATTACHED (`-Iseconds`,
# `--iso-8601=seconds`) — never as a separate token, so no value is consumed for these.
_DATE_ISO_PREFIX = "-I"
_DATE_ISO_LONG = "--iso-8601"
_DEV_NULL = "/dev/null"


def _strip_harmless_redirects(tokens: list[str]) -> list[str]:
    """Drop redirect forms that cannot write anywhere real, before the operator scan.

    `>/dev/null` and `>>/dev/null` discard output (any fd — a preceding lone-digit token like the
    `2` of `2>/dev/null` survives as an inert argument, a divergence from shell semantics that can
    only ever ADD a harmless positional to a read). `>&` followed by a bare stream number
    duplicates one stream onto another and touches no file. Every other redirect token survives to
    be denied by _line_reason.
    """
    stripped: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        nxt = tokens[index + 1] if index + 1 < len(tokens) else None
        if token in {">", ">>"} and nxt == _DEV_NULL:
            index += 2
            continue
        if token == ">&" and nxt in {"1", "2"}:
            index += 2
            continue
        stripped.append(token)
        index += 1
    return stripped

# --- the allowlist --------------------------------------------------------------------------
# Plain readers and filters: they consume input and print. None can write a file on its own (a
# redirect would be needed, and redirects are refused above) — with one flag-gated exception:
# `file -C`/`--compile` writes a compiled `.mgc` magic file, so _segment_allowed rejects that flag
# (see _FILE_WRITE_FLAGS). `sed` and `awk` are deliberately ABSENT
# — both can write files without any redirect (`sed -i`, awk's `print > "f"` and `system()`).
# `tree` and `less` are absent: `tree -o` writes to a named file, and `less -o` logs its input to a
# file (and `less` can also execute a program interactively). `sort` is absent too: GNU sort can run
# an arbitrary helper through `--compress-program`, accepts caller-selected spill locations through
# `-T`/`--temporary-directory`, and may write spill files even without either flag. A complete safe
# flag gate would have to predict runtime spilling, so the command fails closed instead.
_SIMPLE_READERS = frozenset({
    "cat", "head", "tail", "nl", "wc", "uniq", "cut", "tr", "column",
    "grep", "egrep", "fgrep", "rg",
    "ls", "file", "stat", "du", "basename", "dirname", "realpath", "pwd",
    "echo", "diff", "cmp", "jq", "true", "false",
    # `dig` is on the list for incident triage (is DNS the problem?). It IS an egress channel —
    # a crafted name can tunnel data — which is why `dig $(...)` dies on structure and why the
    # outbound network allowlist remains the load-bearing egress control, not this guard.
    "dig",
})
# `ag` (the silver searcher) was here and is deliberately GONE: it documents `--pager COMMAND`, the
# same execute-a-program lever gated on `rg` below, and it is redundant — `rg` and `grep` both cover
# search. Per this file's own rule the allowlist carries what a reviewer NEEDS; an un-enumerable
# tool nothing needs is the easiest to leave off. Restoring it means an `_RG_EXECUTION_FLAGS`-style
# gate verified against the installed binary, not just putting the name back.
# ripgrep flags that run an external program (or a PATH-resolved helper) mid-search, turning a
# reader into code execution. `--pre COMMAND` runs COMMAND on every file; `--hostname-bin COMMAND`
# runs COMMAND to resolve the hostname for hyperlinks (rg 14+); `--search-zip`/`-z` shells out to
# decompressors found on PATH, which a planted `gzip` subverts. `rg` is useful enough for review to
# retain with this gate — enumerate EVERY exec-capable flag, since one unlisted flag reopens the
# hole (proven: `--hostname-bin=/bin/sh` executed before this list grew past `--pre`).
_RG_EXECUTION_FLAGS = frozenset({"--pre", "--hostname-bin", "--search-zip", "-z"})
# `-z` (--search-zip) is a bundling short flag: `rg -iz` = `-i` + `-z`, so match the letter in a
# cluster, not just the standalone token. See _short_cluster_has.
_RG_EXECUTION_SHORT = frozenset({"z"})

# `file` is a reader with ONE write lever: `-C`/`--compile` compiles a magic source file into a
# `.mgc` file on disk — no shell redirect involved, so _STRUCTURE_DENY never sees it (the
# `tree -o` shape again). The short form bundles (`-bC` = `-b` + `-C`), so the letter is matched
# in a cluster too. See _short_cluster_has.
_FILE_WRITE_FLAGS = frozenset({"--compile"})
_FILE_WRITE_SHORT = frozenset({"C"})

# `git` subcommands that have no write SUBCOMMAND (per `git-<name>(1)` synopsis). Several still
# accept `--output=<file>`/`-o <file>` to write a report to disk (diff, log, show, diff-tree,
# whatchanged) — those flag forms are rejected below in _git_allowed, since being on this list is
# not a licence to write files.
_GIT_READ = frozenset({
    "diff", "log", "show", "blame", "status", "shortlog", "describe", "rev-parse", "rev-list",
    "ls-files", "ls-tree", "cat-file", "show-ref", "grep", "whatchanged", "diff-tree",
    "merge-base", "name-rev", "version", "check-ignore",
})
# `check-ignore` earns its slot the way every reader must: a review NEED (proving a secret/key path
# is actually gitignored, negation rules included — reconstructing that from .gitignore by hand is
# where a reviewer silently gets it wrong) and a clean surface (per git-check-ignore(1) it prints
# ignore status and the matching rule, with no exec-capable or output-redirect flag).
# `help` was on this list and is deliberately GONE: `git help -w/--web` hands off to
# `git web--browse`, which runs the command named by `web.browser`/`browser.<tool>.cmd` config, and
# `-i` shells out to an info reader. Removing the SUBCOMMAND closes every viewer spelling at once,
# where denying the flags would leave the next one to be discovered. Reviewing a diff never needs
# git's own manual.
# Flags on _GIT_READ subcommands that redirect output into a file. `--output=<file>` and its
# separate-argument form `-o <file>` are accepted by diff/log/show/diff-tree/whatchanged (they
# share the diff plumbing) and write to the named path with no shell redirect involved, so
# _STRUCTURE_DENY never sees them. Any occurrence is disqualifying.
_GIT_READ_WRITE_FLAGS = frozenset({"-o", "--output"})
# Flags on _GIT_READ subcommands that EXECUTE a program — the git twin of `rg --pre`. `git grep`
# opens matching files in a pager named by `--open-files-in-pager[=CMD]` or its attached short form
# `-O<CMD>`, and runs CMD even with no TTY (proven: `git grep -O/bin/sh` executed the pager). The
# `-O` short form can't be caught by the `split("=")` membership test the write-flags use, so
# _git_allowed rejects any `-O`-prefixed arg explicitly. That also denies the benign
# `git diff -O<orderfile>` — a false positive we accept, per this guard's fail-loud-not-silent rule.
_GIT_READ_EXEC_FLAGS = frozenset({"--open-files-in-pager"})
# The SHORT form of the pager-exec flag: `git grep -O<cmd>` runs CMD, and it bundles
# (`-nO<cmd>` = `-n` + `-O<cmd>`), so a start-of-token test alone misses it. See _short_cluster_has.
_GIT_READ_EXEC_SHORT = frozenset({"O"})
# Honest residual on the git readers, in the docstring's "not a sandbox" class: `git diff`, `log`,
# and `show` run diff DRIVERS and textconv filters named by an existing `.git/config` +
# `.gitattributes` BY DEFAULT — no flag involved, so no flag gate here can see it. The guard denies
# the injection paths it does see (`-c key=val` config and `VAR=x` env prefixes are both rejected
# below), but a config already on disk is outside a command filter's sight. OS-level least
# privilege remains the load-bearing control, per the boundary note at the top of this file.
# Subcommands whose FIRST POSITIONAL decides read vs write (`git stash list` reads, a bare
# `git stash` pushes; `git submodule status` reads, `git submodule update` writes;
# `git reflog show` reads, `git reflog expire` prunes reflog entries).
_GIT_READ_VERBS = {
    "stash": frozenset({"list", "show"}),
    "worktree": frozenset({"list"}),
    "notes": frozenset({"list", "show"}),
    "submodule": frozenset({"status"}),
    "remote": frozenset({"show", "get-url"}),
    # `git reflog` with no subcommand defaults to `show`, but `expire`, `delete`, `drop`, and
    # `write` all mutate the reflog. Gate on an EXPLICIT read verb; a bare `git reflog` is denied
    # rather than defaulted, since the "no positional" shape here is indistinguishable from a
    # typo of a write verb and the safe direction is loud.
    "reflog": frozenset({"show", "list", "exists"}),
}
# Subcommands that list when read-flagged and CREATE when handed a bare name (`git branch feature`,
# `git tag v1.0`). The flag sets differ per subcommand on purpose: `-a` means --all for branch
# (read) but --annotate for tag (WRITE); `-v` means --verbose for branch (a modifier that does NOT
# stop a create) but --verify for tag (which does).
#
# LIST_MODE, not "read" — the load-bearing distinction, and the one this gate got wrong.
#
#   The old shape allowed a positional whenever ANY read flag was present, on the theory that "a
#   read flag makes the intent explicit". That premise is false, and git does not care what we
#   think the intent was. Probed on git 2.43.0, each of these CREATED a real ref while the guard
#   returned allow: `git tag --sort=refname vX1`, `git tag --format=%(refname) vX2`,
#   `git tag -i vX3`, `git branch --sort=refname bX1`, `git branch -i bX2`, `git branch -v bX3`.
#
#   The flags that are actually safe are the ones that force git into LIST (or VERIFY) mode, which
#   makes every positional a pattern or a commit-ish rather than a new ref name. Pure modifiers —
#   `--sort`, `--format`, `-i`/`--ignore-case`, and branch's `-v`/`--verbose` — change only the
#   output and leave the positional free to name a ref. `--sort=x`/`--format=x` are especially
#   deceptive: the attached `=value` means the flag never consumes the following word.
#
#   So only LIST_MODE members authorize a positional. Anything else — a pure modifier, or a git
#   flag released after this was written — falls through to the no-positional rule and denies.
#   That is what keeps the next new modifier from silently reopening the hole.
_GIT_LIST_LIKE = {
    "branch": {
        "list_mode": frozenset({
            "-a", "-r", "--all", "--remotes", "--list", "--contains", "--no-contains",
            "--merged", "--no-merged", "--show-current", "--points-at",
        }),
        "write": frozenset({
            "-d", "-D", "-m", "-M", "-c", "-C", "-f", "--delete", "--move", "--copy", "--force",
            "--set-upstream-to", "-u", "--unset-upstream", "--track", "-t", "--no-track",
            "--edit-description",
        }),
    },
    "tag": {
        "list_mode": frozenset({
            "-l", "--list", "-n", "--contains", "--no-contains", "--points-at",
            "--merged", "--no-merged", "-v", "--verify",
        }),
        "write": frozenset({
            "-a", "--annotate", "-s", "--sign", "-d", "--delete", "-f", "--force", "-m", "-F",
            "-u", "--local-user", "--create-reflog",
        }),
    },
}
# `git config` writes whenever it is not explicitly reading, so require a read flag.
_GIT_CONFIG_READ = frozenset({
    "--get", "--get-all", "--get-regexp", "--get-urlmatch", "--list", "-l",
})
# git's own global options, permitted between `git` and the subcommand. `-c key=val` is NOT here:
# it injects config into the command's execution, which is a lever we have no need to hand over.
_GIT_GLOBAL_WITH_VALUE = frozenset({"-C", "--git-dir", "--work-tree"})
_GIT_GLOBAL_BARE = frozenset({"--no-pager", "-P", "--no-replace-objects", "--literal-pathspecs"})

# `gh` read-only subcommand pairs. `gh api` is absent by design: it silently switches to POST when
# given `-f`/`-F` fields, so "read-only gh api" is a shape too easy to get wrong.
# `gh <group> <verb> --web/-w` opens the resource in $BROWSER — launching an application, not a
# read — so the flag disqualifies any otherwise-allowed pair.
_GH_EXECUTION_FLAGS = frozenset({"--web", "-w"})
# `-w` (--web) bundles too (`gh pr view -cw`), so match the letter in a cluster. See
# _short_cluster_has.
_GH_EXECUTION_SHORT = frozenset({"w"})
_GH_READ = {
    "pr": frozenset({"view", "diff", "list", "checks", "status"}),
    "issue": frozenset({"view", "list", "status"}),
    "repo": frozenset({"view"}),
    "run": frozenset({"view", "list"}),
    "release": frozenset({"view", "list"}),
    "search": frozenset({"prs", "issues", "repos", "commits", "code"}),
}

# `find`'s action flags run commands or delete files — the reason `find` cannot simply be a reader.
_FIND_ACTIONS = ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls")

# `cf` (Cloud Foundry CLI v8) read verbs for incident triage. `target` is bare-form-only — its
# flag form WRITES the target; see _cf_allowed. `cf env` is ABSENT by design: it
# prints the app's full environment — credentials included — to an agent that also holds web
# egress, and that pairing is exactly the exfiltration shape the fleet's doctrine forbids.
_CF_READ = frozenset({
    "app", "apps", "events", "logs", "routes", "services", "spaces", "orgs", "target",
})

# `gcloud` read-only triage for the GCP migration — the `cf` analog, gated by POSITIONAL PREFIX
# because gcloud nests groups two or three levels deep (`run services list`). Same philosophy as
# every list here: enumerate the reads triage NEEDS, deny the rest. `gcloud auth
# print-access-token` / `print-identity-token` / `application-default print-access-token` and
# `gcloud secrets versions access` print live credentials or secret payloads to an agent that also
# holds egress — the `cf env` shape again — and are not on the list, like every unlisted path.
# `config list` / `config get-value` are the `cf target` analog: they print the active project,
# region, and account NAME, not credentials. Release-track prefixes (`gcloud beta …`) shift the
# positional path and deny — fail-loud, add the exact tracked path if a read genuinely needs it.
# A flag value passed as a separate token (`--limit 50`) lands AFTER the matched prefix and is
# inert. A flag BEFORE the command path is denied outright in _gcloud_allowed: the space-separated
# form (`--project foo logging read`) would shift the prefix anyway, but the attached form
# (`--project=foo logging read`) would not — _positionals() skips it — so leading-flag inputs were
# silently prefix-matched until the explicit first-arg check closed the pair. Write the flags
# after the command path (`gcloud logging read … --project=foo`), gcloud's own documented style.
_GCLOUD_READ_PREFIXES = (
    ("run", "services", "list"), ("run", "services", "describe"),
    ("run", "services", "logs", "read"),
    ("run", "revisions", "list"), ("run", "revisions", "describe"),
    ("logging", "read"), ("logging", "logs", "list"),
    ("projects", "describe"),
    ("config", "list"), ("config", "get-value"),
)
# Flags that make even an allowed gcloud read something we refuse to vouch for:
# `--impersonate-service-account` performs the read AS another identity (an access-path lever, not
# a read), and `--flags-file` loads more flags from a file the guard never sees — the same
# smuggling shape as command substitution, so its mere presence is disqualifying.
_GCLOUD_DENY_FLAGS = frozenset({"--impersonate-service-account", "--flags-file"})

# Commands only observability-engineer may run — it validates observability config; sre does not
# need these, and the smaller each profile is, the better it fails.
_OBS_ONLY = frozenset({"yamllint"})
# `promtool` is verb-gated like git: only its `check` family reads (observability-only as well).
_PROMTOOL_READ_VERB = "check"

# The generic tail appended to every denial. The SPECIFIC rule that fired is stated first by
# explain(); a denial that cannot say why it fired trains the agent (and the human reading the
# transcript) to treat the guard as weather instead of policy.
_GUIDANCE = (
    "This read-only agent's Bash is limited to an allowlist of read-only commands (git/gh/cf/gcloud "
    "reads plus grep/rg/cat/ls-style filters; `timeout <n> <cmd>`, `date`, `>/dev/null`, and "
    "`2>&1` are permitted shapes). It may not execute code or apply changes — cite the builder's or "
    "CI's evidence and report what needs changing as a finding. A denied command you believe is a "
    "legitimate read is a loud, one-line allowlist fix by PR — never work around the guard."
)
# Interpreters and build/package entry points get a first-class explanation: this is the denial an
# agent is most tempted to argue with, and the reason is doctrine, not an allowlist gap.
_CODE_RUNNERS = frozenset({
    "python", "python3", "py", "node", "deno", "bash", "sh", "zsh", "dash", "pwsh", "powershell",
    "perl", "ruby", "npx", "npm", "yarn", "pnpm", "make", "cargo", "go", "pytest", "tox", "uv",
    "pip", "pip3", "poetry", "docker", "podman", "source", ".",
})


def _allow() -> None:
    """Positively assert ALLOW (no stdout, distinctive exit code) and stop."""
    sys.exit(EXIT_ALLOW)


def _deny(reason: str) -> None:
    """Emit the deny decision on stdout and assert DENY via the exit code."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(EXIT_DENY)


def _split_segments(tokens: list[str]) -> list[list[str]]:
    """Split a token stream on shell operators into individual commands."""
    segments: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if token in _SEPARATORS or (token and all(ch in _SEPARATOR_CHARS for ch in token)):
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    return [segment for segment in segments if segment]


def _positionals(args: list[str]) -> list[str]:
    return [arg for arg in args if not arg.startswith("-")]


def _short_cluster_has(token: str, letters: frozenset[str]) -> bool:
    """True if a single-dash short-option token bundles any of `letters`.

    Bundled short options are how an exec flag hides behind a benign one: `git grep -nO<cmd>` is
    `-n` + `-O<cmd>`, and `rg -iz` is `-i` + `-z` (--search-zip) — both defeated a naive
    `token in FLAGSET` membership test. We scan the whole cluster (up to any `=`) and treat any
    occurrence of a dangerous letter as present. That OVER-denies the rare case where the letter is
    actually another flag's attached value (`rg -ez` = search for 'z'), which is exactly this
    guard's accepted fail-loud direction: a blocked legitimate read is a one-line allowlist fix, an
    allowed exec is a breach. `--long` options are not clusters and return False here (their exec
    forms are matched by name in the callers).
    """
    if not token.startswith("-") or token.startswith("--"):
        return False
    return any(ch in letters for ch in token[1:].split("=", 1)[0])


def _carries_flag(args: list[str], long_flags: frozenset[str], short_letters: frozenset[str]) -> bool:
    """True if any arg is one of `long_flags` (by name, `=`-value tolerant) or bundles a short letter.

    The one detection mechanism behind every per-command flag gate (git/gh/rg): the auditable
    POLICY stays in each command's named frozensets, only the error-prone matching mechanics live
    here once. Threading the cluster-aware form into every call site by hand is how the bundled-flag
    bypass slipped in; with one predicate that class of fix lands in a single place.
    """
    return any(
        arg.split("=", 1)[0] in long_flags or _short_cluster_has(arg, short_letters)
        for arg in args
    )


def _git_flag_names(args: list[str]) -> set[str]:
    """Normalize flag tokens for membership testing, expanding single-dash clusters.

    Two spellings defeat a plain `token in FLAGSET` test, and both appear in real git usage:
    `--sort=refname` carries its value inline (compare the name only), and `git branch -av` bundles
    `-a` with `-v` in one token. Expanding the cluster letter by letter is what lets `-av` count as
    list-mode via `-a` while a lone `-v` does not. A cluster letter that is really another flag's
    attached value (`git tag -n5` yields a spurious `-5`) is harmless: it simply matches nothing.
    """
    names: set[str] = set()
    for arg in args:
        if not arg.startswith("-"):
            continue
        base = arg.split("=", 1)[0]
        if arg.startswith("--"):
            names.add(base)
        else:
            names.update(f"-{char}" for char in base[1:])
    return names


def _date_reason(args: list[str]) -> "str | None":
    """None if this `date` invocation only displays; otherwise why it is refused.

    Short-flag CLUSTERS (`date -uR`) are denied rather than decomposed: a cluster would have to be
    split to prove no set-flag hides in it, and the spelled-out `date -u -R` is one keystroke away.
    Fail-loud over-denial is this guard's accepted direction.
    """
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("+"):  # a strftime format string: display only
            index += 1
            continue
        if not arg.startswith("-") or arg == "-":
            return (
                f"`date {arg}` is the clock-SETTING operand form (`MMDDhhmm[[CC]YY][.ss]`) — it "
                "writes the system time; display with `date -u`, `date -u +FORMAT`, or "
                "`date -d <when> +FORMAT`"
            )
        base = arg.split("=", 1)[0]
        if base in _DATE_DISPLAY_BARE:
            index += 1
        elif base in _DATE_DISPLAY_WITH_VALUE:
            index += 1 if "=" in arg else 2
        elif arg.startswith(_DATE_ISO_PREFIX) or base == _DATE_ISO_LONG:
            index += 1
        else:
            return (
                f"`date {arg}` is not a known display flag — `--set`/`-s` write the system clock, "
                "and unrecognized flags are denied rather than guessed at"
            )
    return None


def _git_allowed(args: list[str]) -> bool:
    # Step over git's global options to find the subcommand.
    index = 0
    while index < len(args) and args[index].startswith("-"):
        option = args[index]
        base = option.split("=", 1)[0]
        if base in _GIT_GLOBAL_WITH_VALUE:
            index += 1 if "=" in option else 2
        elif option in _GIT_GLOBAL_BARE:
            index += 1
        else:
            return False  # includes `-c key=val`
    if index >= len(args):
        return False
    subcommand, rest = args[index], args[index + 1:]

    if subcommand in _GIT_READ:
        # Even a read subcommand can escape read-only WITHOUT a shell redirect: `--output=<file>` /
        # `-o <file>` writes a report to disk, and `git grep --open-files-in-pager[=CMD]` / `-O<CMD>`
        # (bundled `-nO<CMD>`) executes CMD. Reject every spelling in one check.
        return not _carries_flag(
            rest, _GIT_READ_WRITE_FLAGS | _GIT_READ_EXEC_FLAGS, _GIT_READ_EXEC_SHORT
        )

    if subcommand in _GIT_READ_VERBS:
        verbs = _positionals(rest)
        return bool(verbs) and verbs[0] in _GIT_READ_VERBS[subcommand]

    if subcommand == "config":
        return any(arg.split("=", 1)[0] in _GIT_CONFIG_READ for arg in rest)

    if subcommand in _GIT_LIST_LIKE:
        flags = _GIT_LIST_LIKE[subcommand]
        present = _git_flag_names(rest)
        if present & flags["write"]:
            return False
        # A positional is a CREATE unless a list-mode flag reframes it as a pattern. Note the
        # direction: we require a known-safe flag to permit the positional, rather than trying to
        # enumerate the modifiers that are unsafe — an unknown flag therefore denies.
        if _positionals(rest) and not (present & flags["list_mode"]):
            return False
        return True

    return False


def _gh_allowed(args: list[str]) -> bool:
    # `--web`/`-w` (bundled `-cw`) launches $BROWSER — an app, not a read.
    if _carries_flag(args, _GH_EXECUTION_FLAGS, _GH_EXECUTION_SHORT):
        return False
    positionals = _positionals(args)
    if len(positionals) < 2:
        return False
    group, verb = positionals[0], positionals[1]
    return verb in _GH_READ.get(group, frozenset())


def _rg_allowed(args: list[str]) -> bool:
    # `rg` reads unless a flag runs an external program mid-search: a named exec flag
    # (`--pre`, `--search-zip`, `-z`) or `-z` bundled into a short cluster (`-iz`).
    return not _carries_flag(args, _RG_EXECUTION_FLAGS, _RG_EXECUTION_SHORT)


def _cf_allowed(args: list[str]) -> bool:
    positionals = _positionals(args)
    if not positionals or positionals[0] not in _CF_READ:
        return False
    # `target` is the one _CF_READ verb with a WRITE form: bare `cf target` prints the current
    # org/space, but `-o`/`-s` SET it — local CLI state that silently points every later guarded
    # `cf` read at a different target. Allow only the bare, print-only form; any extra argument
    # (flag or positional) denies, this guard's usual fail-loud direction.
    if positionals[0] == "target":
        return args == ["target"]
    return True


def _gcloud_allowed(args: list[str]) -> bool:
    # A leading flag is denied before any prefix matching: `--project=foo logging read` would
    # otherwise prefix-match because _positionals() skips the attached-value flag entirely. See
    # the comment at _GCLOUD_READ_PREFIXES.
    if not args or args[0].startswith("-"):
        return False
    if _carries_flag(args, _GCLOUD_DENY_FLAGS, frozenset()):
        return False
    positionals = tuple(_positionals(args))
    return any(
        positionals[: len(prefix)] == prefix for prefix in _GCLOUD_READ_PREFIXES
    )


def _segment_reason(segment: list[str], agent: str) -> "str | None":
    """None if this segment is an allowed read; otherwise the specific rule that denies it.

    The reasons name the rule so the agent's next move is obvious: rephrase into an allowed shape,
    hand the command to a human, or propose the one-line allowlist PR. The policy itself is
    unchanged from the boolean helpers this wraps — only the answer got articulate.
    """
    command, args = segment[0], segment[1:]
    # A path to a binary (`/bin/cat`, `./deploy.sh`, `scripts/setup.sh`) is never allowed: the
    # allowlist names commands, and a path is how you smuggle a different one in.
    if "/" in command or "\\" in command or "=" in command:
        return (
            f"`{command}` is a path or assignment in command position — the allowlist names bare "
            "commands only, because a path is how a different binary gets smuggled in"
        )
    if command == "timeout":
        if not args or args[0].startswith("-") or not _TIMEOUT_DURATION.match(args[0]):
            return (
                "`timeout` is allowed only in the flagless form `timeout <duration> <allowed "
                "command>` (e.g. `timeout 30 cf logs my-app`)"
            )
        if len(args) < 2:
            return "`timeout` needs a command to bound: `timeout <duration> <allowed command>`"
        return _segment_reason(args[1:], agent)
    if command == "date":
        return _date_reason(args)
    if command == "git":
        if _git_allowed(args):
            return None
        return (
            "this `git` form is not an allowed read: only read subcommands (log, diff, show, "
            "status, blame, …) without write verbs or output/pager-exec flags (`-o`, `--output`, "
            "`-O`, `--open-files-in-pager`) are permitted"
        )
    if command == "gh":
        if _gh_allowed(args):
            return None
        if args and _positionals(args)[:1] == ["api"]:
            return (
                "`gh api` silently switches to POST with `-f`/`-F` fields, so no shape of it is "
                "on the read-only list — hand the exact call to a human or evidence job"
            )
        return (
            "this `gh` form is not an allowed read: only view/list/diff/checks/status pairs "
            "without `--web`/`-w` are permitted"
        )
    if command == "rg":
        if _rg_allowed(args):
            return None
        return (
            "this `rg` form carries an exec-capable flag (`--pre`, `--hostname-bin`, "
            "`-z`/`--search-zip`) that runs a program mid-search — drop the flag"
        )
    if command == "file":
        if not _carries_flag(args, _FILE_WRITE_FLAGS, _FILE_WRITE_SHORT):
            return None
        return (
            "this `file` form carries `-C`/`--compile`, which writes a compiled magic file — "
            "drop the compile flag for a read-only inspection"
        )
    if command == "cf":
        if _cf_allowed(args):
            return None
        first = _positionals(args)[:1]
        if first in (["env"], ["ssh"]):
            return (
                f"`cf {first[0]}` exposes credentials or a live shell to an agent that also holds "
                "egress — a human runs it and pastes the sanitized excerpt"
            )
        return (
            "this `cf` form is not an allowed read: only app, apps, events, logs, routes, "
            "services, spaces, orgs, and target are permitted — mitigation commands are "
            "recommended to a human, never run"
        )
    if command == "gcloud":
        if _gcloud_allowed(args):
            return None
        return (
            "this `gcloud` form is not on the read allowlist (run services/revisions "
            "list/describe/logs, logging read, projects describe, config list/get-value — flags "
            "after the command path, no `--impersonate-service-account`/`--flags-file`); "
            "credential-printing and secret-access paths are denied by doctrine, not oversight"
        )
    if command == "promtool":
        positionals = _positionals(args)
        if (
            agent == "observability-engineer"
            and bool(positionals)
            and positionals[0] == _PROMTOOL_READ_VERB
        ):
            return None
        if agent != "observability-engineer":
            return "`promtool` is allowed only for the observability-engineer agent"
        return "`promtool` is allowed only in its `check` family — `promtool query` executes reads against a live server"
    if command in _OBS_ONLY:
        if agent == "observability-engineer":
            return None
        return f"`{command}` is allowed only for the observability-engineer agent"
    if command == "find":
        if not any(arg.startswith(_FIND_ACTIONS) for arg in args):
            return None
        return (
            "`find` with an action flag (`-exec`, `-delete`, `-fprint`, …) runs commands or "
            "writes files — use plain `find` and pipe to a reader"
        )
    if command in _SIMPLE_READERS:
        return None
    if command in _CODE_RUNNERS:
        return (
            f"`{command}` executes code — tests, scripts, builds, and package managers are never "
            "read-only, whatever the command looks like"
        )
    return f"`{command}` is not on the read-only allowlist"


def _tokenize(line: str) -> list[str]:
    """Tokenize one line, with shell operators as their OWN tokens.

    `shlex.split` is the obvious choice and it is WRONG here: it splits on whitespace only, so
    `echo hi; git push` comes back as ['echo', 'hi;', 'git', 'push'] — one command, starting with an
    allowed reader, and the `git push` rides in behind it. That bypasses the entire allowlist, which
    is exactly the silent-allow failure this guard exists to prevent (caught by the corpus below).
    `punctuation_chars=True` makes shlex emit `;`, `|`, `||`, `&&`, `(`, `)` as separate tokens,
    while still honouring quotes — so an operator inside a quoted search pattern stays part of its
    argument and never splits anything.
    """
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    return list(lexer)


def _line_reason(line: str, agent: str) -> "str | None":
    """None if every segment of one line is an allowed read; otherwise the first denial reason."""
    try:
        tokens = _tokenize(line)
    except ValueError:
        return "unbalanced quotes — the guard cannot parse the command, so it cannot vouch for it"
    tokens = _strip_harmless_redirects(tokens)
    for token in tokens:
        if token in _SEPARATORS or not token:
            continue
        if all(ch in _PUNCTUATION for ch in token):
            # An unquoted operator token the separators and harmless-redirect pass did not
            # consume. Quoted operators never land here — shlex keeps them inside their argument.
            if "<" in token or ">" in token:
                return (
                    f"the redirection `{token}` — only `>/dev/null` (any fd) and `2>&1` are "
                    "permitted; return results in the conversation instead of writing files"
                )
            return f"the shell grouping operator `{token}` — subshells are not permitted"
    segments = _split_segments(tokens)
    if not segments:
        return "no recognizable command"
    for segment in segments:
        reason = _segment_reason(segment, agent)
        if reason is not None:
            return reason
    return None


def explain(command: str, agent: str = "") -> "str | None":
    """None if `command` is entirely allowed reads; otherwise the specific rule that denies it.

    `agent` is the BARE agent name (namespace already stripped); it gates agent-specific extras
    (observability-engineer's config validators) and nothing else.
    """
    if not command.strip():
        return None  # nothing to run
    normalized = _SIMPLE_VAR.sub(r"$\1", command)
    structure = _STRUCTURE_DENY.search(normalized)
    if structure:
        return (
            f"the shell construct `{structure.group(0)}` — command substitution, backticks, "
            "`${...}` beyond a plain `${NAME}`, and backgrounding smuggle a second command past "
            "the allowlist (inside double quotes too), so their presence is disqualifying"
        )
    # A newline is a command separator just like `;`, and shlex treats it as plain whitespace —
    # so lines are split off BEFORE tokenizing. A quoted string that genuinely spans a newline is
    # torn in half by this and fails to lex, which denies. That is the correct direction to err.
    for line in normalized.splitlines():
        if not line.strip():
            continue
        reason = _line_reason(line, agent)
        if reason is not None:
            return reason
    return None


def is_allowed(command: str, agent: str = "") -> bool:
    """True only if every segment of every line of `command` is a known read-only command."""
    return explain(command, agent) is None


def main() -> None:
    try:
        # Read raw bytes and decode with utf-8-sig so a leading BOM (which some Windows shells
        # and pipes prepend) is stripped reliably, regardless of the locale encoding.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        # Never vouch for input you could not read. _allow() here (the old behavior) positively
        # certified a truncated GUARDED payload as safe — GOV-001. Exit indeterminate so the hook
        # falls through to its blanket deny instead. See the EXIT_INDETERMINATE comment.
        sys.exit(EXIT_INDETERMINATE)
    if not isinstance(data, dict):
        # Parseable JSON that is not the documented dict envelope (e.g. a bare list) is equally
        # unreadable to the scoping logic below — before this check it crashed on `.get` and only
        # failed safe by accident of the hook treating a traceback's exit 1 as not-its-guard.
        sys.exit(EXIT_INDETERMINATE)

    if data.get("tool_name") != "Bash":
        _allow()

    # The plugin hook is session-wide, so scope here before inspecting the command. The main loop
    # carries NO `agent_type`
    # key, so the user's own Bash exits here and is never inspected.
    agent = data.get("agent_type")
    if agent not in GUARDED_AGENTS:
        # Contract canary. `agent_type` is undocumented. If it is renamed upstream, every payload
        # starts looking like the main loop and the guard would quietly stop guarding — precisely
        # the silent-disarm class of bug this fleet hardened against in validate_fleet.py. So when
        # the payload still identifies a guarded agent under some OTHER key, yet no `agent_type`
        # did, treat the contract as broken and fail CLOSED.
        #
        # The check is deliberately keyed, not a substring search over the envelope:
        #   * `tool_input` is excluded outright — the command is attacker- and user-controlled
        #     text, and scanning it would deny an ordinary main-session command that merely
        #     MENTIONS the agent (`git commit -m "fix save-toolkit:sre"`).
        #   * only keys whose NAME contains "agent" are consulted, and only for exact GUARDED
        #     values, so `cwd`/`transcript_path` — which could legitimately contain an agent's name
        #     as a directory component — can never trip it.
        # Residual: a rename of the identity key itself to a name without "agent" in it is not
        # caught here. This fleet ships no automated probe for it; it is caught only by re-probing
        # the live PreToolUse payload shape after a Claude Code upgrade, the manual step the
        # SCOPING CONTRACT note at the top of this file requires. test_hook_wiring.py exercises the
        # payload shapes we know, but a genuinely new key name is an upstream contract change no
        # offline test can anticipate.
        # Second canary, same silent-disarm class on a different axis: the PLUGIN can be renamed
        # under us. `agent_type` still arrives, still namespaced, but with a namespace PLUGIN_NAME
        # no longer spells — so the exact-match above misses and the `agent is None` canary below
        # never fires, because `agent_type` is present. The guard would hand `sre` and
        # `observability-engineer` unguarded Bash while looking perfectly healthy. A namespaced
        # payload whose BARE name is guarded is unambiguously one of our agents under a moved
        # namespace, so deny and say which constant to fix.
        #
        # Trade-off, accepted deliberately: an unrelated plugin shipping its own agent named `sre`
        # is denied too. That is over-reach, but it is loud, self-explanatory, and one constant
        # away from resolution — whereas the alternative is this fleet's read-only boundary
        # disappearing silently on a rename.
        if isinstance(agent, str) and ":" in agent and agent.rsplit(":", 1)[-1] in GUARDED_AGENT_NAMES:
            _deny(
                f"Blocked: the read-only guard saw a guarded agent under an unrecognized plugin "
                f"namespace ({agent!r}), but PLUGIN_NAME in scripts/readonly-guard.py is still "
                f"{PLUGIN_NAME!r}. The plugin was most likely renamed without updating the guard. "
                "The guard fails closed rather than silently stop guarding. Update PLUGIN_NAME to "
                "match the installed plugin."
            )
        if agent is None and any(
            "agent" in key.lower() and isinstance(value, str) and value in GUARDED_AGENTS
            for key, value in data.items()
            if key != "tool_input"
        ):
            _deny(
                "Blocked: the read-only guard could not identify the calling agent. The PreToolUse "
                "payload named a guarded agent but carried no 'agent_type' field, so the hook payload "
                "contract has changed. The guard fails closed rather than silently stop guarding. "
                "Re-probe the payload shape after the CLI upgrade and update GUARDED_AGENTS in "
                "scripts/readonly-guard.py."
            )
        _allow()

    command = (data.get("tool_input") or {}).get("command", "") or ""
    bare_agent = agent.split(":", 1)[-1] if isinstance(agent, str) else ""
    reason = explain(command, bare_agent)
    if reason is not None:
        _deny(f"Blocked by the read-only agent allowlist guard: {reason}. {_GUIDANCE}")
    _allow()


if __name__ == "__main__":
    main()
