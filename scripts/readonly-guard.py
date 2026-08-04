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
  understand — command substitution, redirection, a subshell, an unbalanced quote — is simply not on
  the list, and is denied.

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
plugin agent (`sde-agents:code-reviewer`), bare for a project/user-scope one. THE MAIN LOOP CARRIES
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
PLUGIN_NAME = "sre-agents"
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

# --- shell constructs we refuse to reason about ---------------------------------------------
# An allowlist only means something if the string really is the commands we think it is. Command
# substitution, redirection, process substitution and backgrounding all smuggle in a second command
# (or a write) past the token inspection below, so their mere PRESENCE is disqualifying. A `>` or
# `$(` inside a quoted search pattern is denied too — a false positive we accept, because the deny
# is loud and the alternative is guessing at shell quoting, which is how the old denylist lost.
_STRUCTURE_DENY = re.compile(
    r"\$\(|`|<\(|\$\{"       # command / process substitution, ${...}
    r"|>|<"                  # any redirection, including heredocs
    r"|(?<!&)&(?!&)"         # a lone & (background); && is a separator, handled below
)
# Operator tokens that separate one command from the next. Every resulting segment must stand on its
# own as an allowed read — `git log; rm -rf /` gets no free pass from its harmless first half.
_SEPARATORS = {"|", "||", "&&", ";", "\n"}

# --- the allowlist --------------------------------------------------------------------------
# Plain readers and filters: they consume input and print. None can write a file on their own (a
# redirect would be needed, and redirects are refused above). `sed` and `awk` are deliberately ABSENT
# — both can write files without any redirect (`sed -i`, awk's `print > "f"` and `system()`).
_SIMPLE_READERS = frozenset({
    "cat", "head", "tail", "less", "nl", "wc", "sort", "uniq", "cut", "tr", "column",
    "grep", "egrep", "fgrep", "rg", "ag",
    "ls", "tree", "file", "stat", "du", "basename", "dirname", "realpath", "pwd",
    "echo", "diff", "cmp", "jq", "true", "false",
    # `dig` is on the list for incident triage (is DNS the problem?). It IS an egress channel —
    # a crafted name can tunnel data — which is why `dig $(...)` dies on structure and why the
    # outbound network allowlist remains the load-bearing egress control, not this guard.
    "dig",
})

