"""Export a verified atlas as a standalone, offline browser dashboard."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fleet_atlas_v2_artifacts import OUTPUT, VerifiedDocument, extraction, verify
from fleet_atlas_v2_format import fact_record
from fleet_atlas_v2_sources import is_source

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_suffix(".html")


def payload(document: VerifiedDocument) -> dict:
    if not isinstance(document, VerifiedDocument):
        raise TypeError("dashboard export requires a verified atlas")
    records = [fact_record(fact, document.facts) for fact in document.facts.graph.facts]
    paths = {span["path"] for fact in records for span in fact["citations"]}
    snapshot = document.facts.snapshot
    return {
        "revision": document.revision,
        "treeDigest": snapshot.tree_digest,
        "exportedAt": datetime.now(UTC).isoformat(),
        "nodes": [{"id": node.id, "path": node.path, "selector": node.selector, "type": node.type}
                  for node in document.facts.graph.nodes],
        "facts": records,
        "sources": {path: snapshot.source(path).text for path in sorted(paths)},
        # Use the same line boundaries as Span/Source, including CR and Unicode
        # separators; JavaScript's usual CRLF regex is not Python splitlines().
        "sourceLines": {path: list(snapshot.source(path).lines) for path in sorted(paths)},
    }


def render(data: dict, template: str) -> str:
    if template.count("__ATLAS_DATA__") != 1 or template.count("__ATLAS_CSP__") != 1:
        raise ValueError("dashboard template must contain one data and one CSP placeholder")
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # JSON lives inside an HTML raw-text element: JSON escaping alone does not
    # stop </script>, nor an HTML comment from changing the parser's state.
    for literal, escaped in (("&", "\\u0026"), ("<", "\\u003c"), (">", "\\u003e"),
                             ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        encoded = encoded.replace(literal, escaped)
    hashes = []
    for attributes, body in re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", template, re.S | re.I):
        if re.search(r'type\s*=\s*[\"\']application/json[\"\']', attributes, re.I):
            continue
        hashes.append("'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'")
    policy = ("default-src 'none'; script-src " + " ".join(hashes) +
              "; style-src 'unsafe-inline'; img-src data:; connect-src 'none'; "
              "object-src 'none'; base-uri 'none'; form-action 'none'; frame-src 'none'")
    return template.replace("__ATLAS_CSP__", policy).replace("__ATLAS_DATA__", encoded)


def export(root: Path, output: Path, *, force: bool = False, loader=extraction) -> Path:
    root = root.resolve(strict=True)
    output = output.resolve()
    if output.suffix.lower() != ".html":
        raise ValueError("dashboard output must be an .html file")
    if output.is_relative_to(root):
        relative = output.relative_to(root)
        if is_source(relative.as_posix()) or relative.is_relative_to(OUTPUT):
            raise ValueError("dashboard output must be outside canonical sources and atlas artifacts")
    if output.exists() and not force:
        raise ValueError("output already exists; use --force to replace a generated dashboard")
    document = verify(root, loader)
    template = TEMPLATE.read_text(encoding="utf-8")
    data = payload(document)
    data["rendererDigest"] = hashlib.sha256(Path(__file__).read_bytes() + template.encode()).hexdigest()
    page = render(data, template)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation by default also protects against a concurrent export.
    with output.open("w" if force else "x", encoding="utf-8", newline="\n") as handle:
        handle.write(page)
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    output = args.output or args.root / ".eval-runs/fleet-atlas-dashboard/index.html"
    try:
        result = export(args.root, output, force=args.force)
    except (OSError, ValueError, TypeError) as error:
        print(f"Dashboard export refused: {error}", file=sys.stderr)
        return 1
    print(f"Dashboard: {result}")
    print("Verified at export. Opening this offline snapshot does not recheck workspace freshness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
