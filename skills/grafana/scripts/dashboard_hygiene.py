#!/usr/bin/env python3
"""Dashboard hygiene checker — the mechanically checkable subset of this skill's panel rules.

Offline, with a stdlib-only fallback. Uses bounded PromQL AST inspection when promql-parser is
installed and the expression contains no unresolved Grafana variables. Otherwise textual checks
retain explicit query_analysis gaps; values are never guessed or substituted. No findings means
no implemented rule fired, not that the dashboard is correct. PromQL checks run only for a model
reference whose type is `prometheus`; other or untyped references need their dialect's query
validation. Findings need human review:
fixed UIDs can be intentional in provisioned dashboards, and a `_total` suffix is not type evidence.
Prefer dashboard-linter where installed for real query/schema validation; this helper is the
portable fallback for Classic/V1 models.

Which model shapes it accepts:
  * Classic / V1 `spec`  — the `panels[]` + `templating.list[]` shape
  * an app-platform wrapper — `{apiVersion, kind, metadata, spec}`; the `spec` is unwrapped
  * V2 (`elements`/`layout`) is DETECTED AND REFUSED rather than half-checked: its panels live in a
    different structure, and silently checking zero panels would be worse than saying so.

Exit codes: 0 no review-required findings (advisories may remain), 1 review required,
2 the input could not be checked. Findings are heuristics, not proven defects.
Use --format json for one ASCII-escaped JSON report on stdout, including input errors.
The report's ok means checked, not finding-free; coverage is static_hygiene_only.
--quiet affects text only: JSON always includes every finding. CLI usage errors remain argparse text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from runpy import run_path
from typing import NamedTuple

_module = run_path(str(Path(__file__).with_name("grafana_modules.py")))["load_module"]
promql = _module("grafana_promql")

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
# A datasource reference that is a literal uid rather than a variable.
BUILTIN_DS = frozenset({"-- Grafana --", "-- Mixed --", "-- Dashboard --", "grafana"})
ADVISORY_RULES = frozenset({
    "panel-title", "panel-description", "panel-units", "panel-no-value",
    "panel-datasource", "dashboard-tags", "template-all-value",
})


class InputShapeError(ValueError):
    """The checker cannot traverse this input; it has not assessed its hygiene."""


class Finding(NamedTuple):
    """One heuristic finding; preserve three-field unpacking for existing callers."""

    rule: str
    where: str
    detail: str

    @property
    def severity(self) -> str:
        return "advisory" if self.rule in ADVISORY_RULES else "review"

    def as_report(self) -> dict[str, str]:
        return {**self._asdict(), "severity": self.severity}


def require_shape(value, expected, where, *, nullable=False):
    if nullable and value is None:
        return
    if not isinstance(value, expected):
        kind = {dict: "an object", list: "an array", str: "a string"}[expected]
        raise InputShapeError(f"{where} must be {kind}")


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
    """Validate traversed shapes and return their non-row panels in traversal order.

    Optional null containers retain their existing empty interpretation. Datasource type guards
    and opaque plugin query/config values keep their existing behavior.
    """
    panels = []
    for location, panel in walk_panels(spec.get("panels"), f"{root_path}.panels"):
        panels.append(panel)
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
    return panels


def rate_call_spans(expr):
    """[(function, start, end)] for each rate/irate/increase call, end just past its closing paren.

    Span-based, because both rules that use it are per-call and the string-level shortcuts are
    wrong in opposite directions:

    * "does the expression contain $__rate_interval anywhere" passes
      `rate(a_total[$__rate_interval]) + rate(b_total[5m])`, whose second call is exactly what the
      rule should flag for review;
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


