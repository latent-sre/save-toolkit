#!/usr/bin/env python3
"""Bounded Grafana reads with process-local authentication and safe JSON output.

Python 3.11+, stdlib only. Trusted launcher supplies GRAFANA_URL, GRAFANA_ORG_ID and either
GRAFANA_SA_TOKEN or GRAFANA_USERNAME/GRAFANA_PASSWORD; credential files are not read.
This masks known authentication values, not arbitrary sensitive telemetry, and does
not isolate the surrounding agent's independent tools from the operating system.
Masking can replace any returned value/type, including metadata; exit status is authoritative.
Exit 0: requested API operation succeeded (coverage unproven); 2: safe failure.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import math
import os
import re
import ssl
import sys
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus, urlsplit
from urllib.request import HTTPSHandler, HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_RESPONSE = 2 * 1024 * 1024
TIMEOUT = 20
MAX_RANGE_MS = 24 * 60 * 60 * 1000
UID = re.compile(r"[A-Za-z0-9_-]{1,40}\Z")
TEMPLATE = re.compile(r"\$(?:[A-Za-z_]|\{)|\[\[[A-Za-z_][^\]]*\]\]")


class SafeError(Exception):
    """A static error code safe to expose; never constructed from external text."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SafeError("invalid_arguments")


def parse_args(argv):
    """Validate exact read-only CLI grammar without printing rejected input."""
    parser = _Parser(add_help=False, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    dashboard = commands.add_parser("dashboard", add_help=False, allow_abbrev=False)
    dashboard.add_argument("--uid", required=True)
    query = commands.add_parser("query", add_help=False, allow_abbrev=False)
    query.add_argument("--datasource", required=True)
    query.add_argument("--kind", choices=("prometheus", "loki"), required=True)
    query.add_argument("--from", dest="from_ms", type=int, required=True)
    query.add_argument("--to", dest="to_ms", type=int, required=True)
    expression = query.add_mutually_exclusive_group(required=True)
    expression.add_argument("--expr")
    expression.add_argument("--expr-base64")
    args = parser.parse_args(argv)
    expected = {"--uid"} if args.command == "dashboard" else {"--datasource", "--kind", "--from", "--to", "--expr"}
    if args.command == "query" and args.expr_base64 is not None:
        expected.remove("--expr")
        expected.add("--expr-base64")
    # Require separate, single-use named flags; no positional or --flag=value variants.
    if len(argv) != 1 + 2 * len(expected) or set(argv[1::2]) != expected:
        raise SafeError("invalid_arguments")
    uid = args.uid if args.command == "dashboard" else args.datasource
    if not UID.fullmatch(uid):
        raise SafeError("invalid_arguments")
    if args.command == "query":
        if args.expr_base64 is not None:
            # Encoding is argument transport, not encryption or secret handling.
            try:
                if len(args.expr_base64) > 85336:
                    raise ValueError()
                raw = base64.b64decode(args.expr_base64, validate=True)
                if base64.b64encode(raw).decode("ascii") != args.expr_base64:
                    raise ValueError()
                args.expr = raw.decode("utf-8", errors="strict")
            except (ValueError, UnicodeError):
                raise SafeError("invalid_arguments") from None
        if not 0 <= args.from_ms < args.to_ms <= 253402300799999 or args.to_ms - args.from_ms > MAX_RANGE_MS:
            raise SafeError("invalid_arguments")
        if not args.expr.strip() or len(args.expr) > 16000 or TEMPLATE.search(args.expr):
            raise SafeError("unresolved_or_invalid_expression")
        if any(ord(char) < 32 for char in args.expr):
            raise SafeError("invalid_arguments")
    return args


def _configuration(environ):
    organization = environ.get("GRAFANA_ORG_ID", "")
    if not re.fullmatch(r"[1-9][0-9]{0,18}", organization) or int(organization) > 9223372036854775807:
        raise SafeError("invalid_organization_configuration")
    base = environ.get("GRAFANA_URL", "")
    if not base or any(char.isspace() or ord(char) < 32 for char in base) or "\\" in base:
        raise SafeError("invalid_configuration")
    try:
        url = urlsplit(base)
        port = url.port
    except ValueError:
        raise SafeError("invalid_configuration") from None
    if (url.scheme != "https" or not url.hostname or url.username is not None or url.password is not None
            or url.query or url.fragment or "?" in base or "#" in base
            or "%" in url.netloc or "%" in url.path or (port is not None and not 1 <= port <= 65535)
            or any(part in (".", "..") for part in url.path.split("/"))):
        raise SafeError("invalid_configuration")
    token = environ.get("GRAFANA_SA_TOKEN", "")
    username = environ.get("GRAFANA_USERNAME", "")
    password = environ.get("GRAFANA_PASSWORD", "")
    secrets = [value for value in (token, username, password) if value]
    if any(any(ord(char) < 32 or ord(char) == 127 for char in value) for value in secrets):
        raise SafeError("invalid_authentication")
    pair = username + ":" + password
    encoded = base64.b64encode(pair.encode("utf-8")).decode("ascii")
    if username and password:
        secrets.extend((pair, encoded))
    if token:
        authorization = "Bearer " + token
    elif username and password and ":" not in username:
        authorization = "Basic " + encoded
    else:
        raise SafeError("authentication_unavailable")
    secrets.append(authorization)
    return base.rstrip("/"), authorization, secrets, int(organization)


def _mask(value, secrets):
    variants = set()
    for secret in secrets:
        if secret:
            variants.update((secret, quote(secret, safe=""), quote_plus(secret),
                             base64.b64encode(secret.encode("utf-8")).decode("ascii")))
    pattern = re.compile("|".join(re.escape(value) for value in sorted(variants, key=len, reverse=True))) if variants else None

    def clean(item):
        if isinstance(item, str):
            item = re.sub(r"(https?://)[^/\s@]+@", r"\1[REDACTED]@", item, flags=re.IGNORECASE)
            return pattern.sub("[REDACTED]", item) if pattern else item
        if isinstance(item, list):
            return [clean(child) for child in item]
        if isinstance(item, dict):
            return {clean(key): "[REDACTED]" if key.lower() in {"authorization", "proxy-authorization", "cookie", "set-cookie"}
                    else clean(child) for key, child in item.items()}
        if item is None or isinstance(item, bool):
            text = json.dumps(item)
            return "[REDACTED]" if pattern and pattern.search(text) else item
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            text = str(item)
            return "[REDACTED]" if pattern and pattern.search(text) else item
        return item

    return clean(value)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SafeError("redirect_rejected")


def http_transport(request):
    """No ambient proxies, redirects, netrc, custom trust bypass or credential files."""
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            return response.status, response.read(MAX_RESPONSE + 1)
    except HTTPError as error:
        # Never read/echo HTTP error bodies or exception text (which can contain auth).
        status = error.code
        error.close()
        return status, b""


def _read(transport, base, authorization, organization, path, body=None):
    headers = {"Accept": "application/json", "Authorization": authorization, "X-Grafana-Org-Id": str(organization)}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = Request(base + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                      headers=headers, method="GET" if body is None else "POST")
    try:
        status, raw = transport(request)
    except SafeError:
        raise
    except Exception:
        raise SafeError("request_failed") from None
    if 300 <= status < 400:
        raise SafeError("redirect_rejected")
    if status < 200 or status >= 300:
        raise SafeError("http_error")
    if len(raw) > MAX_RESPONSE:
        raise SafeError("response_too_large")
    try:
        result = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise SafeError("invalid_response") from None
    if not isinstance(result, dict):
        raise SafeError("invalid_response")
    return result


def run(args, environ, transport):
    base, authorization, secrets, organization = _configuration(environ)
    current_org = _read(transport, base, authorization, organization, "/api/org")
    if type(current_org.get("id")) is not int or current_org["id"] != organization:
        raise SafeError("organization_mismatch")
    if args.command == "dashboard":
        response = _read(transport, base, authorization, organization, "/api/dashboards/uid/" + args.uid)
        dashboard = response.get("dashboard")
        if not isinstance(dashboard, dict) or dashboard.get("uid") != args.uid or not isinstance(response.get("meta"), dict):
            raise SafeError("invalid_dashboard_response")
        result = {"ok": True, "operation": "dashboard", "dashboard": dashboard, "meta": response["meta"],
                  "coverage": "configuration_only"}
    else:
        datasource = _read(transport, base, authorization, organization, "/api/datasources/uid/" + args.datasource + "?ds_type=" + args.kind)
        if "orgId" in datasource and (type(datasource["orgId"]) is not int or datasource["orgId"] != organization):
            raise SafeError("organization_mismatch")
        if datasource.get("uid") != args.datasource or datasource.get("type") != args.kind:
            raise SafeError("datasource_mismatch")
        interval = max(1000, math.ceil((args.to_ms - args.from_ms) / 1000))
        query = {"refId": "A", "datasource": {"uid": args.datasource, "type": args.kind},
                 "expr": args.expr, "maxDataPoints": 1000, "intervalMs": interval}
        if args.kind == "prometheus":
            query.update({"range": True, "instant": False, "format": "time_series"})
        else:
            query.update({"queryType": "range", "maxLines": 500})
        response = _read(transport, base, authorization, organization, "/api/ds/query",
                         {"from": str(args.from_ms), "to": str(args.to_ms), "queries": [query]})
        results = response.get("results")
        if response.get("error") or not isinstance(results, dict) or set(results) != {"A"} or not isinstance(results["A"], dict):
            raise SafeError("query_failed")
        result_a = results["A"]
        try:
            failed = bool(result_a.get("error")) or int(result_a.get("status", 200)) >= 400
        except (ValueError, TypeError):
            failed = True
        if failed or not isinstance(result_a.get("frames"), list):
            raise SafeError("query_failed")
        result = {"ok": True, "operation": "query", "datasource": args.datasource, "kind": args.kind,
                  "from": str(args.from_ms), "to": str(args.to_ms), "results": results,
                  "coverage": "not_established", "limits": {"maxDataPoints": 1000, "intervalMs": interval,
                  "maxLines": 500 if args.kind == "loki" else None}}
    result.update({"grafana_url": base, "organization_id": organization,
                   "retrieved_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")})
    return _mask(result, secrets)


def main(argv=None, *, environ=None, transport=None, output=None):
    output = sys.stdout if output is None else output
    try:
        result = run(parse_args(sys.argv[1:] if argv is None else argv), os.environ if environ is None else environ,
                     http_transport if transport is None else transport)
        serialized = json.dumps(result, ensure_ascii=True, allow_nan=False)
        code = 0
    except SafeError as error:
        serialized, code = json.dumps({"ok": False, "error": str(error)}), 2
    except Exception:
        # Process boundary: prevent unexpected library errors exposing credential material.
        serialized, code = '{"ok": false, "error": "request_failed"}', 2
    output.write(serialized + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
