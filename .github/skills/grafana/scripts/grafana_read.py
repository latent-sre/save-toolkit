#!/usr/bin/env python3
"""Bounded Grafana reads with process-local authentication and safe JSON output.

Python 3.14+, stdlib only. The environment supplies GRAFANA_URL, GRAFANA_ORG_ID and either
GRAFANA_SA_TOKEN or GRAFANA_USERNAME/GRAFANA_PASSWORD. When it sets none of them, the one
per-user file ~/.config/save-toolkit/grafana.env (KEY=VALUE lines) supplies them; sources never mix.
This masks known authentication values, not arbitrary sensitive telemetry, and does
not isolate the surrounding agent's independent tools from the operating system.
Masking can replace any returned value/type, including metadata; exit status is authoritative.
Exit 0: requested API operation succeeded (coverage unproven); 2: safe failure.
"""

import argparse
import base64
import hashlib
import json
import math
import os
import re
import ssl
import stat
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, quote_plus, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request, build_opener

MAX_RESPONSE = 2 * 1024 * 1024
TIMEOUT = 20
MAX_RANGE_MS = 24 * 60 * 60 * 1000
MAX_EXPRESSION = 16000
# The canonical base64 of a MAX_EXPRESSION-character expression whose every character takes the
# longest UTF-8 encoding, four bytes; anything longer cannot decode to an acceptable expression.
MAX_EXPRESSION_BASE64 = 4 * math.ceil(4 * MAX_EXPRESSION / 3)
MAX_DATA_POINTS = 1000
SUMMARY_LIMIT = 100
MAX_LOG_LINES = 500
LIST_LIMIT = 100
MAX_SEARCH_PAGE = 100
ALERTS_PER_RULE = 20
UID = re.compile(r"[A-Za-z0-9_-]{1,40}\Z")
SEARCH_TEXT = re.compile(r"[A-Za-z0-9 _.:-]{1,100}\Z")
SILENCE_ID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")
SETTINGS = ("GRAFANA_URL", "GRAFANA_ORG_ID", "GRAFANA_SA_TOKEN", "GRAFANA_USERNAME", "GRAFANA_PASSWORD")
MAX_SETTINGS_FILE = 4096
MAX_RENDER_RANGE_MS = 7 * 24 * 60 * 60 * 1000
MAX_IMAGE = 8 * 1024 * 1024
RENDER_TIMEOUT = 45
RENDER_WIDTH, RENDER_HEIGHT = 1200, 600
MIN_RENDER_WIDTH, MAX_RENDER_WIDTH = 400, 2400
MIN_RENDER_HEIGHT, MAX_RENDER_HEIGHT = 200, 1600
MAX_VARIABLES = 5
VARIABLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}=[A-Za-z0-9_.:-]{1,100}\Z")
SLUG = re.compile(r"[a-z0-9-]{1,100}\Z")
PNG_SIGNATURE = bytes((137, 80, 78, 71, 13, 10, 26, 10))
TEMPLATE =re.compile(r"\$(?:[A-Za-z_]|\{)|\[\[[A-Za-z_][^\]]*\]\]")
MACRO = re.compile(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)")
# Grafana's Prometheus backend expands these from the request's intervalMs, time range and the
# datasource scrape interval; the expanded value can differ from the panel's.
BACKEND_MACROS = frozenset({"__interval", "__interval_ms", "__range", "__range_s", "__range_ms",
                            "__rate_interval", "__rate_interval_ms"})
NEXT_TOKEN = re.compile(r"[A-Za-z0-9_+/=-]{1,1024}\Z")
V2_LAYOUTS = {"GridLayout": "items", "AutoGridLayout": "items", "RowsLayout": "rows", "TabsLayout": "tabs"}
V2_VARIABLES = {"QueryVariable": "query", "TextVariable": "textbox", "ConstantVariable": "constant",
                "DatasourceVariable": "datasource", "IntervalVariable": "interval", "CustomVariable": "custom",
                "GroupByVariable": "groupby", "AdhocVariable": "adhoc", "SwitchVariable": "switch"}
MAX_LAYOUT_DEPTH = 16


class SafeError(Exception):
    """A static error code safe to expose; never constructed from external text.

    `status` carries the numeric HTTP status of a rejected response, which is not secret and
    separates authentication, permission, missing-resource and server failures.
    """

    def __init__(self, code, status=None):
        super().__init__(code)
        self.status = status if isinstance(status, int) and not isinstance(status, bool) else None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SafeError("invalid_arguments")