def panel_findings(panel: dict, where: str):
    """Suggest presentation checks and flag missing targets for review."""
    defaults = (panel.get("fieldConfig") or {}).get("defaults") or {}
    ptype = panel.get("type")
    querying = ptype not in NON_QUERYING

    if not (panel.get("title") or "").strip():
        yield Finding("panel-title", where, "no title; consider whether the panel needs a visible label")
    if not (panel.get("description") or "").strip():
        yield Finding("panel-description", where, "no description; add a tooltip if interpretation needs context")
    if ptype in UNIT_BEARING and not defaults.get("unit"):
        yield Finding("panel-units", where,
                      f"{ptype} panel has no default unit; inspect field overrides and rendered units")
    if querying and not (panel.get("targets") or []):
        yield Finding("panel-no-targets", where, "panel has no targets; review its data source and intended behavior")
    if querying and "noValue" not in defaults:
        yield Finding("panel-no-value", where,
                      "no default 'No value' text; inspect rendered empty-data behavior before changing it")


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
                          f"{scope} names a literal data-source uid {uid!r}; verify its binding "
                          f"if cross-instance portability is required")


def _counter_finding(name, location):
    return Finding("target-counter-agg", location,
                   f"counter-like name {name!r} is outside rate/irate/increase; "
                   f"verify metric type and intent (presence, counts, resets, and lifetime "
                   f"totals can legitimately read it directly)")


def _rate_finding(call, location):
    return Finding("target-rate-interval", location,
                   f"{call[:60]!r} uses a fixed or non-rate window; review the intended "
                   f"horizon and scrape cadence before choosing $__rate_interval")


def _text_query_findings(expr, location):
    """Portable checks for templates, unavailable parsing, or unsupported syntax."""
    query_code = promql.code_only(expr)
    spans = rate_call_spans(query_code)
    for function, start, end in spans:
        windows = RANGE_SELECTOR.findall(query_code[start:end])
        selected_total = (function == "increase"
                          and windows and all(w.strip() == "$__range" for w in windows))
        if windows and not selected_total and not any("$__rate_interval" in w for w in windows):
            yield _rate_finding(expr[start:end], location)
    for match in COUNTER_NAME.finditer(query_code):
        if not any(start <= match.start() < end for _, start, end in spans):
            yield _counter_finding(match.group(1), location)
            break


def _query_analysis(expr):
    """Choose AST inspection or an explicit fallback without resolving variables."""
    if limit := promql.input_limit(expr):
        return None, "not_checked", [limit]
    if promql.VARIABLE.search(expr):
        return None, "text_heuristic", ["promql_template_unresolved"]
    try:
        analysis = promql.analyze(expr)
    except (ImportError, OSError):
        return None, "text_heuristic", ["dependency_unavailable_promql_parser"]
    if analysis.ast_complete:
        return analysis, "promql_ast", list(analysis.gaps)
    return None, "not_checked" if analysis.truncated else "text_heuristic", list(analysis.gaps)


def query_findings(panel: dict, where: str, *, query_analysis=None):
    """Inspect targets whose effective datasource reference is typed `prometheus`."""
    for target in panel.get("targets") or []:
        datasource = target.get("datasource") or panel.get("datasource") or {}
        if not isinstance(datasource, dict) or datasource.get("type") != "prometheus":
            continue
        expr = target.get("expr") or target.get("query") or ""
        if not isinstance(expr, str) or not expr:
            continue
        location = f"{where} [{target.get('refId', '?')}]"
        analysis, mode, gaps = _query_analysis(expr)
        if query_analysis is not None:
            query_analysis.append({"location": location, "mode": mode, "gaps": gaps})
        if analysis is not None:
            for call in analysis.rate_calls:
                yield _rate_finding(call, location)
            if analysis.unrated_counters:
                yield _counter_finding(analysis.unrated_counters[0], location)
        elif mode == "text_heuristic":
            yield from _text_query_findings(expr, location)


def template_findings(spec: dict):
    for variable in (spec.get("templating") or {}).get("list") or []:
        if variable.get("includeAll") and not (variable.get("allValue") or "").strip():
            yield Finding("template-all-value", f"${variable.get('name', '?')}",
                          "'Include All' has no custom all value; inspect expansion size and query "
                          "semantics before choosing a dialect-appropriate value")


def tag_findings(spec: dict):
    # Tags support discovery regardless of whether the dashboard is provisioned or UI-managed.
    if not (spec.get("tags") or []):
        yield Finding("dashboard-tags", "dashboard", "no tags; add them only if useful for discovery or required by local policy")


