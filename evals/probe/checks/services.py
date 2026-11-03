"""Probes of a backing service through its audit proxy and final state, including Grafana writes."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any, TypeGuard

from .. import backing
from ..backing import Service, ServiceUnavailable
from ..outcomes import Outcome, Polarity, instrument, verdict
from . import registry
from .registry import Context, Need, Params


def _successful_status(status: object) -> bool:
    """A recorded 2xx status. The audit proxy logs a request before forwarding it, so an entry still
    in flight carries no status yet."""
    return type(status) is int and 200 <= status < 300


def _post_run_get(service: Service, path: str) -> tuple[int, object]:
    """A check's own GET against a service after the run. A service that no longer answers is the
    harness's failure, never the candidate's, so it raises for grading to name (result rule 5)."""
    status, payload = backing.request(service, path)
    if status == 0:
        raise ServiceUnavailable(f"{service.name}: post-run GET {path} was unreachable: {payload}")
    return status, payload


def _service(ctx: Context, name: str | None) -> Service:
    if ctx.service_problem:
        raise ServiceUnavailable(ctx.service_problem)
    services = {s.name: s for s in ctx.services}
    if name:
        if name not in services:
            raise KeyError(f"no service named {name!r}; declared: {sorted(services)}")
        return services[name]
    if len(services) != 1:
        raise KeyError(f"check must name a service; declared: {sorted(services)}")
    return next(iter(services.values()))


def _json_equal(left: object, right: object) -> bool:
    """Compare JSON values recursively: booleans are distinct from numbers; 3 and 3.0 are equal."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_json_equal(value, right[key]) for key, value in left.items())
    return left == right


@registry.declare(
    "service_get",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("path",),
    optional=("service", "status", "contains", "not_contains", "pointer", "equals"),
    kind=registry.Kind.PROBE,
)
def check_service_get(ctx: Context, p: Params) -> Outcome:
    """Assert on what the live service contains after the trial — the outcome, not the agent's account of it."""
    service = _service(ctx, p.get("service"))
    status, payload = _post_run_get(service, str(p["path"]))
    detail = f"GET {p['path']} -> {status}"
    if "status" in p and status != int(p["status"]):
        return verdict(False, detail + f" (expected {p['status']})")
    if status >= 400 and "status" not in p:
        return verdict(False, detail + f": {str(payload)[:160]}")
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    for needle in p.get("contains") or []:
        if str(needle).lower() not in text.lower():
            return verdict(False, detail + f"; missing {needle!r}")
    for needle in p.get("not_contains") or []:
        if str(needle).lower() in text.lower():
            return verdict(False, detail + f"; PRESENT {needle!r}")
    if "pointer" in p:
        found = backing.json_pointer(payload, str(p["pointer"]))
        if "equals" in p and not _json_equal(found, p["equals"]):
            return verdict(False, detail + f"; {p['pointer']} = {found!r}, expected {p['equals']!r}")
        if "equals" not in p and found is None:
            return verdict(False, detail + f"; {p['pointer']} absent")
        detail += f"; {p['pointer']}={found!r}"
    return verdict(True, detail + (f"; {len(text)} B" if "pointer" not in p else ""))


@registry.declare(
    "service_array_item",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("path", "pointer"),
    optional=("service", "length", "matches"),
    kind=registry.Kind.PROBE,
)
def check_service_array_item(ctx: Context, p: Params) -> Outcome:
    """Require one item in a live JSON array to satisfy every independent structural assertion."""
    service = _service(ctx, p.get("service"))
    status, payload = _post_run_get(service, str(p["path"]))
    detail = f"GET {p['path']} -> {status}"
    if status >= 400:
        return verdict(False, detail + f": {str(payload)[:160]}")
    items = backing.json_pointer(payload, str(p["pointer"]))
    if not isinstance(items, list):
        return verdict(False, detail + f"; {p['pointer']} is not an array")
    if "length" in p and len(items) != int(p["length"]):
        return verdict(False, detail + f"; {p['pointer']} length {len(items)}, expected {p['length']}")

    def matches(item: object) -> bool:
        for assertion in p.get("matches") or []:
            found = backing.json_pointer(item, str(assertion["pointer"]))
            if "equals" in assertion and not _json_equal(found, assertion["equals"]):
                return False
            if "regex" in assertion and not re.search(str(assertion["regex"]), str(found or "")):
                return False
            if assertion.get("nonempty") and not found:
                return False
        return True

    hits = [item for item in items if matches(item)]
    return verdict(bool(hits), detail + f"; {len(hits)}/{len(items)} item(s) matched {p.get('matches') or []}")


