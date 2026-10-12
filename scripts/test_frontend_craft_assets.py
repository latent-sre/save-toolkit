"""Exercise frontend-craft's starting files: the SPA serving contract against a correct server and
each break it names, the dependency-free helpers' own node tests, and the parametric theme's
WCAG AA contrast in both schemes at every brand hue."""

from __future__ import annotations

import json
import math
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
ASSETS = ROOT / "skills/frontend-craft/assets"
CONTRACT = ASSETS / "serving-contract.mjs"
THEME = ASSETS / "theme.css"

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
    "missing_cache": None,
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
                    self.send_header(name, value)
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
                return self.reply(404, b"Not Found", "text/plain", settings["missing_cache"])
            return self.reply(200, INDEX, "text/html; charset=utf-8", settings["index_cache"])

    return Handler


@contextmanager
def serving(**breaks: object) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), server_for(**breaks))
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def run_contract(**env: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    assert node, "node must be available to run the frontend serving contract"
    environment = {k: v for k, v in os.environ.items() if k not in {"BASE_URL", "API_PREFIX", "RUNTIME_CONFIG_PATH"}}
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
            {"missing_cache": "public, max-age=31536000, immutable"},
            ["a missing static file is a 404, not the app"],
            id="missing-chunk-cached-for-a-year",
        ),
        pytest.param(
            {"security_headers": False},
            ["index.html refuses framing and content sniffing"],
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
    assert node, "node must be available to run the frontend helper contracts"
    out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    major, minor = out.lstrip("v").split(".")[:2]
    return int(major), int(minor)


@pytest.mark.parametrize(
    ("suite", "cases"),
    [("problem.test.ts", 9), ("idempotent-write.test.ts", 9), ("runtime-config.test.ts", 7)],
)
def test_the_typescript_helper_contracts_pass(suite: str, cases: int) -> None:
    # Type stripping runs .ts files without a build from Node 22.18; CI's runner image ships 22.23.
    if node_version() < (22, 18):
        pytest.skip(f"{suite} needs Node 22.18+ (type stripping); older node found")
    node = shutil.which("node")
    assert node
    command = [node, "--test", "--test-reporter=tap", "--test-timeout=20000", suite]
    result = subprocess.run(command, cwd=ASSETS, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"# pass {cases}" in result.stdout and "# fail 0" in result.stdout, result.stdout


def test_the_pcf_profile_writes_config_json_from_the_environment(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is needed to run the PCF .profile starter")
    (tmp_path / "public").mkdir()
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "UI_ENVIRONMENT": "staging",
        "UI_API_BASE_URL": "/v1",
        "UI_LOG_SEARCH_URL_TEMPLATE": 'https://logs.example.internal/search?q="{request_id}"',
    }
    result = subprocess.run([bash, str(ASSETS / "pcf/profile.sh")], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    written = json.loads((tmp_path / "public/config.json").read_text(encoding="utf-8"))
    assert written == {
        "environment": "staging",
        "apiBaseUrl": "/v1",
        "logSearchUrlTemplate": 'https://logs.example.internal/search?q="{request_id}"',
    }
    missing = subprocess.run(
        [bash, str(ASSETS / "pcf/profile.sh")],
        env={**os.environ, "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert missing.returncode != 0 and "UI_ENVIRONMENT must be set" in missing.stderr
    control = subprocess.run(
        [bash, str(ASSETS / "pcf/profile.sh")],
        env={**env, "UI_ENVIRONMENT": "staging\r"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert control.returncode != 0 and "must not contain control characters" in control.stderr
    for url in ("https://api.example.internal/v1", "//api.example.internal/v1"):
        elsewhere = subprocess.run(
            [bash, str(ASSETS / "pcf/profile.sh")],
            env={**env, "UI_API_BASE_URL": url},
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert elsewhere.returncode != 0 and "UI_API_BASE_URL must" in elsewhere.stderr, url


# --- The parametric theme: OKLCH tokens evaluated for both schemes, contrast checked at every hue ---


def oklch_to_linear_srgb(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """OKLCH to linear sRGB, gamut-mapped by reducing chroma until the colour fits, as browsers do."""

    def convert(c: float) -> tuple[float, float, float]:
        a = c * math.cos(math.radians(hue))
        b = c * math.sin(math.radians(hue))
        l_ = lightness + 0.3963377774 * a + 0.2158037573 * b
        m_ = lightness - 0.1055613458 * a - 0.0638541728 * b
        s_ = lightness - 0.0894841775 * a - 1.2914855480 * b
        long, medium, short = l_**3, m_**3, s_**3
        return (
            4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short,
            -1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short,
            -0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short,
        )

    def inside(rgb: tuple[float, float, float]) -> bool:
        return all(-1e-6 <= v <= 1 + 1e-6 for v in rgb)

    if inside(convert(chroma)):
        return tuple(min(1.0, max(0.0, v)) for v in convert(chroma))  # type: ignore[return-value]
    low, high = 0.0, chroma
    for _ in range(30):
        mid = (low + high) / 2
        if inside(convert(mid)):
            low = mid
        else:
            high = mid
    return tuple(min(1.0, max(0.0, v)) for v in convert(low))  # type: ignore[return-value]


def luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def encode(channel: float) -> float:
    """Linear sRGB to the gamma-encoded value a browser composites with."""
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def decode(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def over(
    top: tuple[float, float, float], alpha: float, bottom: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Alpha-composite `top` over `bottom` the way a browser paints an oklch(... / alpha) background:
    the blend happens on gamma-encoded sRGB channels, and the result is decoded back to linear for
    luminance. Blending the linear channels over-reports a translucent pill's contrast by about 0.3."""
    blended = (encode(t) * alpha + encode(u) * (1 - alpha) for t, u in zip(top, bottom, strict=True))
    return tuple(decode(v) for v in blended)  # type: ignore[return-value]


def split_top_level(text: str, separator: str) -> list[str]:
    out, depth, current = [], 0, ""
    for ch in text:
        depth += ch == "("
        depth -= ch == ")"
        if ch == separator and depth == 0:
            if current.strip():
                out.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        out.append(current.strip())
    return out


class Theme:
    """The custom properties the theme's first :root rule declares, resolved for one scheme."""

    def __init__(self, scheme: str, knobs: dict[str, str] | None = None) -> None:
        css = THEME.read_text(encoding="utf-8")
        match = re.search(r":root\s*\{(.*?)\n\s*\}", css, re.S)
        assert match, "theme.css has no :root rule"
        self.vars = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", match.group(1)))
        self.vars.update(knobs or {})
        self.scheme = scheme

    def resolve(self, expr: str) -> str:
        previous = None
        while previous != expr:
            previous = expr
            expr = re.sub(r"var\((--[\w-]+)\)", lambda m: self.vars[m.group(1)], expr)
        return expr

    def number(self, expr: str) -> float:
        expr = self.resolve(expr).strip()
        inner = re.fullmatch(r"calc\((.*)\)", expr)
        if inner:
            expr = inner.group(1)
        assert re.fullmatch(r"[\d.\s*+/()-]+", expr), f"unsupported numeric expression {expr}"
        return float(eval(expr))  # digits and arithmetic only, asserted above

    def colour(self, name: str) -> tuple[tuple[float, float, float], float]:
        expr = self.resolve(self.vars[name]).strip()
        scheme = re.fullmatch(r"light-dark\((.*)\)", expr, re.S)
        if scheme:
            light, dark = split_top_level(scheme.group(1), ",")
            expr = light if self.scheme == "light" else dark
        oklch = re.fullmatch(r"oklch\((.*)\)", expr.strip(), re.S)
        assert oklch, f"{name} is not an oklch() colour in the {self.scheme} scheme: {expr}"
        body, alpha = oklch.group(1), 1.0
        if "/" in body:
            body, alpha_text = body.rsplit("/", 1)
            alpha = float(alpha_text)
        lightness, chroma, hue = (self.number(part) for part in split_top_level(body, " "))
        return oklch_to_linear_srgb(lightness, chroma, hue), alpha


SURFACES = ("--surface-page", "--surface-panel", "--surface-raised", "--surface-hover", "--surface-sunken")
STATUSES = ("ok", "warn", "critical", "info", "unknown")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("hue", range(0, 360, 15))
def test_the_theme_meets_aa_contrast_at_every_brand_hue(scheme: str, hue: int) -> None:
    theme = Theme(scheme, {"--brand-hue": str(hue)})
    failures = []
    for surface in SURFACES:
        background, _ = theme.colour(surface)
        for ink in ("--text", "--text-muted", "--text-faint", "--brand"):
            ratio = contrast(theme.colour(ink)[0], background)
            if ratio < 4.5:
                failures.append(f"{ink} on {surface}: {ratio:.2f}")
        for status in STATUSES:
            pill_rgb, alpha = theme.colour(f"--status-{status}-bg")
            ratio = contrast(theme.colour(f"--status-{status}")[0], over(pill_rgb, alpha, background))
            if ratio < 4.5:
                failures.append(f"status-{status} on its pill over {surface}: {ratio:.2f}")
    for fill, ink in (("--brand", "--on-brand"), ("--status-critical", "--on-critical")):
        ratio = contrast(theme.colour(ink)[0], theme.colour(fill)[0])
        if ratio < 4.5:
            failures.append(f"{ink} on {fill}: {ratio:.2f}")
    assert not failures, f"{scheme} scheme at brand hue {hue} below WCAG AA: " + "; ".join(failures)


def test_the_theme_carries_both_bridges_and_the_knobs() -> None:
    css = THEME.read_text(encoding="utf-8")
    for knob in (
        "--brand-hue",
        "--brand-chroma",
        "--surface-hue",
        "--surface-chroma",
        "--radius",
        "--density",
        "--font-ui",
        "--font-code",
    ):
        assert re.search(rf"^\s*{re.escape(knob)}:", css, re.M), f"theme.css lacks the {knob} knob"
    assert "@theme inline" in css, "theme.css lacks the Tailwind v4 bridge"
    for token in (
        "--background",
        "--primary",
        "--primary-foreground",
        "--destructive",
        "--border",
        "--ring",
        "--sidebar",
    ):
        assert re.search(rf"^\s*{re.escape(token)}:\s*var\(", css, re.M), f"theme.css's shadcn bridge lacks {token}"
    assert "color-scheme: light dark" in css and ':root[data-theme="dark"]' in css
