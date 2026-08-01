#!/usr/bin/env python3
"""Validate canonical fleet authority, routing, plugin, and generated-host contracts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from scripts import generate_platform_adapters as adapters
except ModuleNotFoundError:
    import generate_platform_adapters as adapters  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOOL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_.*-]*)(?:\((.*)\))?$")
KNOWN_AGENT_FIELDS = {"name", "description", "tools"}
PLUGIN_INERT_AGENT_FIELDS = {"hooks", "mcpServers", "permissionMode"}
BUILTIN_TOOLS = {
    "Agent", "Bash", "Edit", "Glob", "Grep", "NotebookEdit", "Read", "Skill", "ToolSearch",
    "WebFetch", "WebSearch", "Write",
}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
LOCAL_READ_TOOLS = {"Read", "Grep", "Glob"}
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
        "required": {*LOCAL_READ_TOOLS, "Skill"},
        "forbidden": {"Bash", "Agent", *WRITE_TOOLS, *EXTERNAL_EVIDENCE_TOOLS},
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
    "sre-steward": {
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
    "sre": {"sre-steward", "scribe", "researcher"},
    "sre-steward": {"scribe", "researcher"},
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
        for spec in _tool_specs(fields["tools"]):
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
        if "## The handoff packet" not in body and "## Handoffs" not in body:
            failures.append(f"{path}: missing handoff contract")
        if "[verified]" not in body or "[unverified]" not in body:
            failures.append(f"{path}: missing evidence-label contract")

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
                "Return the exact runbook path or URL and alert name to `sre-steward`",
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
            "forbidden": ("operating documentation → typed `sre-steward`",),
        },
        Path("skills/operational-learning/SKILL.md"): {
            "required": (
                "A discovery is learned only when evidence and an\nexplicit disposition",
                "only `proposed` or `blocked` dispositions—no terminal KB outcome",
                "packet-selected fleet/code directory as KB write authority",
            ),
            "forbidden": (),
        },
        Path("skills/service-onboarding/SKILL.md"): {
            "required": ("emit a **learning disposition**\n   packet to `scribe`",),
            "forbidden": (),
        },
        Path("skills/incident-command/SKILL.md"): {
            "required": (
                "after resolution typed `scribe` captures the postmortem, operating guidance, and learning dispositions",
            ),
            "forbidden": (
                "hand the timeline to the typed `sre-steward` agent for the durable",
                "typed `sre-steward` agent captures\ndurable operating guidance",
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
                "hand the timeline and evidence to the `sre-steward` agent for retrospective documentation",
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


def validate_repo(root: Path = ROOT) -> tuple[list[str], list[str]]:
    names, failures = validate_agents(root)
    failures.extend(validate_scribe_bundle(root))
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