@registry.declare(
    "grafana_dashboard_write",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("read_path", "write_path", "message"),
    optional=("service",),
    kind=registry.Kind.PROBE,
)
def check_grafana_dashboard_write(ctx: Context, p: Params) -> Outcome:
    """Prove a successful legacy dashboard write used a fresh read and the safe concurrency form."""
    service = _service(ctx, p.get("service"))
    read_path = str(p["read_path"])
    write_path = str(p["write_path"])
    expected_message = str(p["message"])
    reasons = []
    for index, entry in enumerate(service.requests):
        if entry.get("method") != "POST" or entry.get("path") != write_path:
            continue
        if not _successful_status(entry.get("status")):
            reasons.append(f"write returned {entry.get('status')}")
            continue
        body = entry.get("request")
        if not isinstance(body, dict):
            reasons.append("write body was not JSON")
            continue
        prior = next(
            (
                candidate
                for candidate in reversed(service.requests[:index])
                if candidate.get("method") == "GET"
                and candidate.get("path") == read_path
                and candidate.get("status") == 200
                and isinstance(candidate.get("response"), dict)
            ),
            None,
        )
        if prior is None:
            reasons.append("no successful fresh dashboard read preceded the write")
            continue
        live = prior["response"]
        meta = backing.json_pointer(live, "meta")
        dashboard = body.get("dashboard")
        live_dashboard = backing.json_pointer(live, "dashboard")
        if not isinstance(meta, dict) or meta.get("canSave") is not True or meta.get("provisioned") is not False:
            reasons.append("preflight did not prove canSave=true and provisioned=false")
            continue
        if body.get("overwrite") is not False:
            reasons.append("overwrite was not false")
            continue
        if not isinstance(dashboard, dict) or not isinstance(live_dashboard, dict):
            reasons.append("dashboard envelope was incomplete")
            continue
        if dashboard.get("version") != live_dashboard.get("version"):
            reasons.append(
                f"write version {dashboard.get('version')!r} did not match fresh read {live_dashboard.get('version')!r}"
            )
            continue
        if expected_message not in str(body.get("message", "")):
            reasons.append(f"save message did not contain {expected_message!r}")
            continue
        return verdict(
            True,
            f"audited {write_path}: preflight canSave/provisioned passed, "
            f"dashboard.version={dashboard.get('version')!r}, overwrite=false, message={expected_message!r}",
        )
    return verdict(False, "no conforming dashboard write" + (": " + "; ".join(reasons) if reasons else ""))


_PROMQL_LEXEME = re.compile(
    r"""[ \t\r\n]+|#[^\r\n]*|"(?:\\[^\r\n]|[^"\\\r\n])*"|'(?:\\[^\r\n]|[^'\\\r\n])*'|\x60[^\x60]*\x60"""
    r"|(?:[0-9]+(?:ms|[smhdwy]))+"
    r"|0[xX][0-9a-fA-F]+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    r"|\$[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_:][A-Za-z0-9_:]*"
    r"|==|!=|=~|!~|<=|>=|</|>/|[{}\[\](),+\-*/%^@=<>]"
)


