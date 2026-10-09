#!/usr/bin/env python3
"""Bounded Grafana reads with process-local authentication and safe JSON output.

Python 3.11+, stdlib only. The environment supplies GRAFANA_URL, GRAFANA_ORG_ID and either
GRAFANA_SA_TOKEN or GRAFANA_USERNAME/GRAFANA_PASSWORD. When it sets none of them, the one
per-user file ~/.config/save-toolkit/grafana.env (KEY=VALUE lines) supplies them; sources never mix.
This masks known authentication values, not arbitrary sensitive telemetry, and does
not isolate the surrounding agent's independent tools from the operating system.
Masking can replace any returned value/type, including metadata; exit status is authoritative.
Exit 0: requested API operation succeeded (coverage unproven); 2: safe failure.
"""

import argparse
import base64
import json
import math
import os
import re
import ssl
import stat
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

MAX_RESPONSE = 2 * 1024 * 1024
TIMEOUT = 20
MAX_RANGE_MS = 24 * 60 * 60 * 1000
MAX_EXPRESSION = 16000
# The canonical base64 of a MAX_EXPRESSION-character expression whose every character takes the
# longest UTF-8 encoding, four bytes; anything longer cannot decode to an acceptable expression.
MAX_EXPRESSION_BASE64 = 4 * math.ceil(4 * MAX_EXPRESSION / 3)
MAX_DATA_POINTS = 1000
MAX_LOG_LINES = 500
LIST_LIMIT = 100
ALERTS_PER_RULE = 20
UID = re.compile(r"[A-Za-z0-9_-]{1,40}\Z")
SEARCH_TEXT = re.compile(r"[A-Za-z0-9 _.:-]{1,100}\Z")
SETTINGS = ("GRAFANA_URL", "GRAFANA_ORG_ID", "GRAFANA_SA_TOKEN", "GRAFANA_USERNAME", "GRAFANA_PASSWORD")
MAX_SETTINGS_FILE = 4096
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
    search = commands.add_parser("search", add_help=False, allow_abbrev=False)
    search.add_argument("--query", required=True)
    alerts = commands.add_parser("alerts", add_help=False, allow_abbrev=False)
    alerts.add_argument("--folder-uid")
    annotations = commands.add_parser("annotations", add_help=False, allow_abbrev=False)
    annotations.add_argument("--from", dest="from_ms", type=int, required=True)
    annotations.add_argument("--to", dest="to_ms", type=int, required=True)
    annotations.add_argument("--dashboard-uid")
    commands.add_parser("silences", add_help=False, allow_abbrev=False)
    args = parser.parse_args(argv)
    expected = {"dashboard": {"--uid"}, "query": {"--datasource", "--kind", "--from", "--to", "--expr"},
                "search": {"--query"}, "alerts": set(), "annotations": {"--from", "--to"}, "silences": set()}[args.command]
    if args.command == "query" and args.expr_base64 is not None:
        expected.remove("--expr")
        expected.add("--expr-base64")
    for flag, value in (("--folder-uid", getattr(args, "folder_uid", None)), ("--dashboard-uid", getattr(args, "dashboard_uid", None))):
        if value is not None:
            expected.add(flag)
    # Require separate, single-use named flags; no positional or --flag=value variants.
    if len(argv) != 1 + 2 * len(expected) or set(argv[1::2]) != expected:
        raise SafeError("invalid_arguments")
    uids = [getattr(args, name, None) for name in ("uid", "datasource", "folder_uid", "dashboard_uid")]
    if any(uid is not None and not UID.fullmatch(uid) for uid in uids):
        raise SafeError("invalid_arguments")
    if args.command == "search" and (not SEARCH_TEXT.fullmatch(args.query) or not args.query.strip()):
        raise SafeError("invalid_arguments")
    if args.command in ("query", "annotations") and (
            not 0 <= args.from_ms < args.to_ms <= 253402300799999 or args.to_ms - args.from_ms > MAX_RANGE_MS):
        raise SafeError("invalid_arguments")
    if args.command == "query":
        if args.expr_base64 is not None:
            # Encoding is argument transport, not encryption or secret handling.
            try:
                if len(args.expr_base64) > MAX_EXPRESSION_BASE64:
                    raise ValueError()
                raw = base64.b64decode(args.expr_base64, validate=True)
                if base64.b64encode(raw).decode("ascii") != args.expr_base64:
                    raise ValueError()
                args.expr = raw.decode("utf-8", errors="strict")
            except (ValueError, UnicodeError):
                raise SafeError("invalid_arguments") from None
        if not args.expr.strip() or len(args.expr) > MAX_EXPRESSION or TEMPLATE.search(args.expr):
            raise SafeError("unresolved_or_invalid_expression")
        if any(ord(char) < 32 for char in args.expr):
            raise SafeError("invalid_arguments")
    return args


