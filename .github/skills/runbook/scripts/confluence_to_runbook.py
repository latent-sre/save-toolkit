#!/usr/bin/env python3
"""Convert a human-supplied Confluence page export into a DRAFT runbook.

Mechanical assistance for the import flow in ../references/confluence-import.md — a HUMAN (or the
software-engineer agent) runs this on an exported page; scribe then edits the draft into a reviewable runbook.
The script never fetches anything: its input is a file the human already exported. The REST v2
page JSON (`?body-format=view`) converts best, because it carries the title, version, and modified
date beside the body; view/export HTML is next; storage-format XHTML is handled best-effort, with
its macro elements counted as losses rather than mangled.

The draft retains source sections, links and image references, marks commands unverified, and
reports unsupported content and uncopied attachments. It never fetches linked resources or turns
an import into verification. Covered by scripts/test_confluence_import.py.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit

# Template slot order mirrors assets/runbook-template.md; headings must match it byte-for-byte so
# a converted draft diffs cleanly against a hand-copied template.
SLOTS = (
    "Purpose & scope",
    "Trigger",
    "Prerequisites",
    "Triage / first checks",
    "Procedure",
    "Verification",
    "Rollback / cleanup",
    "Escalation",
    "Communication",
)

# Source-heading keywords → template slot. Each keyword must start a word in the lowercased heading
# ("fix" matches "Fix it", never "prefix"); first hit wins in this order. Escalation and
# Communication come first because their headings often carry procedure or alert words ("Escalation
# process", "Alert contacts"). Deliberately narrow: a wrong guess buries content in the wrong slot,
# while a miss lands it — visibly — in "Imported content (unmapped)". Err toward the miss.
SLOT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Escalation", ("escalat", "on-call", "on call", "paging", "contact", "support")),
    ("Communication", ("communicat", "notif", "stakeholder", "comms")),
    ("Trigger", ("when to use", "trigger", "symptom", "alert")),
    ("Prerequisites", ("before you start", "prerequisite", "requirement", "access", "tooling", "tools")),
    ("Triage / first checks", ("triage", "first check", "diagnos", "impact")),
    ("Rollback / cleanup", ("rollback", "roll back", "revert", "undo", "backout", "back out", "cleanup")),
    ("Verification", ("verif", "validat", "confirm")),
    ("Procedure", ("step", "procedure", "resolution", "remediat", "instruction", "process", "fix")),
    ("Purpose & scope", ("purpose", "overview", "scope", "about", "goal", "summary")),
    ("References", ("reference", "related", "see also", "links")),
)
_SLOT_PATTERNS = tuple(
    (slot, re.compile("|".join(r"\b" + re.escape(keyword) for keyword in keywords)))
    for slot, keywords in SLOT_KEYWORDS
)

UNVERIFIED_MARK = "*Imported command — [unverified] until rehearsed on the target.*"
SERVICE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class _List:
    ordered: bool
    start: int | None
    step: int
    items: list[tuple[int | None, list[tuple[str, str]]]] = field(default_factory=list)

    def render(self) -> str:
        number = self.start if self.start is not None else (len(self.items) if self.step < 0 else 1)
        numbers = []
        for override, _ in self.items:
            number = override if override is not None else number
            numbers.append(number)
            number += self.step
        # Markdown renumbers reversed/discontinuous lists. Literal labels retain their meaning.
        literal = self.ordered and any(n != numbers[0] + i or not 0 <= n < 10**9
                                       for i, n in enumerate(numbers))
        output = []
        for number, (_, blocks) in zip(numbers, self.items):
            marker = f"- **{number}.** " if literal else (f"{number}. " if self.ordered else "- ")
            indent = " " * (2 if literal else len(marker))
            lines = "\n".join(render_blocks(blocks)).rstrip("\n").split("\n")
            output.append(marker + lines[0])
            output.extend(indent + line if line else "" for line in lines[1:])
            output.append("")
        return "\n".join(output).rstrip("\n")


def _integer(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


class _Extractor(HTMLParser):
    """Flatten the export into (heading, blocks) sections.

    Blocks are ("text", str) paragraphs/list items or ("code", str) literal blocks. Content inside
    Confluence namespace elements (<ac:...>/<ri:...>) or unsupported media is suppressed and counted:
    a macro's innards are parameters, not prose, and half-copied parameters masquerading as
    instructions are worse than a reported loss. Unclosed suppressed tags can leave suppression
    active; the failure direction is suppressing too much into the loss count, never inventing content.
    """

    def __init__(self, title: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        # A title supplied from outside the body (--title or the page JSON) is final: every body h1
        # then stays a section, except one that repeats the title.
        self.title = title or ""
        self._title_fixed = bool(title)
        self.title_source = "supplied" if title else None
        self.sections: list[tuple[str, list[tuple[str, str]]]] = [("", [])]
        self.macro_count = 0
        self.image_count = 0
        self.media_count = 0
        self.table_count = 0
        self.unusable_destinations = 0
        self._ac_depth = 0
        self._media: list[str] = []
        self._in_title = False
        self._heading: str | None = None
        self._pre: list[str] | None = None
        self._text: list[str] = []
        self._lists: list[_List] = []
        self._link: tuple[int, str] | None = None

    def _destination(self, value: str | None) -> str:
        value = (value or "").strip()
        try:
            valid = bool(value) and not any(ord(c) < 32 for c in value)
            valid = valid and urlsplit(value).scheme.lower() in {"", "http", "https", "mailto"}
        except ValueError:
            valid = False
        if not valid:
            self.unusable_destinations += 1
            return ""
        return quote(value, safe="/:#?&=%@+;,-._~")

    @staticmethod
    def _reference(label: str, destination: str) -> str:
        label = " ".join(label.split())
        label = re.sub(r"([\\`*_\[\]{}()#+.!|<>~-])", r"\\\1", label)
        return f"[{label}](<{destination}>)" if destination else label

    def _finish_link(self) -> None:
        if self._link is not None:
            start, destination = self._link
            label = " ".join(self._text[start:]).strip() or destination
            self._text[start:] = [self._reference(label, destination)]
            self._link = None

    def _flush_text(self) -> None:
        self._finish_link()
        text = " ".join(part for part in self._text if part).strip()
        self._text = []
        if not text:
            return
        self._append_block("text", text)

    def _append_block(self, kind: str, text: str) -> None:
        blocks = (self._lists[-1].items[-1][1] if self._lists and self._lists[-1].items
                  else self.sections[-1][1])
        blocks.append((kind, text))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"iframe", "object", "embed", "video", "audio", "svg"} and not self._ac_depth:
            self.media_count += 1
            if tag != "embed":  # Void media has no descendants to suppress.
                self._media.append(tag)
            return
        if self._media:
            return
        if ":" in tag:  # ac:/ri: namespace — Confluence macro machinery, not content
            if self._ac_depth == 0:
                self.macro_count += 1
            self._ac_depth += 1
            return
        if self._ac_depth:
            return
        if tag == "a" and self._pre is None and self._heading is None and not self._in_title:
            self._finish_link()
            if "href" in dict(attrs):
                self._link = (len(self._text), self._destination(dict(attrs)["href"]))
        elif tag == "img":
            self.image_count += 1
            attributes = dict(attrs)
            self._text.append("Image: " + self._reference(
                attributes.get("alt") or "image", self._destination(attributes.get("src"))
            ))
        if tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush_text()
            self._heading = ""
        elif tag == "pre":
            self._flush_text()
            self._pre = []
        elif tag == "table":
            self.table_count += 1
        elif tag in {"ul", "ol"}:
            self._flush_text()
            attributes = dict(attrs)
            self._lists.append(_List(tag == "ol", _integer(attributes.get("start")),
                                     -1 if "reversed" in attributes else 1))
        elif tag == "li":
            self._flush_text()
            if self._lists:
                self._lists[-1].items.append((_integer(dict(attrs).get("value")), []))
        elif tag in {"p", "tr", "br"}:
            if tag != "br" or self._link is None:
                self._flush_text()

    def handle_endtag(self, tag: str) -> None:
        if self._media:
            if tag == self._media[-1]:
                self._media.pop()
            return
        if ":" in tag:
            self._ac_depth = max(0, self._ac_depth - 1)
            return
        if self._ac_depth:
            return
        if tag == "a":
            self._finish_link()
        if tag == "title":
            self._in_title = False
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            heading = (self._heading or "").strip()
            self._heading = None
            if tag == "h1" and heading and not self.title:
                self.title = heading
                self.title_source = "first heading"
            elif heading and heading != self.title:
                self.sections.append((heading, []))
        elif tag == "pre" and self._pre is not None:
            code = "".join(self._pre).strip("\n")
            self._pre = None
            if code.strip():
                self._append_block("code", code)
        elif tag in {"ul", "ol"} and self._lists:
            self._flush_text()
            self._append_block("text", self._lists.pop().render())
        elif tag == "li":
            self._flush_text()
        elif tag in {"p", "tr"}:
            self._flush_text()

    def handle_data(self, data: str) -> None:
        if self._ac_depth or self._media:
            return
        if self._in_title:
            if not self._title_fixed:
                self.title += data.strip()
                self.title_source = "title element" if self.title else None
        elif self._heading is not None:
            self._heading += data
        elif self._pre is not None:
            self._pre.append(data)
        elif data.strip():
            self._text.append(re.sub(r"\s+", " ", data).strip())

    def close(self) -> None:
        self._flush_text()
        while self._lists:
            self._append_block("text", self._lists.pop().render())
        super().close()


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "imported-runbook"


def service_id(value: str) -> str:
    """Accept only the template's stable slug shape (assets/runbook-template.md)."""
    if not SERVICE_ID_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(
            "service-id must match ^[a-z0-9][a-z0-9-]*$"
        )
    return value