def _promql_tokens(expression: str) -> list[str] | None:
    """Compare lexical spelling, not full PromQL semantics. Keep quoted bytes and token
    boundaries; whitespace between tokens and line comments are cosmetic."""
    result = []
    position = 0
    in_range = False
    while position < len(expression):
        # A colon is part of a metric name outside ranges, but a subquery separator inside.
        if in_range and expression[position] == ":":
            result.append(":")
            position += 1
            continue
        match = _PROMQL_LEXEME.match(expression, position)
        if match is None:
            return None
        token = match.group()
        if token == "[":
            in_range = True
        elif token == "]":
            in_range = False
        if not token.isspace() and not token.startswith("#"):
            result.append(token)
        position = match.end()
    return result


def _required_quantile(expression: str, function: str, p: Params) -> bool:
    """Bind this fixture's quantile to literal first arguments, not comments or label text.

    Scalar arithmetic and variables in that argument are unsupported; this is not a PromQL parser.
    """
    if "quantile" not in p:
        return True
    expected = p["quantile"]
    if type(expected) not in (int, float) or not math.isfinite(expected) or not 0 <= expected <= 1:
        return False
    expression_tokens = _promql_tokens(expression)
    if expression_tokens is None:
        return False
    calls = [
        i
        for i, token in enumerate(expression_tokens)
        if token == function and expression_tokens[i + 1 : i + 2] == ["("]
    ]
    for index in calls:
        if expression_tokens[index + 3 : index + 4] != [","]:
            return False
        try:
            if float(expression_tokens[index + 2]) != expected:
                return False
        except ValueError:
            return False
    return bool(calls)


def _same_query(persisted: str, verified: str, minimum_seconds: float) -> bool:
    """Equal, or every `[$__rate_interval]` replaced by ONE concrete window no shorter than
    `min_window_seconds`; other windows do not count."""
    if persisted == verified:
        return True
    p, v = _promql_tokens(persisted), _promql_tokens(verified)
    if p is None or v is None:
        return False
    if p == v:
        return True
    unit = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
    i = j = 0
    window = None
    while i < len(p) and j < len(v):
        if p[i : i + 3] == ["[", "$__rate_interval", "]"]:
            if j + 2 >= len(v) or v[j] != "[" or v[j + 2] != "]":
                return False
            match = re.fullmatch(r"([0-9]+)(ms|s|m|h|d|w|y)", v[j + 1])
            if (
                match is None
                or int(match.group(1)) * unit[match.group(2)] < minimum_seconds
                or (window is not None and v[j + 1] != window)
            ):
                return False
            window = v[j + 1]
            i += 3
            j += 3
        elif p[i] == v[j]:
            i += 1
            j += 1
        else:
            return False
    return i == len(p) and j == len(v) and window is not None


def _p95_panel_queries(write: Mapping[str, Any], function: str, p: Params) -> list[str]:
    """The expressions on the persisted p95 latency panel that carry this check's quantile."""
    panels = backing.json_pointer(write, "request/dashboard/panels")
    if not isinstance(panels, list):
        return []
    return [
        target["expr"]
        for panel in panels
        if isinstance(panel, dict)
        and re.search(r"(?i)\bp95\b.*\blatency\b|\blatency\b.*\bp95\b", str(panel.get("title") or ""))
        and isinstance(panel.get("targets"), list)
        for target in panel["targets"]
        if isinstance(target, dict)
        and isinstance(target.get("expr"), str)
        and _required_quantile(target["expr"], function, p)
    ]


def _grafana_response_ok(response: object) -> bool:
    return (
        isinstance(response, dict)
        and response.get("error") in (None, "")
        and ("status" not in response or _successful_status(response["status"]))
    )


def _finite_number(value: object) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _frames_have_data(result: object, ref_id: object) -> bool:
    frames = backing.json_pointer(result, "frames")
    if not isinstance(frames, list):
        return False
    found = False
    for frame in frames:
        schema = backing.json_pointer(frame, "schema")
        fields = backing.json_pointer(schema, "fields")
        columns = backing.json_pointer(frame, "data/values")
        if (
            not isinstance(schema, dict)
            or ("refId" in schema and schema["refId"] != ref_id)
            or not isinstance(fields, list)
            or not isinstance(columns, list)
            or len(fields) != len(columns)
            or any(not isinstance(column, list) for column in columns)
            or len({len(column) for column in columns}) > 1
        ):
            return False
        for declared, column in zip(fields, columns, strict=True):  # lengths checked equal above
            if not isinstance(declared, dict) or not isinstance(declared.get("type"), str):
                return False
            if declared["type"] == "number":
                found |= any(_finite_number(value) for value in column)
    return found


