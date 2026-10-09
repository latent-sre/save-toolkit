#!/usr/bin/env python3
"""Dashboard hygiene checker — the mechanically checkable subset of this skill's panel rules.

Pure stdlib and offline. Checks textual properties only: no query parsing, datasource resolution,
or Grafana access. A clean result means no implemented rule fired, not that the dashboard is correct.
PromQL heuristics run only for a resolved model reference whose type is `prometheus`; other or
untyped datasource references need their dialect's query validation. Findings need human review:
fixed UIDs can be intentional in provisioned dashboards, and a `_total` suffix is not type evidence.
Prefer dashboard-linter where installed for real query/schema validation; this helper is the
portable fallback for Classic/V1 models.

Which model shapes it accepts:
  * Classic / V1 `spec`  — the `panels[]` + `templating.list[]` shape
  * an app-platform wrapper — `{apiVersion, kind, metadata, spec}`; the `spec` is unwrapped
  * V2 (`elements`/`layout`) is DETECTED AND REFUSED rather than half-checked: its panels live in a
    different structure, and silently checking zero panels would be worse than saying so.

Exit codes: 0 clean, 1 violations found, 2 the input could not be checked.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import NamedTuple

# Panel types for which a unit is meaningful. A `text` or `row` panel has no unit, and flagging one
# would train people to ignore the checker.
UNIT_BEARING = frozenset({"timeseries", "stat", "gauge", "bargauge", "table", "barchart", "trend"})
# Panels that render without querying. Demanding a target or a "no value" string from these reports
# the very documentation panel this skill tells you to add, which trains people to ignore the
# checker as surely as a false unit warning would.
NON_QUERYING = frozenset({"text", "dashlist", "news", "welcome", "alertlist"})
# Range-vector functions whose window must adapt to the panel's resolution.
RATE_FUNCS = re.compile(r"\b(rate|irate|increase)\s*\(")
COUNTER_NAME = re.compile(r"\b(\w+_total)\b")
RANGE_SELECTOR = re.compile(r"\[([^\]]*)\]")
# Ignore string contents without shifting spans; regex label values may contain brackets,
# parentheses, counter-like names, or text resembling functions and Grafana macros.
QUOTED_STRING = re.compile(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`[^`]*`''')
# A datasource reference that is a literal uid rather than a variable.
BUILTIN_DS = frozenset({"-- Grafana --", "-- Mixed --", "-- Dashboard --", "grafana"})


class InputShapeError(ValueError):
    """The checker cannot traverse this input; this is not a hygiene violation."""


class Finding(NamedTuple):
    """One violation. Still a plain (rule, where, detail) tuple for callers that unpack it."""

    rule: str
    where: str
    detail: str


def require_shape(value, expected, where, *, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, expected):
        kind = {dict: "object", list: "array", str: "string"}[expected]
        raise InputShapeError(f"{where} must be an {kind}" if kind in {"object", "array"}
                              else f"{where} must be a {kind}")


def walk_panels(items, where):
    """Yield (location, panel) for every non-row panel, descending into collapsed rows.

    The one row descent: it checks the shapes it traverses itself (each container, panel object and
    type), so neither validation nor checking can walk a panel the other would read differently.
    """
    require_shape(items, list, where, nullable=True)
    for index, panel in enumerate(items or []):
        location = f"{where}[{index}]"
        require_shape(panel, dict, location)
        require_shape(panel.get("type"), str, f"{location}.type", nullable=True)
        if panel.get("type") == "row":
            yield from walk_panels(panel.get("panels"), f"{location}.panels")
        else:
            yield location, panel


def validate_shape(spec: dict, root_path="$"):
    """Check only containers/text the helper traverses, not Grafana's full schema.

    Optional null containers retain their existing empty interpretation. Datasource type guards
    and opaque plugin query/config values keep their existing behavior.
    """
    for location, panel in walk_panels(spec.get("panels"), f"{root_path}.panels"):
        for key in ("title", "description"):
            require_shape(panel.get(key), str, f"{location}.{key}", nullable=True)
        fields = panel.get("fieldConfig")
        require_shape(fields, dict, f"{location}.fieldConfig", nullable=True)
        require_shape((fields or {}).get("defaults"), dict, f"{location}.fieldConfig.defaults", nullable=True)
        targets = panel.get("targets")
        require_shape(targets, list, f"{location}.targets", nullable=True)
        for index, target in enumerate(targets or []):
            require_shape(target, dict, f"{location}.targets[{index}]")

    templating = spec.get("templating")
    require_shape(templating, dict, f"{root_path}.templating", nullable=True)
    variables = (templating or {}).get("list")
    require_shape(variables, list, f"{root_path}.templating.list", nullable=True)
    for index, variable in enumerate(variables or []):
        location = f"{root_path}.templating.list[{index}]"
        require_shape(variable, dict, location)
        if variable.get("includeAll"):
            require_shape(variable.get("allValue"), str, f"{location}.allValue", nullable=True)


def rate_call_spans(expr):
    """[(function, start, end)] for each rate/irate/increase call, end just past its closing paren.

    Span-based, because both rules that use it are per-call and the string-level shortcuts are
    wrong in opposite directions:

    * "does the expression contain $__rate_interval anywhere" passes
      `rate(a_total[$__rate_interval]) + rate(b_total[5m])`, whose second call is exactly what the
      rule exists to reject;
    * "count parentheses before the metric" decides `sum(rate(a[$__rate_interval])) / sum(b_total)`
      has `b_total` inside a rate call, because it cannot see that the earlier call already closed.
    """
    spans = []
    for match in RATE_FUNCS.finditer(expr):
        depth = 0
        index = match.end() - 1  # the opening paren
        while index < len(expr):
            if expr[index] == "(":
                depth += 1
            elif expr[index] == ")":
                depth -= 1
                if depth == 0:
                    spans.append((match.group(1), match.start(), index + 1))
                    break
            index += 1
        else:
            # Unbalanced input: treat the remainder as the call rather than dropping it, so a
            # malformed query is still inspected instead of silently passing.
            spans.append((match.group(1), match.start(), len(expr)))
    return spans


def locate_spec(model: dict) -> tuple[dict, str]:
    """Return the dashboard spec and its JSON path, for a bare model, a k8s wrapper or a legacy GET."""
    require_shape(model, dict, "$")
    if "spec" in model and "apiVersion" in model:
        require_shape(model["spec"], dict, "$.spec")
        return model["spec"], "$.spec"
    # a legacy GET returns {dashboard, meta}
    if "dashboard" in model and "meta" in model:
        require_shape(model["dashboard"], dict, "$.dashboard")
        return model["dashboard"], "$.dashboard"
    return model, "$"


def unwrap(model: dict) -> dict:
    """Return the dashboard spec whether the caller passed a bare model or a k8s wrapper."""
    return locate_spec(model)[0]


def iter_panels(spec: dict):
    """Yield every non-row panel, descending into collapsed rows; untraversable shapes raise."""
    for _location, panel in walk_panels(spec.get("panels"), "$.panels"):
        yield panel


def panel_findings(panel: dict, where: str):
    """What a reader needs to interpret the panel: a title, a description, a unit, and for a
    querying panel a query and a "No value" text."""
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    ptype = panel.get("type")
    querying = ptype not in NON_QUERYING

    if not (panel.get("title") or "").strip():
        yield Finding("panel-title", where, "panel has no title; a title states the question it answers")
    if not (panel.get("description") or "").strip():
        yield Finding("panel-description", where, "no description; it renders as the panel's tooltip")
    if ptype in UNIT_BEARING and not defaults.get("unit"):
        yield Finding("panel-units", where, f"{ptype} panel has no unit set")
    if querying and not (panel.get("targets") or []):
        yield Finding("panel-no-targets", where, "panel has no query")
    if querying and "noValue" not in defaults:
        yield Finding("panel-no-value", where, "no 'No value' text; an empty panel must not read as healthy")


def datasource_findings(panel: dict, where: str):
    """Portability is decided per datasource reference, and a target may override the panel's.

    Checking only the panel level passes a dashboard whose panel says ${datasource} while one
    target names a uid -- Grafana uses the target's, so the model breaks on another instance.
    """
    references = [("panel", panel.get("datasource"))]
    references += [(f"target {target.get('refId', '?')}", target.get("datasource"))
                   for target in panel.get("targets") or []]
    for scope, datasource in references:
        if not isinstance(datasource, dict):
            continue
        uid = datasource.get("uid")
        if isinstance(uid, str) and not uid.startswith("$") and uid not in BUILTIN_DS:
            yield Finding("panel-datasource", where,
                          f"{scope} names a hard-coded data-source uid {uid!r}; use a datasource "
                          f"variable so the model is portable")


def query_findings(panel: dict, where: str):
    """PromQL heuristics, for targets whose effective datasource reference is typed `prometheus`."""
    for target in panel.get("targets") or []:
        datasource = target.get("datasource") or panel.get("datasource") or {}
        if not isinstance(datasource, dict) or datasource.get("type") != "prometheus":
            continue
        expr = target.get("expr") or target.get("query") or ""
        if not isinstance(expr, str) or not expr:
            continue
        location = f"{where} [{target.get('refId', '?')}]"
        query_code = QUOTED_STRING.sub(lambda match: " " * len(match.group()), expr)
        spans = rate_call_spans(query_code)
        for function, start, end in spans:
            windows = RANGE_SELECTOR.findall(query_code[start:end])
            selected_total = (function == "increase"
                              and windows and all(w.strip() == "$__range" for w in windows))
            if windows and not selected_total and not any("$__rate_interval" in w for w in windows):
                yield Finding("target-rate-interval", location,
                              f"{expr[start:end][:60]!r} uses a fixed or non-rate window; review the intended "
                              f"horizon and scrape cadence before choosing $__rate_interval")
        for match in COUNTER_NAME.finditer(query_code):
            if not any(start <= match.start() < end for _, start, end in spans):
                yield Finding("target-counter-agg", location,
                              f"counter-like name {match.group(1)!r} is outside rate/irate/increase; "
                              f"verify metric type and intent (presence, counts, resets, and lifetime "
                              f"totals can legitimately read it directly)")
                break


def template_findings(spec: dict):
    for variable in (spec.get("templating") or {}).get("list") or []:
        if variable.get("includeAll") and not (variable.get("allValue") or "").strip():
            yield Finding("template-all-value", f"${variable.get('name', '?')}",
                          "'Include All' with no custom all value; the expanded expression can grow "
                          "unbounded — set one such as '.+'")


def tag_findings(spec: dict):
    # Tags support discovery regardless of whether the dashboard is provisioned or UI-managed.
    if not (spec.get("tags") or []):
        yield Finding("dashboard-tags", "dashboard", "no tags; search and the dashboard list rely on them")


def check(spec: dict) -> list[Finding]:
    """Return a Finding (rule, where, detail) for every violation, panel by panel, then dashboard-wide."""
    findings: list[Finding] = []
    for panel in iter_panels(spec):
        where = (panel.get("title") or "").strip() or f"panel id={panel.get('id')}"
        for rules in (panel_findings, datasource_findings, query_findings):
            findings.extend(rules(panel, where))
    findings.extend(template_findings(spec))
    findings.extend(tag_findings(spec))
    return findings


def main(argv: list[str] | None = None) -> int:
    # The report echoes dashboard and panel titles; captured stdout (an agent's Bash, CI, `> log`)
    # may default to a legacy code page that cannot encode them, and exit 1 must mean violations.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="dashboard JSON: a bare model, a k8s wrapper, or a legacy GET body")
    parser.add_argument("--quiet", action="store_true", help="print only the summary line")
    args = parser.parse_args(argv)

    try:
        with open(args.path, encoding="utf-8") as handle:
            model = json.load(handle)
    except (OSError, ValueError, RecursionError) as exc:  # deep nesting overflows the JSON decoder
        print(f"cannot check {args.path}: {exc}", file=sys.stderr)
        return 2

    try:
        spec, root_path = locate_spec(model)
        if "elements" in spec or "layout" in spec:
            print("refusing to check a V2 (dynamic) dashboard: its panels live under spec.elements, which "
                  "this checker does not read. Validate the actual V2 candidate with a V2-capable linter "
                  "(dashboard-linter v0.2.0+), or report the validation gap; keep its stored version.", file=sys.stderr)
            return 2
        if "panels" not in spec:
            print("no `panels` key: this does not look like a Classic/V1 dashboard model", file=sys.stderr)
            return 2
        validate_shape(spec, root_path)
    except InputShapeError as exc:
        print(f"cannot check {args.path}: {exc}", file=sys.stderr)
        return 2

    violations = check(spec)
    panel_count = sum(1 for _ in iter_panels(spec))
    if not args.quiet:
        for rule, where, detail in violations:
            print(f"{rule}: {where}\n    {detail}")
        if violations:
            print()
    title = spec.get("title", "<untitled>")
    print(f"{title!r}: {len(violations)} violation(s) across {panel_count} panel(s)")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