def owner(value: str) -> str:
    """Reject owner values that cannot satisfy the frontmatter schema."""
    if not value.strip():
        raise argparse.ArgumentTypeError(
            "owner must contain at least one non-whitespace character"
        )
    return value


def map_slot(heading: str) -> str | None:
    lowered = heading.lower()
    for slot, pattern in _SLOT_PATTERNS:
        if pattern.search(lowered):
            return slot
    return None


@dataclass
class _Page:
    html: str
    title: str | None = None
    version: str | None = None
    modified: str | None = None


def read_page(source: Path) -> _Page:
    """Read an export. A page JSON supplies its title, version, and modified date: Cloud REST v2
    `?body-format=view` (`version.createdAt`), or Data Center v1 `?expand=body.view,version`
    (`version.when`)."""
    text = source.read_text(encoding="utf-8", errors="replace")
    if source.suffix.lower() != ".json":
        return _Page(text)
    try:
        page = json.loads(text)
        body = page["body"]["view"]["value"]
    except (ValueError, KeyError, TypeError):
        raise ValueError(
            f"{source}: not a Confluence page JSON with body.view.value; export with ?body-format=view"
        ) from None
    if not isinstance(body, str) or not body.strip():
        raise ValueError(f"{source}: body.view.value is empty")
    version = page.get("version") if isinstance(page.get("version"), dict) else {}
    title = page.get("title")
    modified = version.get("createdAt") or version.get("when")
    return _Page(
        body,
        title.strip() if isinstance(title, str) and title.strip() else None,
        str(version["number"]) if "number" in version else None,
        str(modified) if modified else None,
    )


