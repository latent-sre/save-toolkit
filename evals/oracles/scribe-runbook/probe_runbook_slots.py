"""Probe-owned oracle for a runbook written with the runbook skill's template.

Usage: python probe_runbook_slots.py <runbook.md> <alert-name> <rule>
Exit 0 when the rule holds, 1 with a reason when it does not. The rules are the skill's own
authoring rules, made mechanical: the shape the template requires with every slot filled or marked
`n/a — why` and no unfinished marker; frontmatter that parses as YAML, in the import-safe initial
state with every value filled and typed; an expected-output line under every procedure step with at
least two routed outcome branches; a source in the sentence that mentions each placeholder, upper-
or lowercase; a bound and a route in the outcome lines of every fallible step (any command, any
wait); a rollback entry per state change, bound to the step by number and carrying an undo command
or an explicit disposition, plus a safe-abort that says something; an escalation row that is timed
and reachable on the same row; a triage tree of conditional branches; an evidence label in every
step that runs a command; and none of the template's placeholders left behind.
"""
import re
import sys

SLOTS = ("Purpose & scope", "Trigger", "Prerequisites", "Triage", "Procedure", "Verification",
         "Rollback", "Escalation", "Communication", "Post-Incident", "Incident history", "References")
FRONTMATTER_KEYS = ("schema_version", "runbook_id", "service_id", "status", "alert_names", "owner",
                    "severity", "source_revision", "last_reviewed", "last_verified",
                    "verification_evidence", "version")
STRING_KEYS = ("runbook_id", "service_id", "owner", "severity", "source_revision")
# Every placeholder the template carries (assets/runbook-template.md), so a copied slot left
# unfilled is caught whichever one it is. evals/test_build_probe.py holds this list to the template.
TEMPLATE_LITERALS = (
    "<Apps Manager view, Splunk search, or Wavefront chart>",
    "<Apps Manager, Splunk, Wavefront or PCF App Metrics; cf CLI v8 only if installed>",
    "<N min or N attempts>", "<P1|P2|P3|P4 / page | ticket>", "<PR, evidence link, prepared, or proposed>",
    "<PR, target revision, and evidence references>", "<YYYY-MM-DD>",
    "<alert name + condition, or observed symptom>", "<channel / stakeholders>",
    "<command/dashboard + expected healthy state>", "<command>", "<concise title / the alert this answers>",
    "<condition A>", "<condition B>", "<dashboard, saved search, prior postmortem>",
    "<e.g. not resolved in 15 min, or blast radius growing>",
    "<e.g. step 4 output differed; no rollback for step 5>", "<e.g. steps 1–3>", "<exact steps>",
    "<how to stop mid-procedure without making it worse>", "<imperative step>", "<link>", "<n>",
    "<next step>", "<other runbook>", "<pager / channel>",
    "<platform-side signal: many apps / failing cells>", "<postmortem or drill link>",
    "<repository@full-sha or reviewed release identifier>", "<role/team>", "<role>",
    "<roles, Apps Manager org/space, VPN, tools>", "<stable-runbook-slug>", "<stable-service-slug>",
    "<team/role>", "<the incident's agreed update interval>", "<the step or escalation row to go to>",
    "<what you should see>", "<…>",
)
# Verbs that change state in the platforms the fleet operates: cf, kubectl, helm, terraform, gcloud,
# shells, and SQL. A read verb (get, describe, logs, app, apps, events, top, curl) is not here.
STATE_CHANGE = re.compile(
    r"\b(restart|restage|rollout|rollback|scale|delete|truncate|kill|drain|cordon|uncordon|taint|evict|"
    r"failover|apply|patch|push|deploy(?!/)|upgrade|install|uninstall|destroy|create|replace|edit|"
    r"set\s+(?:image|env|resources)|unset-env|stop|start|reset|rotate|purge|migrate|bind|unbind|"
    r"map-route|unmap-route|rename|restore|rm|drop|alter|update|insert|write|chmod|chown|mv|"
    r"kubectl\s+exec\b[^\n]*\b(?:rm|kill|sh|bash)\b)\b", re.I)
BOUND = re.compile(r"\b\d+\s*(?:s|sec|seconds?|m|min|minutes?|h|hours?|times|attempts?|retries)\b", re.I)
ROUTE = re.compile(r"(→|->|go to|escalate|stop here|this runbook ends|switch to|see `)", re.I)
BRANCH = re.compile(r"^\s*[-*]\s.*(→|->|go to|escalate|stop here|this runbook ends|switch to)", re.I | re.M)
SOURCE = re.compile(r"\b(from step|from triage|printed by|output of|the row|the table|field|panel|shows|"
                    r"lists|returned by|value from|take it from|comes from|found in|listed by|in step)\b", re.I)
PLACEHOLDER = re.compile(r"<[A-Za-z][A-Za-z0-9_-]*>")
LABEL = re.compile(r"\[(verified|sourced|unverified)")
NA = re.compile(r"\bn/a\s*[—-]", re.I)
DISPOSITION = re.compile(r"(nothing to undo|no rollback|one-way|irreversible|cannot be undone|is the reset|"
                         r"return to|revert|restore|scale (?:it )?back|roll back|undo)", re.I)