def _settings_file():
    """The per-user file in the home directory, never a path relative to the workspace."""
    try:
        path = Path.home() / ".config" / "save-toolkit" / "grafana.env"
    except RuntimeError:
        return None
    # A relative home would resolve the file inside whatever workspace the helper runs from.
    return path if path.is_absolute() else None


def _private(info, uid):
    """POSIX: owned by this user, with no group or other permission bits."""
    return info.st_uid == uid and not info.st_mode & 0o077


def _settings(environ, path):
    """The environment when it names any Grafana setting, even empty; otherwise the per-user file."""
    if path is None or any(name in environ for name in SETTINGS):
        return environ
    try:
        if os.name == "posix":
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise SafeError("invalid_settings_file")
            if not _private(info, os.getuid()):
                raise SafeError("insecure_settings_file")
        raw = path.read_bytes()
    except FileNotFoundError:
        return environ
    except OSError:
        raise SafeError("invalid_settings_file") from None
    try:
        if len(raw) > MAX_SETTINGS_FILE:
            raise ValueError()
        settings = {}
        for line in raw.decode("utf-8-sig").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            name, separator, value = line.partition("=")
            name = name.strip()
            if not separator or name not in SETTINGS or name in settings:
                raise ValueError()
            # Verbatim, as the environment would pass it: there is no quoting to restore stripped bytes.
            settings[name] = value
    except (ValueError, UnicodeError):
        # Static error only: a malformed line can hold the token itself.
        raise SafeError("invalid_settings_file") from None
    return settings


def _reject_constant(name):
    """json.loads hook: NaN and Infinity are not JSON numbers; refuse them rather than return floats."""
    raise ValueError("non-standard JSON constant")