def parse_args(argv):
    """Validate exact read-only CLI grammar without printing rejected input."""
    parser = _Parser(add_help=False, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    dashboard = commands.add_parser("dashboard", add_help=False, allow_abbrev=False)
    dashboard.add_argument("--uid", required=True)
    dashboard.add_argument("--panel", type=int)
    query = commands.add_parser("query", add_help=False, allow_abbrev=False)
    query.add_argument("--datasource", required=True)
    query.add_argument("--kind", choices=("prometheus", "loki"), required=True)
    query.add_argument("--from", dest="from_ms", type=int, required=True)
    query.add_argument("--to", dest="to_ms", type=int, required=True)
    query.add_argument("--mode", choices=("range", "instant"))
    query.add_argument("--output", choices=("full", "summary"))
    query.add_argument("--interval-ms", type=int)
    query.add_argument("--rate-interval-ms", type=int)
    expression = query.add_mutually_exclusive_group(required=True)
    expression.add_argument("--expr")
    expression.add_argument("--expr-base64")
    search = commands.add_parser("search", add_help=False, allow_abbrev=False)
    search.add_argument("--query")
    search.add_argument("--page", type=int)
    search.add_argument("--folder-uid")
    search.add_argument("--tag")
    alerts = commands.add_parser("alerts", add_help=False, allow_abbrev=False)
    alert_scope = alerts.add_mutually_exclusive_group()
    alert_scope.add_argument("--folder-uid")
    alert_scope.add_argument("--uid")
    alerts.add_argument("--group-next-token")
    annotations = commands.add_parser("annotations", add_help=False, allow_abbrev=False)
    annotations.add_argument("--from", dest="from_ms", type=int, required=True)
    annotations.add_argument("--to", dest="to_ms", type=int, required=True)
    annotations.add_argument("--dashboard-uid")
    silences = commands.add_parser("silences", add_help=False, allow_abbrev=False)
    silences.add_argument("--id")
    render = commands.add_parser("render", add_help=False, allow_abbrev=False)
    render.add_argument("--uid", required=True)
    render.add_argument("--panel", type=int, required=True)
    render.add_argument("--from", dest="from_ms", type=int, required=True)
    render.add_argument("--to", dest="to_ms", type=int, required=True)
    render.add_argument("--var", dest="variables", action="append", default=[])
    render.add_argument("--var-base64", dest="encoded_variables", action="append", default=[])
    render.add_argument("--width", type=int)
    render.add_argument("--height", type=int)
    args = parser.parse_args(argv)
    expected = {"dashboard": {"--uid"}, "query": {"--datasource", "--kind", "--from", "--to", "--expr"},
                "search": set(), "alerts": set(), "annotations": {"--from", "--to"}, "silences": set(),
                "render": {"--uid", "--panel", "--from", "--to"}}[args.command]
    if args.command == "query" and args.expr_base64 is not None:
        expected.remove("--expr")
        expected.add("--expr-base64")
    for name in ("folder_uid", "dashboard_uid", "panel", "uid", "page", "tag", "id", "mode", "output",
                 "interval_ms", "rate_interval_ms", "width", "height", "group_next_token", "query"):
        if getattr(args, name, None) is not None:
            expected.add("--" + name.replace("_", "-"))
    # Separate named flags, each exactly once except a repeated --var; no positional or --flag=value variants.
    variables = getattr(args, "variables", [])
    encoded_variables = getattr(args, "encoded_variables", [])
    wanted = (dict.fromkeys(expected, 1) | ({"--var": len(variables)} if variables else {})
              | ({"--var-base64": len(encoded_variables)} if encoded_variables else {}))
    flags = argv[1::2]
    if len(argv) % 2 != 1 or {flag: flags.count(flag) for flag in flags} != wanted:
        raise SafeError("invalid_arguments")
    uids = [getattr(args, name, None) for name in ("uid", "datasource", "folder_uid", "dashboard_uid")]
    if any(uid is not None and not UID.fullmatch(uid) for uid in uids):
        raise SafeError("invalid_arguments")
    if args.command == "search" and (
            (args.query is None and args.folder_uid is None)
            or (args.query is not None and (not SEARCH_TEXT.fullmatch(args.query) or not args.query.strip()))
            or (args.page is not None and not 1 <= args.page <= MAX_SEARCH_PAGE)
            or (args.tag is not None and (not SEARCH_TEXT.fullmatch(args.tag) or not args.tag.strip()))):
        raise SafeError("invalid_arguments")
    if args.command == "alerts" and args.group_next_token is not None and (
            args.uid is not None or not NEXT_TOKEN.fullmatch(args.group_next_token)):
        raise SafeError("invalid_arguments")
    if args.command == "silences" and args.id is not None and not SILENCE_ID.fullmatch(args.id):
        raise SafeError("invalid_arguments")
    if getattr(args, "panel", None) is not None and not 1 <= args.panel <= 2**31 - 1:
        raise SafeError("invalid_arguments")
    limit = MAX_RENDER_RANGE_MS if args.command == "render" else MAX_RANGE_MS
    if args.command in ("query", "annotations", "render") and (
            not 0 <= args.from_ms < args.to_ms <= 253402300799999 or args.to_ms - args.from_ms > limit):
        raise SafeError("invalid_arguments")
    if args.command == "render" and (len(variables) + len(encoded_variables) > MAX_VARIABLES
                                     or not all(VARIABLE.fullmatch(item) for item in variables)):
        raise SafeError("invalid_arguments")
    if args.command == "render":
        # Preserve order across literal and encoded values, including repeated
        # names Grafana uses for multi-selection. Encoding is transport only.
        args.variables = [value if flag == '--var' else _decode_render_variable(value)
                          for flag, value in zip(argv[1::2], argv[2::2], strict=True)
                          if flag in ('--var', '--var-base64')]
        args.width = RENDER_WIDTH if args.width is None else args.width
        args.height = RENDER_HEIGHT if args.height is None else args.height
        if not MIN_RENDER_WIDTH <= args.width <= MAX_RENDER_WIDTH or not MIN_RENDER_HEIGHT <= args.height <= MAX_RENDER_HEIGHT:
            raise SafeError("invalid_arguments")
    if args.command == "query":
        minimum_interval = max(1000, math.ceil((args.to_ms - args.from_ms) / MAX_DATA_POINTS))
        if ((args.interval_ms is not None and not minimum_interval <= args.interval_ms <= MAX_RANGE_MS)
                or (args.rate_interval_ms is not None and (
                    args.kind != "prometheus" or not 1000 <= args.rate_interval_ms <= MAX_RANGE_MS))):
            raise SafeError("invalid_arguments")
        args.mode, args.output = args.mode or "range", args.output or "full"
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
        if not args.expr.strip() or len(args.expr) > MAX_EXPRESSION:
            raise SafeError("unresolved_or_invalid_expression")
        # Multi-line PromQL/LogQL is whitespace to the backend; other control characters are refused.
        if any(ord(char) < 32 and char not in "\t\n\r" for char in args.expr):
            raise SafeError("invalid_arguments")
        args.original_expr, args.substitutions, args.backend_expanded = args.expr, {}, []
        args.expr = _resolve_expression(args)
        unresolved = MACRO.sub(lambda match: "" if match.group(0) in args.backend_expanded else match.group(0), args.expr)
        if len(args.expr) > MAX_EXPRESSION or TEMPLATE.search(unresolved):
            raise SafeError("unresolved_or_invalid_expression")
        args.interval_ms = args.interval_ms or minimum_interval
    return args


def _decode_render_variable(value):
    """Decode one bounded scalar name=value without loosening literal argv rules."""
    try:
        if len(value) > 624:
            raise ValueError()
        raw = base64.b64decode(value, validate=True)
        if base64.b64encode(raw).decode('ascii') != value:
            raise ValueError()
        decoded = raw.decode('utf-8', errors='strict')
        name, separator, literal = decoded.partition('=')
        if not separator or not valid_variable(name, literal):
            raise ValueError()
        return decoded
    except (ValueError, UnicodeError):
        raise SafeError('invalid_arguments') from None


def valid_variable(name, value):
    """One scalar dashboard variable: an identifier name and 1-100 printable characters."""
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,63}", name) is not None and 1 <= len(value) <= 100 and value.isprintable()