def check(spec: dict, *, query_analysis=None) -> list[Finding]:
    """Return heuristic Findings, panel by panel, then dashboard-wide.

    Run validate_shape() first: the shared walk checks only the shapes it traverses, not the fields
    inside a panel (title, fieldConfig, targets) or the templating list.
    """
    return _check_panels(spec, (panel for _, panel in walk_panels(spec.get("panels"), "$.panels")),
                         query_analysis=query_analysis)


def _check_panels(spec, panels, *, query_analysis=None):
    findings: list[Finding] = []
    for panel in panels:
        where = (panel.get("title") or "").strip() or f"panel id={panel.get('id')}"
        for rules in (panel_findings, datasource_findings):
            findings.extend(rules(panel, where))
        findings.extend(query_findings(panel, where, query_analysis=query_analysis))
    findings.extend(template_findings(spec))
    findings.extend(tag_findings(spec))
    return findings


def print_json_report(*, title=None, panel_count=None, findings=(), errors=(), query_analysis=()):
    """Emit the same envelope for a completed check or a refusal, without mixing prose into stdout."""
    print(json.dumps({
        "ok": not errors,
        "coverage": "static_hygiene_only",
        "title": title if isinstance(title, str) else None,
        "panel_count": panel_count,
        "findings": [finding.as_report() for finding in findings],
        "query_analysis": list(query_analysis),
        "errors": list(errors),
    }, ensure_ascii=True))


def main(argv: list[str] | None = None) -> int:
    # The report echoes dashboard and panel titles; captured stdout (an agent's Bash, CI, `> log`)
    # may default to a legacy code page that cannot encode them; exit 1 must mean review findings.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="dashboard JSON: a bare model, a k8s wrapper, or a legacy GET body")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="report format (default: text)")
    parser.add_argument("--quiet", action="store_true", help="print only the text summary; JSON keeps all findings")
    args = parser.parse_args(argv)

    def cannot_check(code, detail):
        if args.format == "json":
            print_json_report(errors=[{"code": code, "detail": detail}])
        else:
            print(detail, file=sys.stderr)
        return 2

    try:
        with open(args.path, encoding="utf-8") as handle:
            model = json.load(handle)
    except (OSError, ValueError, RecursionError) as exc:  # deep nesting overflows the JSON decoder
        code = ("input_read_error" if isinstance(exc, OSError) else
                "input_too_deep" if isinstance(exc, RecursionError) else "invalid_json")
        return cannot_check(code, f"cannot check {args.path}: {exc}")

    try:
        spec, root_path = locate_spec(model)
        if "elements" in spec or "layout" in spec:
            return cannot_check(
                "unsupported_v2",
                "refusing to check a V2 (dynamic) dashboard: its panels live under spec.elements, which "
                "this checker does not read. Validate the actual V2 candidate with a V2-capable linter "
                "(dashboard-linter v0.2.0+), or report the validation gap; keep its stored version.",
            )
        if "panels" not in spec:
            return cannot_check("unsupported_model", "no `panels` key: this does not look like a Classic/V1 dashboard model")
        panels = validate_shape(spec, root_path)
        query_analysis = []
        findings = _check_panels(spec, panels, query_analysis=query_analysis)
        panel_count = len(panels)
    except (InputShapeError, RecursionError) as exc:  # rows nested past the recursion limit overflow the walk
        code = "input_too_deep" if isinstance(exc, RecursionError) else "invalid_shape"
        return cannot_check(code, f"cannot check {args.path}: {exc}")

    title = spec.get("title", "<untitled>")
    review_count = sum(finding.severity == "review" for finding in findings)
    if args.format == "json":
        print_json_report(title=title, panel_count=panel_count, findings=findings,
                          query_analysis=query_analysis)
        return 1 if review_count else 0
    if not args.quiet:
        for finding in findings:
            print(f"{finding.rule} [{finding.severity}]: {finding.where}\n    {finding.detail}")
        if findings:
            print()
    print(f"{title!r}: {review_count} review-required, {len(findings) - review_count} advisory "
          f"finding(s) across {panel_count} panel(s)")
    return 1 if review_count else 0


if __name__ == "__main__":
    sys.exit(main())