# `git` subcommands that have no write SUBCOMMAND (per `git-<name>(1)` synopsis). Several still
# accept `--output=<file>`/`-o <file>` to write a report to disk (diff, log, show, diff-tree,
# whatchanged) — those flag forms are rejected below in _git_allowed, since being on this list is
# not a licence to write files.
_GIT_READ = frozenset({
    "diff", "log", "show", "blame", "status", "shortlog", "describe", "rev-parse", "rev-list",
    "ls-files", "ls-tree", "cat-file", "show-ref", "grep", "whatchanged", "diff-tree",
    "merge-base", "name-rev", "version", "help",
})
# Flags on _GIT_READ subcommands that redirect output into a file. `--output=<file>` and its
# separate-argument form `-o <file>` are accepted by diff/log/show/diff-tree/whatchanged (they
# share the diff plumbing) and write to the named path with no shell redirect involved, so
# _STRUCTURE_DENY never sees them. Any occurrence is disqualifying.
_GIT_READ_WRITE_FLAGS = frozenset({"-o", "--output"})
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
# `git tag v1.0`). Allowed only when no positional is present, or a read flag makes the intent
# explicit — and never when a write flag appears. The flag sets differ per subcommand on purpose:
# `-a` means --all for branch (read) but --annotate for tag (WRITE).
_GIT_LIST_LIKE = {
    "branch": {
        "read": frozenset({
            "-a", "-r", "-v", "-vv", "--all", "--remotes", "--verbose", "--list", "--contains",
            "--no-contains", "--merged", "--no-merged", "--show-current", "--format", "--sort",
            "--points-at", "-i", "--ignore-case",
        }),
        "write": frozenset({
            "-d", "-D", "-m", "-M", "-c", "-C", "-f", "--delete", "--move", "--copy", "--force",
            "--set-upstream-to", "-u", "--unset-upstream", "--track", "-t", "--no-track",
            "--edit-description",
        }),
    },
    "tag": {
        "read": frozenset({
            "-l", "--list", "-n", "--contains", "--no-contains", "--points-at", "--sort",
            "--format", "--merged", "--no-merged", "-v", "--verify", "-i", "--ignore-case",
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

# `cf` (Cloud Foundry CLI v8) read verbs for incident triage. `cf env` is ABSENT by design: it
# prints the app's full environment — credentials included — to an agent that also holds web
# egress, and that pairing is exactly the exfiltration shape the fleet's doctrine forbids.
_CF_READ = frozenset({
    "app", "apps", "events", "logs", "routes", "services", "spaces", "orgs", "target",
})

# Commands only observability-engineer may run — it validates observability config; sre does not
# need these, and the smaller each profile is, the better it fails.
_OBS_ONLY = frozenset({"yamllint"})
# `promtool` is verb-gated like git: only its `check` family reads (observability-only as well).
_PROMTOOL_READ_VERB = "check"

_REASON = (
    "Blocked: this is a read-only agent, and its Bash access is limited to an ALLOWLIST of "
    "read-only commands (cf app/apps/events/logs/routes/services, git diff/log/show/blame/status, "
    "rg, grep, ls, cat, head, find, gh pr view/diff, and similar filters). The command above is "
    "not on that list. Note this agent may NOT execute code — no test runners, no scripts, no "
    "package managers — because running a repository's code is not a read-only act, whatever the "
    "command looks like. Inspect with reads, cite the builder's or CI's test evidence rather than "
    "re-running it, and report anything that needs changing as a finding for the author to apply "
    "— never apply it yourself. A denied command you believe is a legitimate read is a loud, "
    "one-line allowlist fix by PR — never work around the guard."
)


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
        if token in _SEPARATORS:
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    return [segment for segment in segments if segment]


def _positionals(args: list[str]) -> list[str]:
    return [arg for arg in args if not arg.startswith("-")]


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
        # Even for a read subcommand, `--output=<file>` / `-o <file>` writes to disk without any
        # shell redirect. Reject the flag in every form (`--output=x`, `--output x`, `-o x`).
        return not any(arg.split("=", 1)[0] in _GIT_READ_WRITE_FLAGS for arg in rest)

    if subcommand in _GIT_READ_VERBS:
        verbs = _positionals(rest)
        return bool(verbs) and verbs[0] in _GIT_READ_VERBS[subcommand]

    if subcommand == "config":
        return any(arg.split("=", 1)[0] in _GIT_CONFIG_READ for arg in rest)

    if subcommand in _GIT_LIST_LIKE:
        flags = _GIT_LIST_LIKE[subcommand]
        bare = [arg.split("=", 1)[0] for arg in rest if arg.startswith("-")]
        if any(flag in flags["write"] for flag in bare):
            return False
        if any(flag in flags["read"] for flag in bare):
            return True
        # No flags either way: listing is the default, but a positional means "create this".
        return not _positionals(rest)

    return False


def _gh_allowed(args: list[str]) -> bool:
    positionals = _positionals(args)
    if len(positionals) < 2:
        return False
    group, verb = positionals[0], positionals[1]
    return verb in _GH_READ.get(group, frozenset())


def _cf_allowed(args: list[str]) -> bool:
    positionals = _positionals(args)
    return bool(positionals) and positionals[0] in _CF_READ


def _segment_allowed(segment: list[str], agent: str) -> bool:
    command, args = segment[0], segment[1:]
    # A path to a binary (`/bin/cat`, `./deploy.sh`, `scripts/setup.sh`) is never allowed: the
    # allowlist names commands, and a path is how you smuggle a different one in.
    if "/" in command or "\\" in command or "=" in command:
        return False
    if command == "git":
        return _git_allowed(args)
    if command == "gh":
        return _gh_allowed(args)
    if command == "cf":
        return _cf_allowed(args)
    if command == "promtool":
        positionals = _positionals(args)
        return (
            agent == "observability-engineer"
            and bool(positionals)
            and positionals[0] == _PROMTOOL_READ_VERB
        )
    if command in _OBS_ONLY:
        return agent == "observability-engineer"
    if command == "find":
        return not any(arg.startswith(_FIND_ACTIONS) for arg in args)
    return command in _SIMPLE_READERS


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


def is_allowed(command: str, agent: str = "") -> bool:
    """True only if every segment of every line of `command` is a known read-only command.

    `agent` is the BARE agent name (namespace already stripped); it gates agent-specific extras
    (observability-engineer's config validators) and nothing else.
    """
    if not command.strip():
        return True  # nothing to run
    if _STRUCTURE_DENY.search(command):
        return False
    # A newline is a command separator just like `;`, and shlex treats it as plain whitespace —
    # so lines are split off BEFORE tokenizing. A quoted string that genuinely spans a newline is
    # torn in half by this and fails to lex, which denies. That is the correct direction to err.
    for line in command.splitlines():
        if not line.strip():
            continue
        try:
            tokens = _tokenize(line)
        except ValueError:
            return False  # unbalanced quotes: we do not understand it, so we do not permit it
        segments = _split_segments(tokens)
        if not segments or not all(_segment_allowed(segment, agent) for segment in segments):
            return False
    return True


def main() -> None:
    try:
        # Read raw bytes and decode with utf-8-sig so a leading BOM (which some Windows shells
        # and pipes prepend) is stripped reliably, regardless of the locale encoding.
        raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        _allow()  # unparseable input -> don't interfere with the normal permission flow

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
        #     MENTIONS the agent (`git commit -m "fix sde-agents:code-reviewer"`).
        #   * only keys whose NAME contains "agent" are consulted, and only for exact GUARDED
        #     values, so `cwd`/`transcript_path` — which could legitimately contain an agent's name
        #     as a directory component — can never trip it.
        # Residual: a rename to a key without "agent" in it is not caught here; that is what
        # scripts/probe_plugin.py exists to catch after a CLI upgrade.
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
    if not is_allowed(command, bare_agent):
        _deny(_REASON)
    _allow()


if __name__ == "__main__":
    main()