def _resolve_expression(args):
    """Substitute explicit interval inputs; leave the other exact built-ins to the Prometheus backend.

    Loki keeps local range substitution and needs an explicit interval, as before.
    """
    milliseconds = args.to_ms - args.from_ms
    seconds = str(milliseconds // 1000) + (f".{milliseconds % 1000:03d}".rstrip("0") if milliseconds % 1000 else "")
    replacements = {}
    if args.kind == "loki":
        replacements = {"__range": f"{milliseconds // 1000}s" if milliseconds % 1000 == 0 else f"{milliseconds}ms",
                        "__range_s": seconds, "__range_ms": str(milliseconds)}
    if args.interval_ms is not None:
        replacements.update({"__interval": f"{args.interval_ms}ms", "__interval_ms": str(args.interval_ms)})
    if args.rate_interval_ms is not None:
        replacements.update({"__rate_interval": f"{args.rate_interval_ms}ms",
                             "__rate_interval_ms": str(args.rate_interval_ms)})

    def replace(match):
        name = match.group(1) or match.group(2)
        replacement = replacements.get(name)
        if replacement is None:
            if args.kind == "prometheus" and name in BACKEND_MACROS and match.group(0) not in args.backend_expanded:
                args.backend_expanded.append(match.group(0))
            return match.group(0)
        args.substitutions[match.group(0)] = replacement
        return replacement

    return MACRO.sub(replace, args.expr)


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
    # One open that follows no final symlink (and cannot hang on a FIFO); check and read that descriptor.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return environ
    except OSError:
        raise SafeError("invalid_settings_file") from None
    try:
        with open(descriptor, "rb") as handle:
            if os.name == "posix":
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode):
                    raise SafeError("invalid_settings_file")
                if not _private(info, os.getuid()):
                    raise SafeError("insecure_settings_file")
            raw = handle.read(MAX_SETTINGS_FILE + 1)
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

    # Called as transport(request), or with limit= and timeout= for a bounded image.
    transport: Callable[..., tuple[int, bytes]]
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
            raise SafeError("redirect_rejected", status)
        if status < 200 or status >= 300:
            raise SafeError("http_error", status)
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

    def image(self, path, width=RENDER_WIDTH, height=RENDER_HEIGHT):
        """GET one bounded PNG at the fixed render size; return its bytes or raise SafeError."""
        request = Request(self.base + path, headers={"Accept": "image/png", "Authorization": self.authorization,
                                                     "X-Grafana-Org-Id": str(self.organization)}, method="GET")
        try:
            status, raw = self.transport(request, limit=MAX_IMAGE, timeout=RENDER_TIMEOUT)
        except SafeError:
            raise
        except Exception:
            raise SafeError("request_failed") from None
        if 300 <= status < 400:
            raise SafeError("redirect_rejected", status)
        if status == 429:
            raise SafeError("renderer_busy", status)
        if status < 200 or status >= 300:
            raise SafeError("http_error", status)
        if len(raw) > MAX_IMAGE:
            raise SafeError("response_too_large")
        # A login page or error body served with 200 is not an image.
        if raw[:8] != PNG_SIGNATURE or raw[12:16] != b"IHDR" or len(raw) < 24:
            raise SafeError("invalid_image")
        # Grafana answers its own concurrency limit or an unavailable renderer with a stock PNG under HTTP 200.
        dimensions = (int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big"))
        if dimensions == (526, 202) or dimensions != (width, height):
            raise SafeError("renderer_placeholder")
        return raw


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


def http_transport(request, limit=MAX_RESPONSE, timeout=TIMEOUT):
    """No ambient proxies, redirects, netrc, custom trust bypass or credential files."""
    opener = build_opener(ProxyHandler({}), HTTPSHandler(context=ssl.create_default_context()), _NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read(limit + 1)
    except HTTPError as error:
        # Never read/echo HTTP error bodies or exception text (which can contain auth).
        status = error.code
        error.close()
        return status, b""


def _app_platform_dashboard(grafana, uid, version):
    """GET one `/apis` dashboard object at `version`; return its spec, metadata and stored version."""
    namespace = "default" if grafana.organization == 1 else f"org-{grafana.organization}"
    resource = grafana.read(f"/apis/dashboard.grafana.app/{version}/namespaces/{namespace}/dashboards/{uid}")
    metadata, spec, status = resource.get("metadata"), resource.get("spec"), resource.get("status")
    if (resource.get("kind") != "Dashboard" or resource.get("apiVersion") != "dashboard.grafana.app/" + version
            or not isinstance(metadata, dict) or metadata.get("name") != uid
            or metadata.get("namespace") != namespace or not isinstance(spec, dict)):
        raise SafeError("invalid_dashboard_response")
    conversion = status.get("conversion") if isinstance(status, dict) else None
    conversion = conversion if isinstance(conversion, dict) else {}
    if conversion.get("failed"):
        raise SafeError("dashboard_conversion_failed")
    # A read at the stored version carries no conversion status.
    stored = conversion.get("storedVersion") if isinstance(conversion.get("storedVersion"), str) else version
    return resource, namespace, stored


def _load_dashboard(grafana, uid):
    """Read the legacy model and the stored version; a V2-stored dashboard is read natively.

    The legacy read of a V2-stored dashboard is a silent Classic down-conversion (tabs become
    rows), so the stored version comes from a v0alpha1 `/apis` read's conversion status.
    Returns the stored `dashboard`, legacy `meta`, `model`, and for V2 the mapped `panel_view`.
    """
    response = grafana.read("/api/dashboards/uid/" + uid)
    dashboard, meta = response.get("dashboard"), response.get("meta")
    if not isinstance(dashboard, dict) or not isinstance(meta, dict):
        raise SafeError("invalid_dashboard_response")
    stored = meta["apiVersion"].rsplit("/", 1)[-1] if isinstance(meta.get("apiVersion"), str) else ""
    model = {"format": "classic", "stored_version": None, "storage_check": "not_needed"}
    if not stored.startswith("v2") and not any(key in dashboard for key in ("elements", "layout", "spec")):
        if dashboard.get("uid") != uid:
            raise SafeError("invalid_dashboard_response")
        try:
            stored = _app_platform_dashboard(grafana, uid, "v0alpha1")[2]
            model.update(stored_version=stored, storage_check="verified")
        except SafeError as error:
            # Older or restricted instances: the legacy model stays usable, its storage unknown.
            model.update(storage_check="unavailable", **({"http_status": error.status} if error.status else {}))
            return {"dashboard": dashboard, "meta": meta, "model": model}
        if not stored.startswith("v2"):
            return {"dashboard": dashboard, "meta": meta, "model": model}
    version = stored if stored in ("v2beta1", "v2") else "v2beta1"
    try:
        resource, namespace, stored = _app_platform_dashboard(grafana, uid, version)
    except SafeError as error:
        if str(error) in ("invalid_dashboard_response", "dashboard_conversion_failed"):
            raise
        raise SafeError("v2_dashboard_unavailable", error.status) from None
    return {"dashboard": resource, "meta": meta,
            "panel_view": v2_panel_view(resource["spec"], uid=uid, version=resource["metadata"].get("generation")),
            "model": {"format": "v2", "stored_version": stored, "api_version": version, "namespace": namespace,
                      "storage_check": "verified", "panel_view": "mapped_from_v2"}}


def _v2_datasource(kind):
    """V2 queries name the datasource type as `group` and the datasource UID as `datasource.name`."""
    source = kind.get("datasource") if isinstance(kind.get("datasource"), dict) else {}
    return {key: value for key, value in (("type", kind.get("group")), ("uid", source.get("name"))) if isinstance(value, str)}


def _v2_panel(name, element, repeat, context):
    if not isinstance(element, dict) or not isinstance(element.get("spec"), dict):
        raise SafeError("invalid_panel_tree")
    body = element["spec"]
    panel = {"id": body.get("id"), "title": body.get("title"), "_element": name, "_parent_context": context}
    if element.get("kind") == "LibraryPanel":
        panel.update(type="library-panel", libraryPanel=body.get("libraryPanel"))
    elif element.get("kind") == "Panel":
        viz, data = body.get("vizConfig"), body.get("data")
        if (not isinstance(viz, dict) or not isinstance(viz.get("spec", {}), dict)
                or not isinstance(data, dict) or not isinstance(data.get("spec"), dict)):
            raise SafeError("invalid_panel_tree")
        viz_spec, group = viz.get("spec", {}), data["spec"]
        panel.update({key: value for key, value in (
            ("type", viz.get("group")), ("description", body.get("description")),
            ("options", viz_spec.get("options")), ("fieldConfig", viz_spec.get("fieldConfig"))) if value is not None})
        options, queries = group.get("queryOptions") or {}, group.get("queries") or []
        transformations = group.get("transformations") or []
        if not isinstance(options, dict) or not isinstance(queries, list) or not isinstance(transformations, list):
            raise SafeError("invalid_panel_tree")
        panel.update({key: options[key] for key in ("interval", "maxDataPoints", "timeFrom", "timeShift", "timeCompare") if key in options})
        if transformations:
            panel["transformations"] = [{"id": item.get("group"), **(item.get("spec") or {})} if isinstance(item, dict) else item
                                        for item in transformations]
        panel["targets"] = []
        for query in queries:
            spec = query.get("spec") if isinstance(query, dict) else None
            data_query = spec.get("query") if isinstance(spec, dict) else None
            if not isinstance(data_query, dict) or not isinstance(data_query.get("spec", {}), dict):
                raise SafeError("invalid_panel_tree")
            panel["targets"].append({**data_query.get("spec", {}), "refId": spec.get("refId", "A"),
                                     "hide": spec.get("hidden") is True, "datasource": _v2_datasource(data_query)})
    else:
        raise SafeError("unsupported_dashboard_model")
    if repeat:
        panel["repeat"] = repeat.get("value") if isinstance(repeat, dict) else repeat
    return panel


def v2_panel_view(spec, *, uid=None, version=None):
    """Map a V2 spec onto the Classic panel/target/templating shape the planner and checks read.

    Panels keep their numeric `id` plus `_element` (the element name); repeated or variable-scoped
    rows and tabs become `_parent_context`. Layouts are flattened in document order.
    """
    elements, layout, variables = spec.get("elements"), spec.get("layout"), spec.get("variables", [])
    if not isinstance(elements, dict) or not isinstance(layout, dict) or not isinstance(variables, list):
        raise SafeError("invalid_panel_tree")
    panels, pending = [], [(layout, [], 0)]
    while pending:
        node, context, depth = pending.pop()
        if depth > MAX_LAYOUT_DEPTH or not isinstance(node, dict) or not isinstance(node.get("spec"), dict):
            raise SafeError("invalid_panel_tree")
        key = V2_LAYOUTS.get(node.get("kind"))
        if key is None:
            raise SafeError("unsupported_dashboard_model")
        children = node["spec"].get(key)
        if not isinstance(children, list) or not all(isinstance(child, dict) and isinstance(child.get("spec"), dict)
                                                     for child in children):
            raise SafeError("invalid_panel_tree")
        if key == "items":
            for item in children:
                reference = item["spec"].get("element")
                name = reference.get("name") if isinstance(reference, dict) else None
                if not isinstance(name, str) or name not in elements:
                    raise SafeError("invalid_panel_tree")
                panels.append(_v2_panel(name, elements[name], item["spec"].get("repeat"), context))
        else:
            for section in reversed(children):
                scoped = [name for name, value in (("repeat", section["spec"].get("repeat")),
                                                   ("scopedVars", section["spec"].get("variables"))) if value]
                pending.append((section["spec"].get("layout"), context + scoped, depth + 1))
    templating = []
    for variable in variables:
        if not isinstance(variable, dict) or not isinstance(variable.get("spec"), dict):
            raise SafeError("invalid_panel_tree")
        body = variable["spec"]
        item = {key: body[key] for key in ("name", "label", "current", "multi", "includeAll", "allValue", "filters", "hide")
                if key in body}
        item["type"] = V2_VARIABLES.get(variable.get("kind"), "unknown")
        query = body.get("query")
        if isinstance(query, dict):
            item.update(query=query.get("spec") if isinstance(query.get("spec"), dict) else {}, datasource=_v2_datasource(query))
        elif query is not None:
            item["query"] = query
        if variable.get("kind") in ("AdhocVariable", "GroupByVariable"):
            item["datasource"] = _v2_datasource(variable)
        templating.append(item)
    view = {"uid": uid, "version": version, "title": spec.get("title"), "tags": spec.get("tags") or [],
            "templating": {"list": templating}, "panels": panels}
    time_settings = spec.get("timeSettings")
    if isinstance(time_settings, dict):
        view.update(time={"from": time_settings.get("from"), "to": time_settings.get("to")},
                    timezone=time_settings.get("timezone"))
    return view


def _dashboard(grafana, args):
    loaded = _load_dashboard(grafana, args.uid)
    model = loaded.get("panel_view", loaded["dashboard"])
    if args.panel is not None:
        panel = _panel(model, args.panel)
        if panel is None:
            raise SafeError("panel_not_found")
        # Raw configuration: variables, queries and transformations have not been executed/resolved.
        context = {name: model.get(name) for name in ("uid", "version", "title", "time", "timezone", "templating")}
        result = {"ok": True, "operation": "dashboard", "dashboard": context, "panel_id": args.panel,
                  "panel": panel, "coverage": "configuration_only"}
    else:
        result = {"ok": True, "operation": "dashboard", "dashboard": loaded["dashboard"], "meta": loaded["meta"],
                  "coverage": "configuration_only"}
        if "panel_view" in loaded:
            result["panel_view"] = loaded["panel_view"]
    if "model" in loaded:
        result["model"] = loaded["model"]
    return result


def _query(grafana, args):
    datasource = grafana.read("/api/datasources/uid/" + args.datasource)
    if "orgId" in datasource and (type(datasource["orgId"]) is not int or datasource["orgId"] != grafana.organization):
        raise SafeError("organization_mismatch")
    if datasource.get("uid") != args.datasource or datasource.get("type") != args.kind:
        raise SafeError("datasource_mismatch")
    # Data source hints do not enforce the response size; the transport enforces MAX_RESPONSE.
    limits = {"maxDataPoints": MAX_DATA_POINTS, "intervalMs": args.interval_ms,
              "maxLines": MAX_LOG_LINES if args.kind == "loki" else None,
              "maxDataPointsEnforced": False, "maxResponseBytes": MAX_RESPONSE}
    query = {"refId": "A", "datasource": {"uid": args.datasource, "type": args.kind},
             "expr": args.expr, "maxDataPoints": limits["maxDataPoints"], "intervalMs": limits["intervalMs"]}
    if args.kind == "prometheus":
        query.update({"range": args.mode == "range", "instant": args.mode == "instant", "format": "time_series"})
    else:
        query.update({"queryType": args.mode, "maxLines": limits["maxLines"]})
    response = grafana.read("/api/ds/query", {"from": str(args.from_ms), "to": str(args.to_ms), "queries": [query]})
    results = response.get("results")
    if response.get("error") or not isinstance(results, dict) or set(results) != {"A"} or not isinstance(results["A"], dict):
        raise SafeError("query_failed")
    result_a = results["A"]
    if result_failed(result_a) or not isinstance(result_a.get("frames"), list):
        raise SafeError("query_failed")
    expression = {"original": args.original_expr, "resolved": args.expr, "substitutions": args.substitutions,
                  "backend_expanded": args.backend_expanded}
    if args.backend_expanded:
        # Expanded server-side from intervalMs/maxDataPoints here, not the panel's width or min interval.
        expression["panel_equivalence"] = "not_established"
    result = {"ok": True, "operation": "query", "datasource": args.datasource, "kind": args.kind,
              "from": str(args.from_ms), "to": str(args.to_ms), "mode": args.mode, "output": args.output,
              "evaluation_time_ms": args.to_ms if args.mode == "instant" else None, "expression": expression,
              "summary": _query_summary(result_a, response, args), "coverage": "not_established", "limits": limits}
    if args.output == "full":
        result["results"] = results
    return result


def result_failed(entry):
    """A `/api/ds/query` result entry that reports an error or a non-2xx status."""
    try:
        return bool(entry.get("error")) or int(entry.get("status", 200)) >= 400
    except (ValueError, TypeError, OverflowError):
        return True


def _finite(value):
    """JSON integers are finite; avoid float conversion overflow on large integers."""
    return type(value) is int or (type(value) is float and math.isfinite(value))


def frame_columns(frame):
    """Return supported wire columns plus a static refusal reason; never infer rows.

    Reader summaries, statistics, row inspection and threshold previews share this
    structural boundary. Callers still own stricter time, identity and size rules.
    """
    if not isinstance(frame, dict) or not isinstance(frame.get("schema"), dict) or not isinstance(frame.get("data"), dict):
        return None, "invalid_frame"
    # These wire encodings change values (including zero/null placeholders and timestamps).
    # Refuse them until decoded, rather than calculating plausible but incorrect statistics.
    if any(frame["data"].get(name) not in (None, {}, []) for name in ("entities", "bases", "factors", "enums", "nanos")):
        return None, "encoded_frame"
    meta = frame["schema"].get("meta")
    if isinstance(meta, dict) and meta.get("type") in ("numeric-long", "timeseries-long"):
        return None, "row_labelled_frame"
    fields, columns = frame["schema"].get("fields"), frame["data"].get("values")
    if not isinstance(fields, list) or not isinstance(columns, list) or len(fields) != len(columns):
        return None, "invalid_columns"
    if any(not isinstance(field, dict) or field.get("type") not in ("time", "number", "string", "boolean", "other")
           for field in fields):
        return None, "unsupported_fields"
    if any(not isinstance(column, list) for column in columns):
        return None, "invalid_columns"
    types = {field["type"] for field in fields}
    # Row labels can distinguish many series inside one numeric column. Logs without numeric
    # fields remain countable, but do not merge categorical metric rows into one series.
    if "number" in types and types & {"string", "boolean", "other"}:
        return None, "unsupported_fields"
    if len({len(column) for column in columns}) > 1:
        return None, "invalid_columns"
    return (fields, columns), None


def _time_summary(values, args, *, incomplete=False):
    finite = [value for value in values if _finite(value)]
    invalid = len(values) - len(finite)
    complete = bool(finite) and not invalid and not incomplete
    minimum, maximum = (min(finite), max(finite)) if finite else (None, None)
    outside = any(value < args.from_ms or value > args.to_ms for value in finite)
    mismatch = any(value != args.to_ms for value in finite)
    return {"timestamp_min_ms": minimum, "timestamp_max_ms": maximum, "timestamp_count": len(finite),
            "timestamp_invalid_count": invalid,
            "timestamp_status": "complete" if complete else "partial" if finite else "unavailable",
            "out_of_window": True if outside else False if complete else None,
            "instant_timestamp_mismatch": (True if mismatch else False if complete else None) if args.mode == "instant" else None}


def _numeric_summary(values):
    finite = [value for value in values if _finite(value)]
    nulls = sum(value is None for value in values)
    invalid = len(values) - len(finite) - nulls
    state = "unsupported" if invalid else "values" if finite else "all_null" if nulls else "empty"
    return {"point_count": len(values), "finite_count": len(finite), "null_count": nulls, "invalid_count": invalid,
            "state": state, "min": min(finite) if finite else None, "max": max(finite) if finite else None,
            # Last means returned row order, including a trailing null; it is not a dashboard reducer.
            "last": values[-1] if values and (_finite(values[-1]) or values[-1] is None) else None,
            "last_finite": finite[-1] if finite else None, "maxDataPoints_exceeded": len(values) > MAX_DATA_POINTS}


def _query_summary(result, response, args):
    """Observed wire data only. Detail caps do not change totals or discard full-mode results."""
    frames = result["frames"]
    summary = {"frame_count": len(frames), "summarized_frame_count": 0, "unsupported_frame_count": 0,
               "observed_row_count": 0, "observed_numeric_series_count": 0, "series": [], "series_limit": SUMMARY_LIMIT,
               "series_over_point_hint": 0, "frames_over_point_hint": 0, "notices": [], "notice_count": 0, "warnings": []}
    times, time_incomplete, invalid_values = [], False, False

    def notices(source, value):
        if value is None:
            return
        for notice in value if isinstance(value, list) else [value]:
            summary["notice_count"] += 1
            if len(summary["notices"]) < SUMMARY_LIMIT:
                summary["notices"].append({"source": source, "notice": notice})

    for name in ("notices", "warnings", "warning"):
        notices("response." + name, response.get(name))
        notices("results.A." + name, result.get(name))
    for index, frame in enumerate(frames):
        schema = frame.get("schema") if isinstance(frame, dict) else None
        meta = schema.get("meta") if isinstance(schema, dict) else None
        if isinstance(meta, dict):
            notices(f"frames[{index}].schema.meta.notices", meta.get("notices"))
        parsed, _reason = frame_columns(frame)
        if parsed is None:
            summary["unsupported_frame_count"] += 1
            time_incomplete = True
            continue
        fields, columns = parsed
        rows = len(columns[0]) if columns else 0
        summary["summarized_frame_count"] += 1
        summary["observed_row_count"] += rows
        summary["frames_over_point_hint"] += rows > MAX_DATA_POINTS
        time_fields = [column for field, column in zip(fields, columns, strict=False) if field["type"] == "time"]
        frame_times = [value for column in time_fields for value in column]
        times.extend(frame_times)
        time_incomplete |= bool(rows and not time_fields)
        time_summary = _time_summary(frame_times, args)
        invalid_values |= bool(time_summary["timestamp_invalid_count"])
        for field_index, (field, values) in enumerate(zip(fields, columns, strict=False)):
            if field["type"] != "number":
                continue
            summary["observed_numeric_series_count"] += 1
            stats = _numeric_summary(values)
            invalid_values |= bool(stats["invalid_count"])
            summary["series_over_point_hint"] += stats["maxDataPoints_exceeded"]
            if len(summary["series"]) < SUMMARY_LIMIT:
                summary["series"].append({"frame_index": index, "field_index": field_index,
                                          "name": field.get("name"), "labels": field.get("labels"), **stats, **time_summary})
    unsupported = summary["unsupported_frame_count"]
    summary.update({"status": "unsupported" if unsupported and not summary["summarized_frame_count"] else
                    "partial" if unsupported or invalid_values else "complete",
                    "row_count": None if unsupported else summary["observed_row_count"],
                    "numeric_series_count": None if unsupported else summary["observed_numeric_series_count"],
                    "series_truncated": summary["observed_numeric_series_count"] > len(summary["series"]),
                    "notices_truncated": summary["notice_count"] > len(summary["notices"]),
                    **_time_summary(times, args, incomplete=time_incomplete)})
    for condition, warning in ((unsupported, "unsupported_frame_shape"), (invalid_values, "unsupported_field_values"),
                               (summary["frames_over_point_hint"], "observed_frames_exceed_requested_point_hint"),
                               (summary["series_over_point_hint"], "observed_series_exceed_requested_point_hint"),
                               (summary["out_of_window"], "observed_timestamps_outside_requested_window"),
                               (summary["instant_timestamp_mismatch"], "observed_instant_timestamps_differ_from_requested_end")):
        if condition:
            summary["warnings"].append(warning)
    return summary


def _search(grafana, args):
    path = "/api/search?type=dash-db&limit=" + str(LIST_LIMIT)
    if args.query is not None:
        path += "&query=" + quote(args.query, safe="")
    if args.page is not None:
        path += "&page=" + str(args.page)
    if args.folder_uid is not None:
        path += "&folderUIDs=" + args.folder_uid
    if args.tag is not None:
        path += "&tag=" + quote(args.tag, safe="")
    items = grafana.items(path)
    if len(items) > LIST_LIMIT:
        raise SafeError("invalid_search_response")
    if args.folder_uid is not None and any(item.get("folderUid") != args.folder_uid for item in items):
        raise SafeError("folder_mismatch")
    page = args.page or 1
    full = len(items) == LIST_LIMIT
    # A full page only suggests a next request; permissions and contents may change between reads.
    return {"ok": True, "operation": "search", "query": args.query, "items": items,
            "page": page, "next_page": page + 1 if full and page < MAX_SEARCH_PAGE else None,
            "folder_uid": args.folder_uid, "tag": args.tag,
            "truncated": full, "coverage": "permission_scoped", "limits": {"limit": LIST_LIMIT, "maxPage": MAX_SEARCH_PAGE}}


def _alerts(grafana, args):
    if args.uid is not None:
        rule = grafana.read("/api/v1/provisioning/alert-rules/" + args.uid)
        if rule.get("uid") != args.uid:
            raise SafeError("alert_rule_mismatch")
        if "orgID" in rule and (type(rule["orgID"]) is not int or rule["orgID"] != grafana.organization):
            raise SafeError("organization_mismatch")
        return {"ok": True, "operation": "alerts", "uid": args.uid, "rule": rule, "coverage": "configuration_only"}
    path = "/api/prometheus/grafana/api/v1/rules?group_limit=" + str(LIST_LIMIT) + "&limit_alerts=" + str(ALERTS_PER_RULE)
    path += "&folder_uid=" + args.folder_uid if args.folder_uid else ""
    path += "&group_next_token=" + quote(args.group_next_token, safe="") if args.group_next_token else ""
    response = grafana.read(path)
    data = response.get("data")
    if response.get("status") != "success" or not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        raise SafeError("query_failed")
    groups = _items(data["groups"], grafana.organization)
    # Grafana answers an inaccessible or unknown folder_uid with every visible folder.
    if args.folder_uid and any(group.get("folderUid") != args.folder_uid for group in groups):
        raise SafeError("folder_mismatch")
    # Each rule's instance list stops at limit_alerts; its totals count every instance by state
    # (an errored instance can count twice, so this can over-report but not miss a cut list).
    cut = []
    for group in groups:
        for rule in group.get("rules") if isinstance(group.get("rules"), list) else []:
            alerts, totals = (rule.get("alerts"), rule.get("totals")) if isinstance(rule, dict) else (None, None)
            total = sum(v for v in totals.values() if type(v) is int) if isinstance(totals, dict) else None
            if isinstance(alerts, list) and len(alerts) >= ALERTS_PER_RULE and (total is None or total > len(alerts)):
                cut.append({"uid": rule.get("uid"), "returned": len(alerts), "total": total})
    token = data.get("groupNextToken")
    token = token if isinstance(token, str) and token else None
    return {"ok": True, "operation": "alerts", "folder_uid": args.folder_uid, "groups": groups,
            "totals": data.get("totals"), "truncated": bool(token or cut), "groups_truncated": bool(token),
            "group_next_token": token if token and NEXT_TOKEN.fullmatch(token) else None,
            "instances_truncated_rules": cut[:LIST_LIMIT], "instances_truncated_rule_count": len(cut),
            "coverage": "permission_scoped", "limits": {"group_limit": LIST_LIMIT, "limit_alerts": ALERTS_PER_RULE}}


def _annotations(grafana, args):
    path = "/api/annotations?from=" + str(args.from_ms) + "&to=" + str(args.to_ms) + "&limit=" + str(LIST_LIMIT)
    items = grafana.items(path + ("&dashboardUID=" + args.dashboard_uid if args.dashboard_uid else ""))
    return {"ok": True, "operation": "annotations", "from": str(args.from_ms), "to": str(args.to_ms),
            "dashboard_uid": args.dashboard_uid, "items": items, "truncated": len(items) >= LIST_LIMIT,
            "coverage": "permission_scoped", "limits": {"limit": LIST_LIMIT}}


def _silences(grafana, args):
    if args.id is not None:
        silence = grafana.read("/api/alertmanager/grafana/api/v2/silence/" + args.id)
        if silence.get("id") != args.id:
            raise SafeError("silence_mismatch")
        return {"ok": True, "operation": "silences", "id": args.id, "silence": silence, "coverage": "permission_scoped"}
    return {"ok": True, "operation": "silences", "silences": grafana.items("/api/alertmanager/grafana/api/v2/silences"),
            "coverage": "permission_scoped"}


def dashboard_panels(dashboard):
    """Validate a whole Classic tree (or mapped V2 view); return its non-row panels in order.

    Each panel gains `_parent_context`: the repeat/scopedVars keys of enclosing rows or sections.
    """
    if any(key in dashboard for key in ("elements", "layout", "spec")):
        raise SafeError("unsupported_dashboard_model")
    top = dashboard.get("panels")
    if not isinstance(top, list):
        raise SafeError("invalid_panel_tree")
    pending, ids, found = [(panel, []) for panel in reversed(top)], set(), []
    while pending:
        panel, inherited = pending.pop()
        if (not isinstance(panel, dict) or type(panel.get("id")) is not int
                or not 1 <= panel["id"] <= 2**31 - 1 or not isinstance(panel.get("type"), str) or not panel["type"]):
            raise SafeError("invalid_panel_tree")
        if panel["id"] in ids:
            raise SafeError("ambiguous_panel_id")
        ids.add(panel["id"])
        if "panels" in panel and (panel["type"] != "row" or not isinstance(panel["panels"], list)):
            raise SafeError("invalid_panel_tree")
        if panel["type"] == "row":
            context = inherited + [key for key in ("repeat", "scopedVars") if panel.get(key)]
            pending.extend((child, context) for child in reversed(panel.get("panels", [])))
        else:
            stored = panel.get("_parent_context")
            own = [key for key in ("repeat", "scopedVars") if isinstance(stored, list) and key in stored]
            found.append({**panel, "_parent_context": own + inherited})
    return found


def _panel(dashboard, panel_id):
    """Select a unique non-row panel only after validating the complete panel tree."""
    for panel in dashboard_panels(dashboard):
        if panel["id"] == panel_id:
            return {key: value for key, value in panel.items() if key != "_parent_context" or value}
    return None


def _render_dir():
    """A fixed per-user capture directory, never TMPDIR or the working directory; day-old renders go."""
    try:
        path = Path.home() / ".cache" / "save-toolkit" / "grafana-renders"
    except RuntimeError:
        raise SafeError("capture_directory_unavailable") from None
    if not path.is_absolute():
        raise SafeError("capture_directory_unavailable")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    cutoff = time.time() - 24 * 60 * 60
    for old in path.glob("grafana-render-*.png"):
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass
    return path


def _save_image(raw):
    """An owner-only file (mkstemp) in the per-user capture directory."""
    descriptor, name = tempfile.mkstemp(prefix="grafana-render-", suffix=".png", dir=_render_dir())
    with open(descriptor, "wb") as handle:
        handle.write(raw)
    return name


def _render(grafana, args):
    loaded = _load_dashboard(grafana, args.uid)
    meta, dashboard = loaded["meta"], loaded.get("panel_view", loaded["dashboard"])
    panel = _panel(dashboard, args.panel)
    if panel is None:
        raise SafeError("panel_not_found")
    slug = meta["slug"] if isinstance(meta.get("slug"), str) and SLUG.fullmatch(meta["slug"]) else "_"
    params = [("orgId", grafana.organization), ("panelId", args.panel), ("from", args.from_ms), ("to", args.to_ms),
              ("width", args.width), ("height", args.height), ("scale", 1), ("tz", "UTC"),
              ("timeout", RENDER_TIMEOUT - 5)]
    params += [("var-" + name, value) for name, _, value in (item.partition("=") for item in args.variables)]
    raw = grafana.image("/render/d-solo/" + args.uid + "/" + slug + "?" + urlencode(params), args.width, args.height)
    return {"ok": True, "operation": "render", "uid": args.uid, "panel_id": args.panel,
            "panel_title": panel.get("title"), "dashboard_version": dashboard.get("version"),
            "from": str(args.from_ms), "to": str(args.to_ms), "tz": "UTC", "variables": args.variables,
            "image_path": _save_image(raw), "image_bytes": len(raw), "image_sha256": hashlib.sha256(raw).hexdigest(),
            "width": args.width, "height": args.height,
            # The PNG is evidence only once the caller opens and inspects it.
            "coverage": "image_uninspected",
            "limits": {"maxBytes": MAX_IMAGE, "timeoutSeconds": RENDER_TIMEOUT, "maxRangeMs": MAX_RENDER_RANGE_MS,
                       "minWidth": MIN_RENDER_WIDTH, "maxWidth": MAX_RENDER_WIDTH,
                       "minHeight": MIN_RENDER_HEIGHT, "maxHeight": MAX_RENDER_HEIGHT}}


_OPERATIONS = {"dashboard": _dashboard, "query": _query, "search": _search, "alerts": _alerts,
               "annotations": _annotations, "silences": _silences, "render": _render}


def run(args, environ, transport):
    grafana, secrets = _connect(_settings(environ, _settings_file()), transport)
    current_org = grafana.read("/api/org")
    if type(current_org.get("id")) is not int or current_org["id"] != grafana.organization:
        raise SafeError("organization_mismatch")
    result = _OPERATIONS[args.command](grafana, args)
    result.update({"grafana_url": grafana.base, "organization_id": grafana.organization,
                   "retrieved_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z")})
    masked = _mask(result, secrets)
    if args.command == "render" and masked.get("image_path") != result["image_path"]:
        # A configured Basic credential appears in the path; a masked path cannot be opened.
        Path(result["image_path"]).unlink(missing_ok=True)
        raise SafeError("image_path_masked")
    return masked


def main(argv=None, *, environ=None, transport=None, output=None):
    output = sys.stdout if output is None else output
    try:
        result = run(parse_args(sys.argv[1:] if argv is None else argv), os.environ if environ is None else environ,
                     http_transport if transport is None else transport)
        serialized = json.dumps(result, ensure_ascii=True, allow_nan=False)
        code = 0
    except SafeError as error:
        failure = {"ok": False, "error": str(error)}
        if error.status is not None:
            failure["http_status"] = error.status
        serialized, code = json.dumps(failure), 2
    except Exception:
        # Process boundary: prevent unexpected library errors exposing credential material.
        serialized, code = '{"ok": false, "error": "request_failed"}', 2
    output.write(serialized + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