@dataclass(frozen=True)
class _Connection:
    """One verified origin, credential and organization; every request carries all three."""

    transport: Callable[[Request], tuple[int, bytes]]
    base: str
    authorization: str
    organization: int

    def read(self, path, body=None, expect=dict):
        """GET a fixed API path, or POST a JSON body to it; return its JSON `expect` or raise SafeError."""
        headers = {"Accept": "application/json", "Authorization": self.authorization,
                   "X-Grafana-Org-Id": str(self.organization)}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(self.base + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                          headers=headers, method="GET" if body is None else "POST")
        try:
            status, raw = self.transport(request)
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
            result = json.loads(raw, parse_constant=_reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            raise SafeError("invalid_response") from None
        if not isinstance(result, expect):
            raise SafeError("invalid_response")
        return result

    def items(self, path):
        """A list endpoint: every item is an object, and none names another organization."""
        return _items(self.read(path, expect=list), self.organization)


def _items(response, organization):
    """List endpoints: every item is an object, and none names another organization."""
    if not all(isinstance(item, dict) for item in response):
        raise SafeError("invalid_response")
    if any("orgId" in item and (type(item["orgId"]) is not int or item["orgId"] != organization) for item in response):
        raise SafeError("organization_mismatch")
    return response


def _connect(environ, transport):
    """Validate the launcher's settings; return the connection and every credential form to mask."""
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
    return _Connection(transport, base.rstrip("/"), authorization, int(organization)), secrets


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
        # Numbers as Python spells them: a decoded 1e999 is inf, which json.dumps would spell Infinity.
        if isinstance(item, (int, float)):
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


def _dashboard(grafana, args):
    response = grafana.read("/api/dashboards/uid/" + args.uid)
    dashboard = response.get("dashboard")
    if not isinstance(dashboard, dict) or dashboard.get("uid") != args.uid or not isinstance(response.get("meta"), dict):
        raise SafeError("invalid_dashboard_response")
    return {"ok": True, "operation": "dashboard", "dashboard": dashboard, "meta": response["meta"],
            "coverage": "configuration_only"}


def _query(grafana, args):
    datasource = grafana.read("/api/datasources/uid/" + args.datasource + "?ds_type=" + args.kind)
    if "orgId" in datasource and (type(datasource["orgId"]) is not int or datasource["orgId"] != grafana.organization):
        raise SafeError("organization_mismatch")
    if datasource.get("uid") != args.datasource or datasource.get("type") != args.kind:
        raise SafeError("datasource_mismatch")
    interval = max(1000, math.ceil((args.to_ms - args.from_ms) / 1000))
    # The limits sent are the limits reported beside the evidence.
    limits = {"maxDataPoints": MAX_DATA_POINTS, "intervalMs": interval,
              "maxLines": MAX_LOG_LINES if args.kind == "loki" else None}
    query = {"refId": "A", "datasource": {"uid": args.datasource, "type": args.kind},
             "expr": args.expr, "maxDataPoints": limits["maxDataPoints"], "intervalMs": limits["intervalMs"]}
    if args.kind == "prometheus":
        query.update({"range": True, "instant": False, "format": "time_series"})
    else:
        query.update({"queryType": "range", "maxLines": limits["maxLines"]})
    response = grafana.read("/api/ds/query", {"from": str(args.from_ms), "to": str(args.to_ms), "queries": [query]})
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
    return {"ok": True, "operation": "query", "datasource": args.datasource, "kind": args.kind,
            "from": str(args.from_ms), "to": str(args.to_ms), "results": results,
            "coverage": "not_established", "limits": limits}


def _search(grafana, args):
    items = grafana.items("/api/search?type=dash-db&limit=" + str(LIST_LIMIT) + "&query=" + quote(args.query, safe=""))
    return {"ok": True, "operation": "search", "query": args.query, "items": items,
            "truncated": len(items) >= LIST_LIMIT, "coverage": "permission_scoped", "limits": {"limit": LIST_LIMIT}}


def _alerts(grafana, args):
    path = "/api/prometheus/grafana/api/v1/rules?group_limit=" + str(LIST_LIMIT) + "&limit_alerts=" + str(ALERTS_PER_RULE)
    response = grafana.read(path + ("&folder_uid=" + args.folder_uid if args.folder_uid else ""))
    data = response.get("data")
    if response.get("status") != "success" or not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        raise SafeError("query_failed")
    groups = _items(data["groups"], grafana.organization)
    # Grafana answers an inaccessible or unknown folder_uid with every visible folder.
    if args.folder_uid and any(group.get("folderUid") != args.folder_uid for group in groups):
        raise SafeError("folder_mismatch")
    return {"ok": True, "operation": "alerts", "folder_uid": args.folder_uid, "groups": groups,
            "totals": data.get("totals"), "truncated": bool(data.get("groupNextToken")),
            "coverage": "permission_scoped", "limits": {"group_limit": LIST_LIMIT, "limit_alerts": ALERTS_PER_RULE}}


def _annotations(grafana, args):
    path = "/api/annotations?from=" + str(args.from_ms) + "&to=" + str(args.to_ms) + "&limit=" + str(LIST_LIMIT)
    items = grafana.items(path + ("&dashboardUID=" + args.dashboard_uid if args.dashboard_uid else ""))
    return {"ok": True, "operation": "annotations", "from": str(args.from_ms), "to": str(args.to_ms),
            "dashboard_uid": args.dashboard_uid, "items": items, "truncated": len(items) >= LIST_LIMIT,
            "coverage": "permission_scoped", "limits": {"limit": LIST_LIMIT}}


def _silences(grafana, args):
    return {"ok": True, "operation": "silences", "silences": grafana.items("/api/alertmanager/grafana/api/v2/silences"),
            "coverage": "permission_scoped"}


_OPERATIONS = {"dashboard": _dashboard, "query": _query, "search": _search, "alerts": _alerts,
               "annotations": _annotations, "silences": _silences}


def run(args, environ, transport):
    grafana, secrets = _connect(_settings(environ, _settings_file()), transport)
    current_org = grafana.read("/api/org")
    if type(current_org.get("id")) is not int or current_org["id"] != grafana.organization:
        raise SafeError("organization_mismatch")
    result = _OPERATIONS[args.command](grafana, args)
    result.update({"grafana_url": grafana.base, "organization_id": grafana.organization,
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