UNFILLED = re.compile(r"\b(TBD|TODO|TBC|FIXME)\b|\?\?\?")
OUTPUT_FENCE = re.compile(r"^(json|yaml|yml|text|txt|output|log|logs|plain|console-output)$", re.I)


def section(text: str, name: str) -> str:
    """The body of the H2 section whose heading starts with `name`, or ''."""
    m = re.search(r"^## " + re.escape(name) + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def steps(body: str) -> list[str]:
    """Numbered steps of a section, each with its indented continuation lines."""
    parts = re.split(r"^(?=\d+\.\s)", body, flags=re.M)
    return [p for p in parts if re.match(r"\d+\.\s", p)]


def commands(step: str) -> str:
    """The fenced command blocks of a step: fences before its Expected line whose language tag is
    not an output format, so shown output and prose like "do not restart" are not commands."""
    before = re.split(r"expected\s*:", step, maxsplit=1, flags=re.I)[0]
    blocks = re.findall(r"```([^\n]*)\n(.*?)```", before, re.S)
    return "\n".join(body for tag, body in blocks if not OUTPUT_FENCE.match(tag.strip()))


def prose(step: str) -> str:
    """A step with its fenced blocks removed."""
    return re.sub(r"```.*?```", " ", step, flags=re.S)


def outcome_lines(step: str) -> str:
    """The Expected line and the outcome branches after it: where routing and bounds have to live."""
    m = re.search(r"expected\s*:.*", step, re.I | re.S)
    return m.group(0) if m else ""


def entries(body: str) -> list[str]:
    """Top-level bullets of a section, each with its continuation lines."""
    parts = re.split(r"^(?=[-*]\s)", body, flags=re.M)
    return [p for p in parts if re.match(r"[-*]\s", p)]


def title(step: str) -> str:
    return step.split("\n", 1)[0][:60]


def rule_frontmatter(text: str, alert: str) -> str | None:
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return "no frontmatter block"
    try:
        import yaml
    except ImportError:
        return "PyYAML is not importable here, so the frontmatter cannot be parsed"
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return f"frontmatter is not valid YAML: {str(exc).splitlines()[0]}"
    if not isinstance(fm, dict):
        return "frontmatter is not a mapping"
    missing = [k for k in FRONTMATTER_KEYS if k not in fm]
    if missing:
        return "frontmatter missing " + ", ".join(missing)
    if not isinstance(fm["schema_version"], int):
        return f"schema_version is {fm['schema_version']!r}, not an integer"
    bad = [k for k in STRING_KEYS if not isinstance(fm[k], str) or not fm[k].strip()]
    if bad:
        return "frontmatter values that are not a non-empty string: " + ", ".join(bad)
    if fm["status"] != "draft":
        return f"status is {fm['status']!r}; a new runbook starts draft"
    names = fm["alert_names"]
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        return "alert_names is not a list of strings"
    if alert not in names:
        return f"alert_names does not name {alert}"
    for key in ("last_reviewed", "last_verified"):
        if fm[key] is not None:
            return f"{key} is {fm[key]!r}; it starts null until a human review or bound rehearsal"
    if not isinstance(fm["verification_evidence"], list):
        return "verification_evidence is not a list"
    version = fm["version"]
    if not (isinstance(version, int) or (isinstance(version, str) and version.strip())):
        return f"version is {version!r}"
    return None


def rule_slots(text: str, alert: str) -> str | None:
    missing = [s for s in SLOTS if not re.search(r"^## " + re.escape(s), text, re.M)]
    if missing:
        return "missing sections: " + ", ".join(missing)
    empty, unfinished = [], []
    for s in SLOTS:
        body = section(text, s)
        lines = [l for l in body.splitlines() if l.strip() and not l.strip().startswith(">")]
        if not lines or (len(lines) == 1 and re.fullmatch(r"\W*n/a\W*", lines[0], re.I) and not NA.search(lines[0])):
            empty.append(s)
        elif UNFILLED.search(body) and not NA.search(body):
            unfinished.append(s)
    if empty:
        return "sections with no body and no `n/a — why`: " + ", ".join(empty)
    return ("sections left unfinished (TBD, TODO, ???): " + ", ".join(unfinished)) if unfinished else None


def rule_expected_per_step(text: str, alert: str) -> str | None:
    procedure = steps(section(text, "Procedure"))
    if not procedure:
        return "no numbered procedure steps"
    bare = [title(s) for s in procedure if not re.search(r"expected\s*:", s, re.I)]
    return ("procedure steps without an Expected line: " + " | ".join(bare)) if bare else None


def rule_expected_distinguishes(text: str, alert: str) -> str | None:
    """An expected line sorts its outcomes: at least two routed branches follow it, so a bare
    success line with a single failure route does not pass for worked / partly worked / failed."""
    procedure = steps(section(text, "Procedure"))
    if not procedure:
        return "no numbered procedure steps"
    thin = [title(s) for s in procedure if len(BRANCH.findall(outcome_lines(s))) < 2]
    return ("procedure steps whose expected line has fewer than two routed outcome branches: "
            + " | ".join(thin)) if thin else None


def rule_placeholders_sourced(text: str, alert: str) -> str | None:
    """Each placeholder is sourced in a sentence that mentions it, not by a source-like word
    anywhere in the step."""
    body = section(text, "Triage") + section(text, "Procedure")
    unsourced = []
    for s in steps(body):
        for ph in sorted(set(PLACEHOLDER.findall(s))):
            mentions = re.findall(r"[^.\n]*" + re.escape(ph) + r"[^.\n]*", prose(s))
            if not any(SOURCE.search(m) for m in mentions):
                unsourced.append(f"{ph} in {title(s)!r}")
    return ("placeholders with no source in their own sentence: " + " | ".join(unsourced)) if unsourced else None


def rule_stop_conditions(text: str, alert: str) -> str | None:
    """Any step that runs a command or waits can fail; its outcome lines say how long, and where
    to go. A duration inside the command (a log lookback) does not count."""
    unbounded = []
    for s in steps(section(text, "Procedure")):
        fallible = bool(commands(s).strip()) or re.search(r"\bwait\b", prose(s), re.I)
        outcome = outcome_lines(s)
        if fallible and not (BOUND.search(outcome) and ROUTE.search(outcome)):
            unbounded.append(title(s))
    return ("fallible steps whose outcome lines carry no bound and route: " + " | ".join(unbounded)) if unbounded else None


def rule_rollback_per_change(text: str, alert: str) -> str | None:
    """Each state change is bound to its own rollback entry by step number, and the entry says
    how to undo it or states that it cannot be; the safe-abort says something too."""
    rollback = section(text, "Rollback")
    if not rollback.strip():
        return "no Rollback / cleanup section body"
    items = entries(rollback)
    abort = [e for e in items if re.match(r"[-*]\s*\**safe-abort", e, re.I)]
    if not abort:
        return "no Safe-abort entry"
    abort_text = re.sub(r"^[-*]\s*\**safe-abort\**\s*:?", "", abort[0], flags=re.I).strip()
    if len(abort_text.split()) < 6 or UNFILLED.search(abort_text):
        return "the Safe-abort entry does not say how to stop without making it worse"
    problems = []
    for s in steps(section(text, "Procedure")):
        verb = STATE_CHANGE.search(commands(s))
        if not verb:
            continue
        number = re.match(r"(\d+)\.", s).group(1)
        entry = [e for e in items if re.search(rf"\bstep\s*{number}\b", e.split("\n", 1)[0], re.I)]
        if not entry:
            problems.append(f"step {number} ({verb.group(1)}): no rollback entry names it")
        elif UNFILLED.search(entry[0]) or not (commands(entry[0]).strip() or DISPOSITION.search(entry[0])):
            problems.append(f"step {number} ({verb.group(1)}): its entry has no undo command and no disposition")
    return ("rollback: " + "; ".join(problems)) if problems else None


def rule_escalation_reachable(text: str, alert: str) -> str | None:
    esc = section(text, "Escalation")
    rows = [l for l in esc.splitlines() if l.startswith("|") and not re.match(r"\|\s*-", l) and "When" not in l]
    if not rows:
        return "no escalation rows"
    both = [r for r in rows if BOUND.search(r) and re.search(r"#[a-z0-9-]+|pager|page\b|on-?call", r, re.I)]
    return None if both else "no escalation row is both time-boxed and names a pager or channel"


def rule_triage_routes(text: str, alert: str) -> str | None:
    """A decision tree is conditional branches that route, not route phrases in prose."""
    branches = len(BRANCH.findall(section(text, "Triage")))
    return None if branches >= 2 else f"triage has {branches} routed branch(es); a decision tree needs at least two"


def rule_evidence_labels(text: str, alert: str) -> str | None:
    """Every step that runs a command carries a label saying what stands behind that command."""
    body = section(text, "Triage") + section(text, "Procedure")
    unlabeled = [title(s) for s in steps(body) if commands(s).strip() and not LABEL.search(s)]
    if not LABEL.search(text):
        return "no evidence label anywhere"
    return ("command steps with no evidence label: " + " | ".join(unlabeled)) if unlabeled else None


def rule_no_template_literals(text: str, alert: str) -> str | None:
    left = [t for t in TEMPLATE_LITERALS if t in text]
    return ("template placeholders left in: " + ", ".join(left)) if left else None


RULES = {name[5:].replace("_", "-"): fn for name, fn in globals().items() if name.startswith("rule_")}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path, alert, rule = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        print(f"FAIL {rule}: cannot read {path}: {exc}")
        return 1
    if rule not in RULES:
        print(f"FAIL {rule}: unknown rule; known: {', '.join(sorted(RULES))}")
        return 1
    problem = RULES[rule](text, alert)
    print(f"{'PASS' if problem is None else 'FAIL'} {rule}" + (f": {problem}" if problem else ""))
    return 0 if problem is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
