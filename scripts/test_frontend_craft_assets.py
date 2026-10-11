"""Exercise frontend-craft's shipped assets: the SPA serving contract against a correct server and
each break it names, the problem and idempotent-write helpers' own node tests, and the console
theme's contrast in both themes."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "skills/frontend-craft/assets/serving-contract.mjs"
THEME = ROOT / "skills/frontend-craft/assets/console-theme.css"

BUNDLE_PATH = "/assets/index-3f9a1c.js"
INDEX = (
    b'<!doctype html><html><head><script type="module" src="/assets/index-3f9a1c.js"></script>'
    b'</head><body><div id="app"></div></body></html>'
)

CORRECT = {
    "index_cache": "no-cache",
    "config_cache": "no-cache",
    "fallback_everything": False,
    "api_routed": True,
    "security_headers": True,
}
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'",
    "X-Content-Type-Options": "nosniff",
}


def server_for(**breaks: object) -> type[BaseHTTPRequestHandler]:
    settings = {**CORRECT, **breaks}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:
            pass

        def reply(self, status: int, body: bytes, content_type: str, cache: object = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            if cache:
                self.send_header("Cache-Control", str(cache))
            if settings["security_headers"] and content_type.startswith("text/html"):
                for name, value in SECURITY_HEADERS.items():
                    configured: object = value
                    if name == "Content-Security-Policy":
                        configured = settings.get("csp", value)
                        if self.path != "/" and "deep_csp" in settings:
                            configured = settings["deep_csp"]
                    elif self.path != "/" and "deep_sniff" in settings:
                        configured = settings["deep_sniff"]
                    if configured is not None:
                        for header_value in configured if isinstance(configured, list) else [configured]:
                            self.send_header(name, str(header_value))
                if settings.get("report_only"):
                    self.send_header("Content-Security-Policy-Report-Only", str(settings["report_only"]))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]
            if path == BUNDLE_PATH:
                return self.reply(200, b"console.log('app')", "text/javascript", "max-age=31536000, immutable")
            if path == "/config.json":
                return self.reply(200, b'{"apiBaseUrl": "/v1"}', "application/json", settings["config_cache"])
            if path.startswith("/v1/") and settings["api_routed"]:
                return self.reply(404, b'{"status": 404}', "application/problem+json")
            if "." in path.rsplit("/", 1)[-1] and not settings["fallback_everything"]:
                return self.reply(404, b"Not Found", "text/plain")
            return self.reply(200, INDEX, "text/html; charset=utf-8", settings["index_cache"])

    return Handler


@contextmanager
def serving(**breaks: object) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), server_for(**breaks))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def run_contract(**env: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    assert node, "node must be available to run the frontend serving contract"
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in {"BASE_URL", "API_PREFIX", "RUNTIME_CONFIG_PATH", "FRAME_ANCESTORS_EXPECTED"}
    }
    # The runner's own timeout ends the test file's process, so a hang fails fast without orphaned pipes.
    command = [node, "--test", "--test-reporter=tap", "--test-timeout=20000", str(CONTRACT)]
    return subprocess.run(
        command, env={**environment, **env}, capture_output=True, text=True, encoding="utf-8", timeout=120
    )


def failed_checks(result: subprocess.CompletedProcess[str]) -> list[str]:
    return sorted(line.split(" - ", 1)[1] for line in result.stdout.splitlines() if line.startswith("not ok"))


def test_a_correct_server_passes_every_check() -> None:
    with serving() as base:
        result = run_contract(BASE_URL=base, API_PREFIX="/v1/", RUNTIME_CONFIG_PATH="/config.json")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# pass 7" in result.stdout, result.stdout


@pytest.mark.parametrize(
    ("breaks", "expected"),
    [
        (
            {"csp": "frame-ancestors *"},
            ["a deep link serves the app and revalidates", "index.html refuses framing and content sniffing"],
        ),
        ({"deep_csp": "frame-ancestors *"}, ["a deep link serves the app and revalidates"]),
    ],
)
def test_permissive_framing_is_rejected(breaks: dict[str, object], expected: list[str]) -> None:
    with serving(**breaks) as base:
        result = run_contract(BASE_URL=base, API_PREFIX="/v1/", RUNTIME_CONFIG_PATH="/config.json")
    assert result.returncode != 0, result.stdout
    assert failed_checks(result) == expected, result.stdout


@pytest.mark.parametrize(
    "csp",
    [
        None,
        "default-src 'none'",
        "frame-ancestors https:",
        "frame-ancestors 'self'",
        "frame-ancestors https://embed.example",
        "frame-ancestors",
        "frame-ancestors 'none' https://embed.example",
        "frame-ancestors *; frame-ancestors 'none'",
        "frame-ancestors 'none'; frame-ancestors *",
        "frame-ancestors 'none', frame-ancestors *",
        ["frame-ancestors *", "frame-ancestors 'none'"],
        ["frame-ancestors 'none'", "frame-ancestors 'none'"],
        "frame-ancestors https://*.example",
        "frame-ancestors https://embed.example/path",
        "frame-ancestors 'nonce-abc'",
        "frame-ancestors https://127.1",
        "frame-ancestors http://127.0.0.1:8080",
        "frame-ancestors https://embed.example:99999",
    ],
)
def test_default_framing_requires_no_embedding(csp: object) -> None:
    with serving(csp=csp) as base:
        result = run_contract(BASE_URL=base)
    assert result.returncode != 0, result.stdout
    assert failed_checks(result) == [
        "a deep link serves the app and revalidates",
        "index.html refuses framing and content sniffing",
    ], result.stdout
    assert "frame-ancestors" in result.stdout, result.stdout


def test_report_only_cannot_replace_an_enforced_policy() -> None:
    with serving(csp=None, report_only="frame-ancestors 'none'") as base:
        result = run_contract(BASE_URL=base)
    assert result.returncode != 0, result.stdout
    assert "report-only is insufficient" in result.stdout, result.stdout
    assert len(failed_checks(result)) == 2, result.stdout


@pytest.mark.parametrize(
    ("csp", "expected"),
    [
        ("default-src 'self'; FRAME-ANCESTORS\t'NONE'; object-src 'none'", "'none'"),
        ("frame-ancestors 'self'", "'self'"),
        ("frame-ancestors https://embed.example", "https://embed.example"),
        (
            "frame-ancestors HTTPS://Embed.Example:443 'self' https://other.example:8443",
            "https://other.example:8443 https://embed.example 'self'",
        ),
        ("frame-ancestors http://localhost:8080", "http://localhost:8080"),
        ("frame-ancestors https://two--dashes.example", "https://two--dashes.example"),
    ],
)
def test_supported_explicit_framing_expectations_pass(csp: str, expected: str) -> None:
    with serving(csp=csp) as base:
        result = run_contract(
            BASE_URL=base, API_PREFIX="/v1/", RUNTIME_CONFIG_PATH="/config.json", FRAME_ANCESTORS_EXPECTED=expected
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# pass 7" in result.stdout, result.stdout


@pytest.mark.parametrize(
    "csp",
    [
        "frame-ancestors 'none'",
        "frame-ancestors https://other.example",
        "frame-ancestors https://embed.example https://other.example",
        "frame-ancestors *",
        ["frame-ancestors https://embed.example", "frame-ancestors https://other.example"],
    ],
)
def test_explicit_embedding_must_match_on_each_html_route(csp: object) -> None:
    with serving(csp="frame-ancestors https://embed.example", deep_csp=csp) as base:
        result = run_contract(BASE_URL=base, FRAME_ANCESTORS_EXPECTED="https://embed.example")
    assert result.returncode != 0, result.stdout
    assert failed_checks(result) == ["a deep link serves the app and revalidates"], result.stdout


@pytest.mark.parametrize(
    "expected", ["", "*", "https:", "https://*.example", "'none' 'self'", "https://embed.example/path"]
)
def test_unsupported_framing_configuration_fails_clearly(expected: str) -> None:
    with serving() as base:
        result = run_contract(BASE_URL=base, FRAME_ANCESTORS_EXPECTED=expected)
    assert result.returncode != 0, result.stdout
    assert "FRAME_ANCESTORS_EXPECTED" in result.stdout + result.stderr


def test_deep_link_content_sniffing_header_is_required() -> None:
    with serving(deep_sniff=None) as base:
        result = run_contract(BASE_URL=base)
    assert result.returncode != 0, result.stdout
    assert failed_checks(result) == ["a deep link serves the app and revalidates"], result.stdout
    assert "X-Content-Type-Options" in result.stdout, result.stdout


@pytest.mark.parametrize(
    ("breaks", "expected"),
    [
        pytest.param(
            {"fallback_everything": True, "api_routed": False},
            ["a missing static file is a 404, not the app", "an unknown API path is not the app"],
            id="pushstate-rewrites-every-missing-path",
        ),
        pytest.param(
            {"index_cache": "max-age=3600"},
            ["a deep link serves the app and revalidates", "index.html is the app and revalidates"],
            id="html-cached-for-an-hour",
        ),
        pytest.param({"config_cache": None}, ["runtime configuration is fresh JSON"], id="config-without-no-cache"),
        pytest.param(
            {"security_headers": False},
            ["a deep link serves the app and revalidates", "index.html refuses framing and content sniffing"],
            id="html-without-security-headers",
        ),
    ],
)
def test_each_named_break_fails_its_own_check(breaks: dict[str, object], expected: list[str]) -> None:
    with serving(**breaks) as base:
        result = run_contract(BASE_URL=base, API_PREFIX="/v1/", RUNTIME_CONFIG_PATH="/config.json")
    assert result.returncode != 0, result.stdout
    assert failed_checks(result) == expected, result.stdout


def test_unset_optional_checks_are_skipped() -> None:
    with serving(api_routed=False, config_cache=None) as base:
        result = run_contract(BASE_URL=base)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# skipped 2" in result.stdout, result.stdout


def test_a_missing_base_url_fails() -> None:
    result = run_contract()
    assert result.returncode != 0
    assert "Set BASE_URL" in result.stdout + result.stderr


def node_version() -> tuple[int, int]:
    node = shutil.which("node")
    assert node, "node must be available to run the frontend problem contract"
    out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    major, minor = out.lstrip("v").split(".")[:2]
    return int(major), int(minor)


@pytest.mark.parametrize(("suite", "cases"), [("problem.test.ts", 6), ("idempotent-write.test.ts", 8)])
def test_the_typescript_helper_contracts_pass(suite: str, cases: int) -> None:
    # Type stripping runs .ts files without a build from Node 22.18; CI's runner image ships 22.23.
    if node_version() < (22, 18):
        pytest.skip(f"{suite} needs Node 22.18+ (type stripping); older node found")
    node = shutil.which("node")
    assert node
    command = [node, "--test", "--test-reporter=tap", "--test-timeout=20000", suite]
    result = subprocess.run(command, cwd=CONTRACT.parent, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"# pass {cases}" in result.stdout and "# fail 0" in result.stdout, result.stdout


def theme_tokens(selector: str) -> dict[str, str]:
    """The custom properties one rule of the console theme declares, by its exact selector."""
    css = THEME.read_text(encoding="utf-8")
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"console-theme.css has no rule for {selector}"
    return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", match.group(1)))


def rgb(value: str) -> tuple[float, float, float, float]:
    value = value.strip()
    if value.startswith("#"):
        return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16), 1.0
    parts = re.match(r"rgb\(\s*(\d+)\s+(\d+)\s+(\d+)\s*/\s*([\d.]+)\s*\)", value)
    assert parts, f"unparsed colour {value}"
    return float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])


def over(top: str, bottom: str) -> tuple[float, float, float]:
    r, g, b, a = rgb(top)
    br, bg, bb, _ = rgb(bottom)
    return r * a + br * (1 - a), g * a + bg * (1 - a), b * a + bb * (1 - a)


def contrast(fg: tuple[float, ...], bg: tuple[float, ...]) -> float:
    def luminance(c: tuple[float, ...]) -> float:
        channels = [x / 255 for x in c[:3]]
        lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in channels]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    light, dark = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


THEMES = {"dark": ":root", "light": ':root[data-theme="light"]'}


@pytest.mark.parametrize("theme", sorted(THEMES))
def test_console_theme_meets_aa_contrast(theme: str) -> None:
    t = theme_tokens(THEMES[theme])
    failures = []
    for surface in ("surface-page", "surface-panel", "surface-raised"):
        for text in ("text", "text-muted", "accent"):
            ratio = contrast(rgb(t[f"--{text}"]), rgb(t[f"--{surface}"]))
            if ratio < 4.5:
                failures.append(f"{text} on {surface}: {ratio:.2f}")
        for status in ("ok", "warn", "critical", "unknown", "progress"):
            pill = over(t[f"--status-{status}-bg"], t[f"--{surface}"])
            ratio = contrast(rgb(t[f"--status-{status}"]), pill)
            if ratio < 4.5:
                failures.append(f"status-{status} on its pill over {surface}: {ratio:.2f}")
    for fill, ink in (("accent", "on-accent"), ("status-critical", "on-critical")):
        ratio = contrast(rgb(t[f"--{ink}"]), rgb(t[f"--{fill}"]))
        if ratio < 4.5:
            failures.append(f"{ink} on {fill}: {ratio:.2f}")
    assert not failures, f"{theme} theme below WCAG AA: " + "; ".join(failures)


def test_the_os_light_theme_matches_the_explicit_light_theme() -> None:
    css = THEME.read_text(encoding="utf-8")
    media = re.search(r":root:not\(\[data-theme\]\)\s*\{([^}]*)\}", css)
    assert media
    following_os = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", media.group(1)))
    assert following_os == theme_tokens(THEMES["light"])