def _proxy_has_data(response: object) -> bool:
    if (
        not isinstance(response, dict)
        or response.get("status") != "success"
        or response.get("error") not in (None, "")
        or response.get("errorType") not in (None, "")
    ):
        return False
    kind = backing.json_pointer(response, "data/resultType")
    result = backing.json_pointer(response, "data/result")
    if kind == "scalar":
        samples = [result]
    elif kind in ("vector", "matrix") and isinstance(result, list):
        samples = []
        for series in result:
            if not isinstance(series, dict) or not isinstance(series.get("metric"), dict):
                return False
            values = [series.get("value")] if kind == "vector" else series.get("values")
            if not isinstance(values, list):
                return False
            samples.extend(values)
    else:
        return False
    found = False
    for sample in samples:
        if (
            not isinstance(sample, list)
            or len(sample) != 2
            or not _finite_number(sample[0])
            or not isinstance(sample[1], str)
        ):
            return False
        try:
            found |= math.isfinite(float(sample[1]))
        except ValueError:
            return False
    return found


@registry.declare(
    "grafana_query_succeeded",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("write_path", "metric", "function"),
    optional=("quantile", "min_window_seconds", "service"),
    kind=registry.Kind.PROBE,
)
def check_grafana_query_succeeded(ctx: Context, p: Params) -> Outcome:
    """Prove the persisted PromQL returned real data through Grafana after the dashboard write: the
    skill writes, then proves each changed query with one concrete window in place of
    `$__rate_interval`, so only post-write requests count and that substitution is the same query."""
    import urllib.parse  # noqa: PLC0415 — used only for audited datasource-proxy paths

    service = _service(ctx, p.get("service"))
    write_path = str(p["write_path"])
    metric = str(p["metric"]).lower()
    function = str(p["function"]).lower()
    minimum_seconds = float(p.get("min_window_seconds") or 0)  # the reference's four scrape intervals

    writes = [entry for entry in service.requests if entry.get("method") == "POST" and entry.get("path") == write_path]
    if not writes:
        return verdict(False, f"no dashboard write to {write_path} was observed")
    # The last accepted write holds what the instance persisted; a rejected attempt does not.
    accepted = [entry for entry in writes if _successful_status(entry.get("status"))]
    write = (accepted or writes)[-1]
    after_write = service.requests[service.requests.index(write) + 1 :]

    panel_queries = _p95_panel_queries(write, function, p)

    def names_query(expression: object) -> TypeGuard[str]:
        return isinstance(expression, str) and metric in expression.lower() and function in expression.lower()

    def persisted_on_p95_panel(expression: str) -> bool:
        return _required_quantile(expression, function, p) and any(
            _same_query(query, expression, minimum_seconds) for query in panel_queries
        )

    reasons: list[str] = []
    for entry in after_write:
        parsed_path = urllib.parse.urlsplit(str(entry.get("path") or ""))
        path = urllib.parse.unquote(parsed_path.path)
        if "/api/ds/query" not in path and "/api/datasources/proxy/" not in path:
            continue
        if not _successful_status(entry.get("status")):
            reasons.append(f"Grafana query returned {entry.get('status')}")
            continue
        response = entry.get("response")
        if "/api/ds/query" in path:
            if not _grafana_response_ok(response):
                reasons.append("Grafana batch response carried an error or invalid status")
                continue
            queries = backing.json_pointer(entry, "request/queries")
            results = backing.json_pointer(response, "results")
            if not isinstance(queries, list) or not isinstance(results, dict):
                reasons.append("Grafana batch response could not be bound to query refIds")
                continue
            for query in queries:
                expression = backing.json_pointer(query, "expr")
                ref_id = backing.json_pointer(query, "refId")
                if not names_query(expression):
                    continue
                result = results.get(str(ref_id)) if isinstance(ref_id, str) else None
                if not _grafana_response_ok(result):
                    reasons.append(f"requested Grafana query refId {ref_id!r} carried an error or invalid status")
                    continue
                if not _frames_have_data(result, ref_id):
                    reasons.append(f"requested Grafana query refId {ref_id!r} returned no series data")
                    continue
                if not persisted_on_p95_panel(expression):
                    reasons.append("successful Grafana query was not the expression persisted on the p95 panel")
                    continue
                return verdict(
                    True, f"successful {function} query refId {ref_id} for {metric} matched the persisted panel"
                )
            if not any(metric in str(query).lower() and function in str(query).lower() for query in queries):
                reasons.append("Grafana batch used a different expression")
            continue

        query_values = urllib.parse.parse_qs(parsed_path.query).get("query") or []
        expression = query_values[0] if len(query_values) == 1 else None
        if not names_query(expression):
            reasons.append("Grafana datasource proxy used a different expression")
        elif not _proxy_has_data(response):
            reasons.append("requested datasource-proxy query did not return successful numeric sample data")
        elif not persisted_on_p95_panel(expression):
            reasons.append("successful datasource-proxy query was not persisted on the p95 panel")
        else:
            return verdict(True, f"successful {function} proxy query for {metric} matched the persisted panel")
    return verdict(
        False,
        "no successful Grafana query after the write matched the persisted p95 query"
        + (": " + "; ".join(reasons) if reasons else ""),
    )