def render_blocks(blocks: list[tuple[str, str]]) -> list[str]:
    lines: list[str] = []
    for kind, value in blocks:
        if kind == "code":
            longest = max((len(match.group(0)) for match in re.finditer(r"`+", value)), default=0)
            fence = "`" * max(3, longest + 1)
            lines += [fence, value, fence, UNVERIFIED_MARK, ""]
        else:
            lines += [value, ""]
    return lines


def convert(source: Path, source_url: str | None, service_id: str, owner: str,
            title: str | None = None) -> tuple[str, str]:
    """Return (draft_markdown, stdout_report). Raises ValueError on an unusable page JSON."""
    page = read_page(source)
    parser = _Extractor(title or page.title)
    parser.feed(page.html)
    parser.close()

    title = " ".join((parser.title or source.stem).split())
    display_title = parser._reference(title, "")
    mapped: dict[str, list[str]] = {}
    unmapped: list[str] = []
    report: list[str] = [f"Converted: {source.name} — “{title}”"]
    if parser.title_source is None:
        report.append(f"  warning: no page title found; runbook_id comes from the file name "
                      f"“{source.stem}” — pass --title, or convert the page JSON")
    elif parser.title_source == "first heading":
        report.append("  warning: title taken from the first heading; if that heading is a section, "
                      "pass --title so it stays in the draft")
    for heading, blocks in parser.sections:
        if not blocks:
            continue
        slot = map_slot(heading) if heading else "Purpose & scope"
        body = render_blocks(blocks)
        if slot:
            note = f"*(from source section: “{heading}”)*" if heading else ""
            mapped.setdefault(slot, []).extend(([note, ""] if note else []) + body)
            report.append(f"  mapped   “{heading or '(intro)'}” -> {slot}")
        else:
            unmapped += [f"### {heading}", ""] + body
            report.append(f"  unmapped “{heading}” -> Imported content (unmapped)")

    today = datetime.date.today().isoformat()
    losses = [
        f"Confluence macros dropped (not convertible): {parser.macro_count}",
        f"Image attachments not copied: {parser.image_count} (references retained where usable)",
        f"Unsupported media dropped: {parser.media_count}",
        f"HTML tables flattened: {parser.table_count}",
        f"Unusable link or image destinations: {parser.unusable_destinations}",
    ]
    report.extend(f"  losses: {loss}" for loss in losses)

    lines = [
        "---",
        "schema_version: 1",
        f"runbook_id: {slugify(title)}",
        f"service_id: {json.dumps(service_id, ensure_ascii=False)}",
        "status: draft",
        "alert_names: []",
        f"owner: {json.dumps(owner, ensure_ascii=False)}",
        "severity: <P1|P2|P3|P4 / page | ticket>",
        "source_revision: <repository@short-commit or reviewed release identifier>",
        "last_reviewed: null",
        "last_verified: null",
        "verification_evidence: []",
        "version: 1",
        "---",
        "",
        f"# Runbook: {display_title}",
        "",
        "> **Imported draft.** Converted from a Confluence export; every command below is",
        "> `[unverified]` until rehearsed on the target. Fill applicable slots from evidence; mark",
        "> only genuinely inapplicable ones “n/a — why”. Missing applicable evidence stays",
        "> `[unverified]` with an owner and next check. See the runbook skill's Confluence-import",
        "> reference for the provenance rules this draft follows.",
        "",
    ]
    for slot in SLOTS:
        lines.append(f"## {slot}")
        lines.append("")
        content = mapped.get(slot)
        lines += content if content else ["<fill in — not present in the source page>", ""]
    lines += [
        "## Post-Incident",
        "",
        "- [ ] Append an Incident history row: version used, steps that held, steps that failed",
        "      or were missing, and the follow-up reference.",
        "- [ ] Create a learning disposition for every missing, contradicted, or newly useful step.",
        "",
        "## Incident history (living-runbook accretion)",
        "",
        "| Date (UTC) | Incident / drill ref | Version used | Steps that held | Steps that failed / were missing | Follow-up (disposition / PR or evidence reference) |",
        "|---|---|---|---|---|---|",
        "",
        "## Imported content (unmapped)",
        "",
    ]
    lines += unmapped if unmapped else ["(nothing — every source section mapped to a slot)", ""]
    lines += ["## References", ""]
    if "References" in mapped:
        lines += mapped["References"]
    lines += [
        "**Import provenance**",
        "",
        f"- Source file: `{source.name}`",
        f"- Source page title: “{display_title}”",
    ]
    if source_url:
        lines.append(f"- Source page URL: {json.dumps(source_url, ensure_ascii=False)}")
    lines += [
        f"- Source page version: {page.version or '<fill in — page history>'}",
        f"- Source page last modified: {page.modified or '<fill in — page history>'}",
        f"- Converted: {today}",
    ] + [f"- Conversion losses: {loss}" for loss in losses] + [""]
    return "\n".join(lines), "\n".join(report)


