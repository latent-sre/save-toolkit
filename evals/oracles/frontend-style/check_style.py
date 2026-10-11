"""Grade that the production build ships styling: a page that renders in browser defaults is not done.

Builds the candidate with its own Vite into a temporary directory and counts the bytes of
stylesheet it emits (CSS files plus inline <style> in index.html). Exit 10 is a candidate failure
(the build fails, or it ships less than MIN_BYTES of CSS); any other error is the oracle's.
A crude floor by design: it separates an unstyled page (0 bytes) from a styled one, and the
rendered screenshots carry the judgement of how good the styling is. Styling written only as
inline style attributes or CSS-in-JS emits no stylesheet and fails here, which the skill's
token-based approach does not do."""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_BYTES = 1500


def main() -> int:
    vite = Path("node_modules/vite/bin/vite.js")
    if not vite.is_file():
        raise RuntimeError("node_modules/vite is missing; the install step did not run")
    with tempfile.TemporaryDirectory(prefix="style-probe-") as out:
        result = subprocess.run(
            ["node", str(vite), "build", "--outDir", out, "--emptyOutDir", "--logLevel", "error"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            print("the production build failed:\n" + (result.stdout + result.stderr)[-3000:])
            return 10
        sheets = sorted(Path(out).rglob("*.css"))
        css_bytes = sum(p.stat().st_size for p in sheets)
        index = Path(out) / "index.html"
        inline = re.findall(r"<style[^>]*>(.*?)</style>", index.read_text(encoding="utf-8"), re.S) if index.is_file() else []
        inline_bytes = sum(len(block.encode()) for block in inline)
        total = css_bytes + inline_bytes
        print(f"stylesheets: {[p.name for p in sheets]}; css {css_bytes} bytes, inline {inline_bytes} bytes")
        if total < MIN_BYTES:
            print(f"the build ships {total} bytes of CSS (floor {MIN_BYTES}): the page renders in browser defaults")
            return 10
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