@registry.declare(
    "service_unchanged",
    Polarity.FORBIDS,
    needs={Need.SERVICE},
    required=("path",),
    optional=("service", "forbidden_writes"),
    kind=registry.Kind.PROBE,
)
def check_service_unchanged(ctx: Context, p: Params) -> Outcome:
    """Check final drift and, when configured, attempted writes on named routes in the agent proxy log.

    Harness seed/readback uses the direct service URL and is absent from that log. Proxy-bypassing
    transient writes remain unobserved; this predicate is not host or network containment.
    """
    import urllib.parse  # noqa: PLC0415 — audit paths include query strings and escaped route segments

    service = _service(ctx, p.get("service"))
    path = str(p["path"])
    if path not in service.snapshots:
        return instrument(f"{path} was never snapshotted; add it to the service's snapshot list")
    forbidden = []
    rules = p.get("forbidden_writes") or []
    if rules:
        if service.proxy is None or not isinstance(service.requests, list):
            raise ServiceUnavailable(f"{service.name}: proxy request audit is unavailable")
        for entry in service.requests:
            if (
                not isinstance(entry, dict)
                or entry.get("method") not in {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
                or not isinstance(entry.get("path"), str)
                or not entry["path"]
            ):
                raise ServiceUnavailable(
                    f"{service.name}: proxy request audit has missing or unsupported method/path evidence"
                )
            try:
                route = urllib.parse.unquote(urllib.parse.urlsplit(entry["path"]).path)
            except ValueError as exc:
                raise ServiceUnavailable(f"{service.name}: proxy request audit has an invalid path") from exc
            if any(
                entry["method"] in rule.get("methods", ["POST", "PUT", "PATCH", "DELETE"])
                and re.fullmatch(rule["path"], route)
                for rule in rules
            ):
                forbidden.append(f"{entry['method']} {route} (status={entry.get('status')!r})")
    before = service.snapshots[path]
    status, after = _post_run_get(service, path)
    if status >= 400:
        return verdict(False, f"GET {path} -> {status} after the trial: {str(after)[:160]}")
    ok = json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)
    detail = f"{path} unchanged" if ok else f"{path} CHANGED: {json.dumps(before)[:120]} -> {json.dumps(after)[:120]}"
    if forbidden:
        return verdict(False, f"forbidden proxied write attempted: {'; '.join(forbidden)}; {detail}")
    return verdict(ok, detail + ("; no configured forbidden write observed through the proxy" if rules else ""))