def main(argv: list[str] | None = None) -> int:
    # The report echoes source headings; captured stdout (an agent's Bash, CI, `> log`) may default
    # to a legacy code page that cannot encode them, and the draft is already written by then.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path,
                        help="exported Confluence page: REST v2 page JSON (preferred) or view/export HTML")
    parser.add_argument("-o", "--output", type=Path, required=True, help="draft runbook path to write")
    parser.add_argument("--source-url", default=None, help="original page URL for provenance")
    parser.add_argument("--service-id", required=True, type=service_id)
    parser.add_argument("--owner", default="<team/role>", type=owner)
    parser.add_argument("--title", default=None,
                        help="page title, when the export is a bare body fragment without one")
    parser.add_argument("--force", action="store_true",
                        help="replace an existing draft; a runbook's history rows are evidence")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"error: cannot read {args.source}", file=sys.stderr)
        return 1
    if args.output.exists() and not args.force:
        print(f"error: {args.output} exists; pass --force to replace it (its history rows are "
              f"evidence — convert to a new path and merge by hand instead)", file=sys.stderr)
        return 1
    try:
        draft, report = convert(args.source, args.source_url, args.service_id, args.owner,
                                args.title.strip() if args.title and args.title.strip() else None)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(draft, encoding="utf-8")
    except OSError as exc:
        print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
        return 1
    print(report)
    print(f"Draft written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
