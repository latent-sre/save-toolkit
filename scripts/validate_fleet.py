#!/usr/bin/env python3
"""Validate canonical fleet authority, routing, plugin, and generated-host contracts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from scripts import generate_platform_adapters as adapters
except ModuleNotFoundError:
    import generate_platform_adapters as adapters  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOOL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.*-]*)(?:\((.*)\))?$")
KNOWN_AGENT_FIELDS = {"name", "description", "tools", "model"}
# `model:` accepts a generation ALIAS only. An alias tracks the current model of its tier and
# cannot rot; a full ID (claude-opus-4-1-20250805) silently pins a model past its usefulness,
# which is the staleness the old blanket ban existed to prevent. Keeping the ban only on the
# part that actually goes stale is what lets routine lanes be tiered down cheaply.
# `inherit` is the default and is accepted explicitly so a lane can document the choice.
MODEL_ALIASES = {"haiku", "sonnet", "opus", "fable", "inherit"}
PLUGIN_INERT_AGENT_FIELDS = {"hooks", "mcpServers", "permissionMode"}
BUILTIN_TOOLS = {
    "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Skill", "ToolSearch",
    "WebFetch", "WebSearch", "Write",
}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
LOCAL_READ_TOOLS = {"Read", "Grep", "Glob"}
# The evidence-label triad, pinned once: an agent that uses any label must carry all three.
EVIDENCE_TRIAD = ("[verified]", "[sourced]", "[unverified]")
# The delegating form of the handoff rule, and the disclaimers that replace it in a lane holding no
# `Agent` tool. Matched as literal substrings so a reworded rule fails loudly here rather than
# quietly reintroducing an instruction the lane cannot carry out.
DELEGATION_IMPERATIVE = "Hand to exactly one agent"
# Several equally correct phrasings are already in use, so the set is a union rather than one house
# style — the point is that the lane says somewhere in its own handoff section that it cannot
# dispatch, not that every file says it identically.
#
# Every member must assert INCAPABILITY. "Recommend exactly one next owner" was briefly here and is
# deliberately gone: it describes what the lane does, not what it cannot do, so an agent could keep
# that sentence, drop every "cannot" statement, and still pass — reopening the precise
# misleading-authority drift this contract exists to stop. Recommending and being unable to dispatch
# are different claims, and only the second one is the control.
NON_DELEGATION_DISCLAIMERS = (
    "cannot invoke",
    "cannot delegate",
    "caller must invoke",
)


def _flatten(text: str) -> str:
    """Collapse all whitespace runs to single spaces for substring matching.

    Every phrase above is longer than a few words, so in a hard-wrapped markdown body it is a coin
    flip whether a newline lands in the middle of one. `repository-investigator` really does wrap
    "You cannot\\ndelegate or contact the external lane yourself", and a naive `in` test against the
    raw body misses it — reporting a violation in a file that is already correct. Matching against
    the flattened text makes the check independent of where the author's reflow put the breaks.
    """
    return " ".join(text.split())
WEB_TOOLS = {"WebFetch", "WebSearch"}
EVIDENCE_MCP_TOOLS = {
    "mcp__claude_ai_Context7__query-docs",
    "mcp__claude_ai_Context7__resolve-library-id",
    "mcp__plugin_context7_context7__query-docs",
    "mcp__plugin_context7_context7__resolve-library-id",
    "mcp__plugin_githits_githits__code_files",
    "mcp__plugin_githits_githits__code_grep",
    "mcp__plugin_githits_githits__code_read",
    "mcp__plugin_githits_githits__docs_list",
    "mcp__plugin_githits_githits__docs_read",
    "mcp__plugin_githits_githits__get_example",
    "mcp__plugin_githits_githits__pkg_changelog",
    "mcp__plugin_githits_githits__pkg_deps",
    "mcp__plugin_githits_githits__pkg_info",
    "mcp__plugin_githits_githits__pkg_upgrade_review",
    "mcp__plugin_githits_githits__pkg_vulns",
    "mcp__plugin_githits_githits__search",
    "mcp__plugin_githits_githits__search_language",
    "mcp__plugin_githits_githits__search_status",
}
SCRIBE_EXECUTION_VERBS = (
    r"(?:run|execute|invoke|rehearse|test|try|validate|verify|perform|conduct)"
)
SCRIBE_EXECUTION_OBJECTS = (
    r"(?:commands?|procedures?|runbooks?|game[\s/-]?days?|drills?|syntax|outputs?|targets?|ones?)"
)
SCRIBE_IMPERATIVE_EXECUTION_RE = re.compile(
    rf"(?i)^(?:please\s+)?(?P<verb>{SCRIBE_EXECUTION_VERBS})\s+"
    rf"(?:(?:the|these|those|a|an|any|each|all|supplied|read-only|live|realistic)\s+)*"
    rf"(?P<object>{SCRIBE_EXECUTION_OBJECTS})\b"
)
SCRIBE_ACTOR_EXECUTION_RE = re.compile(
    rf"(?i)\b(?P<actor>scribe|you|this agent|the documentation agent)\b"
    rf"(?=(?P<context>[^\n.!?;]{{0,120}}?)\b(?P<verb>{SCRIBE_EXECUTION_VERBS})\b)"
)
SCRIBE_NEGATED_ACTOR_RE = re.compile(
    r"(?i)\b(?:not|never|cannot|can't|couldn't|mustn't|shouldn't|won't|wouldn't|"
    r"doesn't|don't|didn't|isn't|aren't|wasn't|weren't|forbidden|prohibited|"
    r"disallowed|unable)\b"
)
SCRIBE_NEGATED_REQUEST_RE = re.compile(
    r"(?i)\b(?:do\s+not|don't|never)\s+"
    r"(?:ask|tell|allow|permit|require|instruct|let)(?:\s+(?:the|this))?\s*$"
)
SCRIBE_POLARITY_RESET_RE = re.compile(r"(?i)\b(?:but|however|instead)\b")
SCRIBE_FENCED_CODE_RE = re.compile(r"(?s)(?:```|~~~).*?(?:```|~~~)")
SCRIBE_PRESSURE_TABLE_ROW_RE = re.compile(
    r'(?im)^\|\s*"[^"\n]*"\s*\|\s*(?:do\s+not|never|stop\b)[^|\n]*\|\s*$'
)
SCRIBE_CLAUSE_SPLIT_RE = re.compile(r"(?:[.!?;]\s+|\n+)")
SCRIBE_MARKDOWN_LEAD_RE = re.compile(r"^\s*(?:(?:[-+*>#]+|\d+[.)])\s*)+")
SCRIBE_LOADED_SOURCES = (
    Path("agents/scribe.md"),
    Path("skills/runbook/SKILL.md"),
    Path("skills/postmortem/SKILL.md"),
    Path("skills/operational-learning/SKILL.md"),
    Path("skills/service-onboarding/SKILL.md"),
    Path("skills/incident-command/SKILL.md"),
    Path("skills/runbook/assets/runbook-template.md"),
    Path("skills/postmortem/assets/postmortem-template.md"),
)
EXTERNAL_EVIDENCE_TOOLS = {"ToolSearch", *WEB_TOOLS, *EVIDENCE_MCP_TOOLS}
SCRIBE_TOOLS = {"Read", "Grep", "Glob", "Edit", "Write", "Skill"}
EXPECTED_AUTHORITY = {
    "reviewer": {
        "required": LOCAL_READ_TOOLS,
        "forbidden": {"Bash", "Agent", "Skill", *WRITE_TOOLS, *EXTERNAL_EVIDENCE_TOOLS},
    },
    "repository-investigator": {
        "required": LOCAL_READ_TOOLS,
        "forbidden": {
            "Bash", "Agent", "Skill", *WRITE_TOOLS, *EXTERNAL_EVIDENCE_TOOLS,
        },
    },
    "researcher": {
        "required": EXTERNAL_EVIDENCE_TOOLS,
        "forbidden": {"Read", "Grep", "Glob", "Bash", "Agent", "Skill", *WRITE_TOOLS},
    },
    "sde": {
        "required": {"Read", "Bash", "Edit", "Write", "Skill", "Agent"},
        "forbidden": EXTERNAL_EVIDENCE_TOOLS,
    },
    "sre": {
        "required": {"Read", "Bash", "Skill", "Agent"},
        "forbidden": {*WRITE_TOOLS, *EXTERNAL_EVIDENCE_TOOLS},
    },
    "observability-engineer": {
        "required": {"Read", "Bash", "Edit", "Write", "Skill", "Agent"},
        "forbidden": EXTERNAL_EVIDENCE_TOOLS,
    },
    "scribe": {
        "required": SCRIBE_TOOLS,
        "forbidden": {*(BUILTIN_TOOLS - SCRIBE_TOOLS), *EXTERNAL_EVIDENCE_TOOLS},
    },
    "prompt-engineer": {
        "required": {"Read", "Bash", "Edit", "Write", "Skill", "Agent"},
        "forbidden": EXTERNAL_EVIDENCE_TOOLS,
    },
}
EXPECTED_DELEGATION = {
    "reviewer": set(),
    "repository-investigator": set(),
    "researcher": set(),
    "sde": {"reviewer", "scribe", "researcher"},
    "sre": {"researcher"},
    "observability-engineer": {"scribe", "researcher"},
    "scribe": set(),
    "prompt-engineer": {"researcher"},
}


def _tool_specs(raw: object) -> list[str]:
    return adapters._split_tool_specs(raw)  # shared grammar with the generator


def _tool_bases(raw: object) -> set[str]:
    return {spec.split("(", 1)[0] for spec in _tool_specs(raw)}


def _delegates(raw: object) -> set[str]:
    result: set[str] = set()
    for spec in _tool_specs(raw):
        match = TOOL_RE.fullmatch(spec)
        if match and match.group(1) == "Agent" and match.group(2):
            result.update(item.strip() for item in match.group(2).split(",") if item.strip())
    return result


def validate_agents(root: Path) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    names: list[str] = []
    parsed: dict[str, tuple[Path, dict[str, object], str]] = {}
    for path in sorted((root / "agents").glob("*.md")):
        try:
            fields, body, _ = adapters.parse_frontmatter(path)
        except (OSError, UnicodeError, ValueError) as exc:
            failures.append(str(exc))
            continue
        name = fields.get("name")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name) or name != path.stem:
            failures.append(f"{path}: name must be kebab-case and match the filename")
            continue
        names.append(name)
        parsed[name] = (path, fields, body)
        unknown = sorted(set(fields) - KNOWN_AGENT_FIELDS)
        if unknown:
            failures.append(f"{path}: unknown or unsupported plugin agent field(s): {', '.join(unknown)}")
        model = fields.get("model")
        if "model" in fields and (not isinstance(model, str) or model not in MODEL_ALIASES):
            failures.append(
                f"{path}: model must be one of {', '.join(sorted(MODEL_ALIASES))} — "
                "a full model ID goes stale silently"
            )
        inert = sorted(set(fields) & PLUGIN_INERT_AGENT_FIELDS)
        if inert:
            failures.append(f"{path}: plugin-inert authority field(s) are forbidden: {', '.join(inert)}")
        description = fields.get("description")
        if not isinstance(description, str) or not description.strip():
            failures.append(f"{path}: description is required")
        elif len(description.encode("utf-8")) > 1024:
            failures.append(f"{path}: description exceeds 1024 UTF-8 bytes")
        if "tools" not in fields:
            failures.append(f"{path}: tools must be explicit; omission inherits all tools")
            continue
        specs = _tool_specs(fields["tools"])
        # A repeated grant signals a bad merge and defeats the set-based authority reasoning below,
        # where the duplicate silently collapses and the mistake never surfaces.
        duplicates = sorted({spec for spec in specs if specs.count(spec) > 1})
        if duplicates:
            failures.append(f"{path}: duplicate tool grant(s): {', '.join(duplicates)}")
        for spec in specs:
            match = TOOL_RE.fullmatch(spec)
            if not match:
                failures.append(f"{path}: malformed tool grant {spec!r}")
                continue
            base = match.group(1)
            if base.startswith("mcp__"):
                if base not in EVIDENCE_MCP_TOOLS:
                    failures.append(f"{path}: MCP authority is not exact-approved: {base}")
                if match.group(2):
                    failures.append(f"{path}: MCP grants cannot carry scoped arguments: {spec}")
            elif base not in BUILTIN_TOOLS:
                failures.append(f"{path}: unknown tool grant {base!r}")
            elif match.group(2) and base != "Agent":
                # A scoped grant like `Bash(git diff:*)` READS like a narrowed tool and does nothing:
                # probed on CLI 2.1.200, an agent granted `Bash(git diff:*)` ran `git status` exactly
                # like one granted bare `Bash`. Only `Agent(target)` scoping is honored (and only on a
                # main-thread agent). A scoped grant here is a limit that looks real and is not.
                failures.append(
                    f"{path}: scoped tool grant {spec!r} is silently ignored by the runtime; "
                    f"grant bare {base!r} (per-command scoping lives in the guard, not tools:)"
                )
        if "## The handoff packet" not in body and "## Handoffs" not in body:
            failures.append(f"{path}: missing handoff contract")
        # An agent with no `Agent` tool cannot dispatch anyone, so the shared handoff block's
        # imperative form is a false instruction in that lane. This is not hypothetical tidying:
        # `reviewer` — local read-only by tool absence, and the lane that gates every merge —
        # carried the `sde` block verbatim, telling it to "Hand to exactly one agent" and to load
        # `production-change-gate`, a skill it holds no `Skill` tool to load. `scribe`, under the
        # identical constraint, had been adapted correctly ("Recommend exactly one next owner. This
        # role cannot invoke that owner."), which is what proves the reviewer copy was drift rather
        # than a deliberate choice. A filled-in template beats a prose constraint 70 lines earlier,
        # so the contradiction is pinned here rather than left to review.
        if "Agent" not in _tool_bases(fields["tools"]):
            flat = _flatten(body)
            if DELEGATION_IMPERATIVE in flat:
                failures.append(
                    f"{path}: says {DELEGATION_IMPERATIVE!r} but holds no Agent tool; this lane can "
                    f"only recommend a next owner (see scribe.md for the adapted wording)"
                )
            if not any(phrase in flat for phrase in NON_DELEGATION_DISCLAIMERS):
                failures.append(
                    f"{path}: holds no Agent tool, so its handoff block must state that it cannot "
                    f"invoke the next owner; expected one of {list(NON_DELEGATION_DISCLAIMERS)}"
                )
        # The evidence triad is all-or-nothing: an agent that keeps [verified]/[unverified] but drops
        # [sourced] silently loses the ability to distinguish "I ran it" from "the file says so".
        present = [label for label in EVIDENCE_TRIAD if label in body]
        if not present:
            failures.append(f"{path}: missing evidence-label contract")
        elif len(present) != len(EVIDENCE_TRIAD):
            missing = [label for label in EVIDENCE_TRIAD if label not in present]
            failures.append(f"{path}: incomplete evidence-label triad; missing {', '.join(missing)}")

    expected_names = set(EXPECTED_AUTHORITY)
    if set(names) != expected_names:
        failures.append(
            "agents/: roster mismatch; expected " + ", ".join(sorted(expected_names))
            + "; found " + ", ".join(sorted(names))
        )
    for name, (path, fields, _) in parsed.items():
        bases = _tool_bases(fields["tools"])
        authority = EXPECTED_AUTHORITY[name]
        missing = sorted(authority["required"] - bases)
        forbidden = sorted(authority["forbidden"] & bases)
        if missing:
            failures.append(f"{path}: missing required tool(s): {', '.join(missing)}")
        if forbidden:
            failures.append(f"{path}: forbidden tool(s): {', '.join(forbidden)}")
        delegates = _delegates(fields["tools"])
        expected_delegates = EXPECTED_DELEGATION[name]
        if delegates != expected_delegates:
            failures.append(
                f"{path}: delegation mismatch; expected "
                f"{', '.join(sorted(expected_delegates)) or 'none'}; found "
                f"{', '.join(sorted(delegates)) or 'none'}"
            )
        for target in sorted(delegates):
            if target not in expected_names:
                failures.append(f"{path}: Agent target {target!r} does not exist")
        if name in adapters.GUARDED_AGENTS and "Bash" not in bases:
            failures.append(f"{path}: guard roster claims an agent without Bash")
        # The reverse of the line above, and the higher-value half: an agent that holds Bash with no
        # write tool is a read-only-by-intent agent whose read-only-ness is only a promise unless the
        # guard actually scopes it. If it is not on the guard roster, that promise has no control
        # behind it — and adding such an agent is exactly when this is easy to forget.
        if "Bash" in bases and not (bases & WRITE_TOOLS) and name not in adapters.GUARDED_AGENTS:
            failures.append(
                f"{path}: agent holds Bash without a write tool but is not on the guard roster "
                f"(GUARDED_AGENTS in generate_platform_adapters.py / readonly-guard.py); its "
                f"read-only posture is unenforced"
            )
    return names, failures


def _scribe_instruction_clauses(text: str) -> list[str]:
    """Return prose clauses while excluding code and quoted pressure examples."""

    prose = SCRIBE_FENCED_CODE_RE.sub(" ", text)
    prose = SCRIBE_PRESSURE_TABLE_ROW_RE.sub(" ", prose).replace("`", "")
    clauses: list[str] = []
    for raw_clause in SCRIBE_CLAUSE_SPLIT_RE.split(prose):
        clause = " ".join(raw_clause.split())
        clause = SCRIBE_MARKDOWN_LEAD_RE.sub("", clause).lstrip("| ").strip()
        if clause:
            clauses.append(clause)
    return clauses


def _find_scribe_execution_directive(text: str) -> tuple[str, str] | None:
    """Find affirmative execution language aimed at the documentation lane.

    This is a bounded structural guard, not a semantic classifier. Bare imperatives in trusted
    instruction prose are treated as addressed to the loading agent. Explicit scribe-agent clauses
    are allowed only when their execution verb is negated or when a negated request governs the
    actor, such as "Do not ask scribe to run commands."
    """

    for clause in _scribe_instruction_clauses(text):
        for actor_match in SCRIBE_ACTOR_EXECUTION_RE.finditer(clause):
            context = actor_match.group("context")
            governed_prefix = clause[: actor_match.start()]
            polarity_context = SCRIBE_POLARITY_RESET_RE.split(context)[-1]
            request_is_negated = (
                not SCRIBE_POLARITY_RESET_RE.search(context)
                and SCRIBE_NEGATED_REQUEST_RE.search(governed_prefix) is not None
            )
            if not SCRIBE_NEGATED_ACTOR_RE.search(polarity_context) and not request_is_negated:
                excerpt = clause[actor_match.start() : actor_match.end("verb")]
                return "documentation-agent execution language", excerpt

        imperative_match = SCRIBE_IMPERATIVE_EXECUTION_RE.search(clause)
        if imperative_match is not None:
            return "imperative execution language", imperative_match.group(0)
    return None


def validate_scribe_bundle(root: Path) -> list[str]:
    """Guard known scribe bundle boundaries; outer tool isolation remains load-bearing.

    These structural checks catch ownership regressions and broad classes of authoring directives.
    They are not a semantic proof that arbitrary prose cannot imply execution.
    """

    contracts = {
        Path("agents/scribe.md"): {
            "required": (
                "**Knowledge closeout mode**",
                "`operational-learning`",
                "Return the exact runbook path or URL and alert name to `observability-engineer`",
            ),
            "forbidden": ("and link it from the alert",),
        },
        Path("skills/runbook/SKILL.md"): {
            "required": (
                "A named human or service owner runs game days\n"
                "or drills under approved, realistic conditions; `scribe` only records the supplied results",
                "never execute from\n  this documentation lane, including a read-only command",
            ),
            "forbidden": ("run read-only ones to confirm syntax",),
        },
        Path("skills/postmortem/SKILL.md"): {
            "required": (
                "operating documentation → typed `scribe`",
                "every new operational fact has a **learning disposition**",
            ),
            "forbidden": ("operating documentation → typed `observability-engineer`",),
        },
        Path("skills/operational-learning/SKILL.md"): {
            "required": (
                "A discovery is learned only when evidence and an\nexplicit disposition",
                "An active incident permits only\n   `proposed` or `blocked` outcomes",
                "`prepared` means an actual reviewable documentation diff exists",
            ),
            "forbidden": (),
        },
        Path("skills/service-onboarding/SKILL.md"): {
            "required": ("emit an **evidence-bound\n   handoff** to `scribe`",),
            "forbidden": (),
        },
        Path("skills/incident-command/SKILL.md"): {
            "required": (
                "The caller, not `sre`, separately\ndispatches typed `observability-engineer` for detection changes and typed `scribe` for the\npostmortem, operating guidance, and learning dispositions",
            ),
            "forbidden": (
                "typed `observability-engineer` confirm that user impact",
                "hand the timeline to the typed `observability-engineer` agent for the durable",
                "typed `observability-engineer` agent captures\ndurable operating guidance",
            ),
        },
        Path("skills/runbook/assets/runbook-template.md"): {
            "required": (
                "hand the timeline and evidence to the `scribe` agent for retrospective documentation",
                "last_verified: null",
                "Change `last_verified` only when incoming rehearsal evidence binds this exact runbook version",
                "otherwise leave it unchanged",
            ),
            "forbidden": (
                "hand the timeline and evidence to the `observability-engineer` agent for retrospective documentation",
                "bump `last_verified`",
            ),
        },
        Path("skills/postmortem/assets/postmortem-template.md"): {
            "required": (
                "## Operational knowledge dispositions",
                "## Verification gaps",
            ),
            "forbidden": (),
        },
    }
    failures: list[str] = []
    loaded_sources = set(SCRIBE_LOADED_SOURCES)
    contract_sources = set(contracts)
    if loaded_sources != contract_sources:
        failures.append(
            "scribe bundle source roster mismatch: "
            f"missing contracts={sorted(loaded_sources - contract_sources)}; "
            f"unexpected contracts={sorted(contract_sources - loaded_sources)}"
        )
    for relative in SCRIBE_LOADED_SOURCES:
        contract = contracts.get(relative, {"required": (), "forbidden": ()})
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            failures.append(f"{path}: cannot validate scribe bundle contract: {exc}")
            continue
        for required in contract["required"]:
            if required not in text:
                failures.append(f"{path}: missing scribe bundle contract: {required!r}")
        for forbidden in contract["forbidden"]:
            if forbidden in text:
                failures.append(f"{path}: stale scribe bundle contract: {forbidden!r}")
        directive = _find_scribe_execution_directive(text)
        if directive is not None:
            label, excerpt = directive
            failures.append(
                f"{path}: scribe execution directive ({label}): {excerpt!r}"
            )
    return failures


def _load_guard(root: Path):
    """Import scripts/readonly-guard.py by path — its hyphen makes it un-importable by name."""
    import importlib.util

    guard_path = root / "scripts" / "readonly-guard.py"
    spec = importlib.util.spec_from_file_location("_readonly_guard", guard_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load guard module from {guard_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_guard_wiring(root: Path, agent_names: list[str]) -> list[str]:
    """Tie the guard's own roster and namespace to the fleet it claims to protect.

    Three silent-disarm holes, each a one-line edit away:
      * the guard's roster and the generator's roster are two independent literals that nothing
        forces to agree — a name added to one but not the other guards nothing or renders no adapter;
      * a roster entry that resolves to no agent (a typo) makes the guard match nobody, silently;
      * the guard recognizes its subject by the namespaced `agent_type` (`save-toolkit:sre`), so a
        plugin rename that misses PLUGIN_NAME makes every payload fail to match and the guard allows
        everything while looking healthy.
    """
    failures: list[str] = []
    try:
        guard = _load_guard(root)
    except Exception as exc:  # a broken guard must fail loudly, never certify a stale one
        return [f"scripts/readonly-guard.py: cannot load to validate guard wiring: {exc}"]

    guard_roster = set(getattr(guard, "GUARDED_AGENT_NAMES", set()))
    if guard_roster != set(adapters.GUARDED_AGENTS):
        failures.append(
            "guard roster mismatch: readonly-guard.py GUARDED_AGENT_NAMES="
            f"{sorted(guard_roster)} vs generate_platform_adapters.py GUARDED_AGENTS="
            f"{sorted(adapters.GUARDED_AGENTS)}; the two must name the same agents"
        )
    unknown = sorted(guard_roster - set(agent_names))
    if unknown:
        failures.append(
            f"guard roster names non-existent agent(s): {', '.join(unknown)}; the guard would "
            f"match nobody for those names"
        )

    plugin_name = getattr(guard, "PLUGIN_NAME", None)
    try:
        manifest_name = adapters._manifest(root / ".claude-plugin/plugin.json").get("name")
    except (OSError, ValueError) as exc:
        failures.append(f".claude-plugin/plugin.json: cannot read to check guard PLUGIN_NAME: {exc}")
        manifest_name = None
    if manifest_name is not None and plugin_name != manifest_name:
        failures.append(
            f"guard PLUGIN_NAME {plugin_name!r} != manifest name {manifest_name!r}; a plugin rename "
            f"that misses PLUGIN_NAME makes the namespaced agent_type never match and disarms the guard"
        )
    return failures


def validate_roster_graph(root: Path) -> list[str]:
    """Bind the AGENTS.md roster 'Delegates to' column to the enforced delegation graph.

    The fleet's delegation graph has exactly one enforced SOURCE — each agent's `Agent(...)` grant
    in frontmatter, checked against EXPECTED_DELEGATION in validate_agents — and one human-readable
    RENDER: the "Delegates to" column of the roster table in AGENTS.md. Nothing kept the render
    honest until here. An edge added to (or dropped from) an agent's frontmatter, or a new agent,
    could leave the roster describing a graph the fleet no longer has — the repo's signature
    silent-drift failure, one table further out from the code. This turns the render into a
    validated projection of the enforced graph rather than a hand-kept second story.

    It parses only the LAST cell of each roster row for edges, so backticked tool names in the
    "Tools posture" cell (`Read`, `cf`, `git`) can never be misread as delegation targets.
    """
    path = root / "AGENTS.md"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [str(exc)]
    documented: dict[str, set[str]] = {}
    failures: list[str] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if not in_table:
            if stripped.startswith("|") and "Delegates to" in stripped and "Agent" in stripped:
                in_table = True
            continue
        if not stripped.startswith("|"):
            break  # first non-table line ends the roster
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 4:
            continue
        agent_names = re.findall(r"`([a-z0-9-]+)`", cells[0])
        if not agent_names:
            continue  # header/separator row, or a row without a backticked agent name
        agent = agent_names[0]
        if agent in documented:
            failures.append(f"{path}: duplicate roster row for agent {agent!r}")
            continue
        documented[agent] = set(re.findall(r"`([a-z0-9-]+)`", cells[-1]))

    if not documented:
        return [f"{path}: could not find the roster 'Delegates to' table to validate the graph"]

    expected_agents = set(EXPECTED_DELEGATION)
    if set(documented) != expected_agents:
        failures.append(
            f"{path}: roster rows {sorted(documented)} do not match the enforced roster "
            f"{sorted(expected_agents)}"
        )
    for agent in sorted(set(documented) & expected_agents):
        if documented[agent] != EXPECTED_DELEGATION[agent]:
            failures.append(
                f"{path}: roster 'Delegates to' for {agent!r} is "
                f"{', '.join(sorted(documented[agent])) or '—'}, but the enforced graph has "
                f"{', '.join(sorted(EXPECTED_DELEGATION[agent])) or '—'}"
            )
    return failures


def validate_repo(root: Path = ROOT) -> tuple[list[str], list[str]]:
    names, failures = validate_agents(root)
    failures.extend(validate_scribe_bundle(root))
    failures.extend(validate_guard_wiring(root, names))
    failures.extend(validate_roster_graph(root))
    failures.extend(adapters.validate_platform_support(root))
    return names, failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    names, failures = validate_repo(ROOT)
    if failures:
        print(f"Fleet validation: FAIL ({len(failures)} issue(s))")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"Fleet validation: PASS ({len(names)} agents, plugin and adapters consistent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
