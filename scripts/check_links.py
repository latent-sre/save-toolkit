#!/usr/bin/env python3
"""Check canonical skill/command frontmatter, links, and bundle reachability.

The authored plugin sources live at root-level skills/ and commands/. Generated
host adapters are consequences and are checked separately by the adapter generator.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):(?:[ \t]*(.*))?$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
CODE_PATH_RE = re.compile(
    r"`((?:references|assets|scripts)/[A-Za-z0-9._/-]+)`"
)
# Documents whose links must RESOLVE, checked for nothing else.
#
# Scope is the live authority set per docs/README.md -- the root guides, the rules index, the
# roadmap, the live reference contracts, and the accepted decisions. These were checked by nothing,
# and the rules index in particular exists to point a reader at a primary source, so a dead pointer
# there sends someone looking for authority to a file that is not there.
#
# Deliberately EXCLUDED: docs/superpowers/ and docs/reviews/. A historical plan or a dated review
# legitimately references files a later round deleted -- that is what makes it a record rather than
# a document. Failing the gate on ~31 such links would be noise, and noise in a gate is how a real
# failure gets scrolled past.
#
# Only resolvability is asserted. The skill rules applied elsewhere in this file (owned-root
# containment, code-span pointers must be Markdown links) are conventions for skill bundles; docs
# legitimately link across the whole repository and cite scripts inline.
LIVE_DOC_ROOTS = ("README.md", "CONTRIBUTING.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md")
LIVE_DOC_DIR_GLOBS = (("docs", "*.md"), ("docs/decisions", "*.md"))


EVIDENCE_BANNER_ANCHOR = "**Evidence default"


def _evidence_banner(text: str) -> str | None:
    """The contiguous blockquote containing the shared evidence-default banner, or None."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if EVIDENCE_BANNER_ANCHOR in line and line.lstrip().startswith(">"):
            block = []
            for candidate in lines[index:]:
                if not candidate.lstrip().startswith(">"):
                    break
                block.append(candidate.rstrip())
            return "\n".join(block)
    return None


def _check_evidence_banner(root: Path) -> list[str]:
    """Every skill's evidence-default banner must be byte-identical.

    All 29 currently hash the same, so this changes nothing today -- which is the point. The banner
    is duplicated 29 times by necessity (check_links forbids a relative link escaping a skill root,
    so a shared reference is architecturally impossible here), and nothing asserted the copies stay
    in step. One reworded copy would silently give one lane a different evidence contract from the
    rest of the fleet, and no other check in this repo would see it.
    """
    skill_root = root / "skills"
    if not skill_root.is_dir():
        return []
    banners: dict[str, str] = {}
    missing: list[str] = []
    failures: list[str] = []
    for skill_path in sorted(skill_root.glob("*/SKILL.md")):
        try:
            banner = _evidence_banner(skill_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue  # already reported by the reader in check()
        if banner is None:
            missing.append(skill_path.relative_to(root).as_posix())
            continue
        banners[skill_path.parent.name] = banner
    # Presence binds only once the banner is established as a convention. A tree where NO skill
    # carries one is a minimal fixture, not a fleet that lost its evidence contract, and failing
    # those would make this check a tax on every synthetic test rather than a guard on the real
    # tree. Where some skills carry it, the rest must.
    if banners:
        failures.extend(f"{path}: missing the evidence-default banner" for path in missing)
    distinct = sorted(set(banners.values()))
    if len(distinct) > 1:
        # Name the minority spelling(s): with 29 copies, reporting "they differ" is not actionable.
        majority = max(distinct, key=lambda text: sum(1 for v in banners.values() if v == text))
        for name, banner in sorted(banners.items()):
            if banner != majority:
                failures.append(
                    f"skills/{name}/SKILL.md: evidence-default banner differs from the other "
                    f"{len(banners) - 1} skills; reword all of them or none"
                )
    return failures


def _check_live_doc_links(root: Path) -> list[str]:
    failures: list[str] = []
    targets: list[Path] = [root / name for name in LIVE_DOC_ROOTS]
    for relative, pattern in LIVE_DOC_DIR_GLOBS:
        directory = root / relative
        if directory.is_dir():
            targets.extend(sorted(directory.glob(pattern)))
    for path in targets:
        if not path.is_file():
            continue
        try:
            text = _strip_fences(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            failures.append(f"{path.as_posix()}: cannot read UTF-8: {exc}")
            continue
        for _, raw in _links(text):
            target = _relative_target(raw)
            if target is None:
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            # Containment before existence. With enough `..` components a link resolves outside the
            # repository, where `.exists()` answers a question about the HOST rather than the repo:
            # a root README link to `../../etc/passwd` passes on Unix and fails on Windows, and
            # would not resolve for any consumer either way. An escaping link is always a defect,
            # so it is reported as one instead of being silently accepted when the host happens to
            # have that path.
            if not resolved.is_relative_to(root):
                failures.append(
                    f"{path.relative_to(root).as_posix()}: link {target!r} escapes the repository"
                )
            elif not resolved.exists():
                failures.append(
                    f"{path.relative_to(root).as_posix()}: dead link {target!r}"
                )
    return failures
ALLOWED_KEYS = {
    "name",
    "description",
    "argument-hint",
    "disable-model-invocation",
    "compatibility",
}
MANUAL_ONLY = {"pcf-deploy", "service-onboarding"}
YAML_NON_STRING = re.compile(
    r"^(?:"
    r"~|null|true|false|yes|no|on|off|"
    r"[-+]?(?:0|[1-9][0-9_]*|0o[0-7_]+|0x[0-9a-f_]+)|"
    r"[-+]?(?:(?:[0-9][0-9_]*)?\.[0-9_]+|[0-9][0-9_]*[eE][-+]?[0-9]+|\.inf|\.nan)|"
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[Tt ][0-9:.+\-Zz ]+)?"
    r")$",
    re.IGNORECASE,
)


def _strip_fences(text: str) -> str:
    kept = []
    fence = None
    for line in text.splitlines(keepends=True):
        match = re.match(r"^[ \t]*(```+|~~~+)", line)
        if match:
            marker = match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            kept.append("\n" if line.endswith(("\n", "\r")) else "")
        elif fence is None:
            kept.append(line)
        else:
            kept.append("\n" if line.endswith(("\n", "\r")) else "")
    return "".join(kept)


def _yaml_string(raw: str, where: str, failures: list[str]) -> str | None:
    raw = raw.strip()
    if not raw:
        failures.append(f"{where}: value must be one nonblank YAML string")
        return None
    if raw.startswith("[") or raw.startswith("{"):
        failures.append(f"{where}: value must be a string, not a collection")
        return None
    if raw.startswith('"'):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            failures.append(f"{where}: invalid quoted string")
            return None
        if not isinstance(value, str) or not value.strip():
            failures.append(f"{where}: value must be one nonblank YAML string")
            return None
        return value
    if raw.startswith("'"):
        if len(raw) < 2 or not raw.endswith("'"):
            failures.append(f"{where}: invalid quoted string")
            return None
        value = raw[1:-1].replace("''", "'")
        if not value.strip():
            failures.append(f"{where}: value must be one nonblank YAML string")
            return None
        return value
    if YAML_NON_STRING.fullmatch(raw):
        failures.append(f"{where}: value must be a YAML string, not an implicit scalar")
        return None
    return raw


def _frontmatter(text: str, path: Path) -> tuple[dict[str, str], str, list[str]]:
    failures: list[str] = []
    lines = text.splitlines()
    where = path.as_posix()
    if not lines or lines[0].strip() != "---":
        return {}, text, [f"{where}: missing frontmatter"]
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration:
        return {}, text, [f"{where}: unterminated frontmatter"]

    values: dict[str, str] = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("#"):
            index += 1
            continue
        match = KEY_RE.fullmatch(line)
        if not match:
            failures.append(f"{where}:{index + 1}: malformed top-level frontmatter")
            index += 1
            continue
        key, raw = match.group(1), (match.group(2) or "")
        if key in values:
            failures.append(f"{where}:{index + 1}: duplicate frontmatter key '{key}'")
        if raw in {">", ">-", "|", "|-"}:
            chunks = []
            index += 1
            while index < end and (lines[index].startswith((" ", "\t")) or not lines[index]):
                chunks.append(lines[index].strip())
                index += 1
            value = " ".join(chunk for chunk in chunks if chunk)
            values[key] = value
            continue
        values[key] = raw.strip()
        index += 1

    unknown = sorted(set(values) - ALLOWED_KEYS)
    if unknown:
        failures.append(f"{where}: unknown frontmatter key(s): {', '.join(unknown)}")
    body = "\n".join(lines[end + 1 :])
    return values, body, failures


def _check_skill_frontmatter(path: Path, text: str) -> tuple[str, list[str]]:
    values, body, failures = _frontmatter(text, path)
    where = path.as_posix()
    expected_name = path.parent.name
    name = _yaml_string(values.get("name", ""), f"{where}: name", failures)
    if name and (not NAME_RE.fullmatch(name) or name != expected_name):
        failures.append(
            f"{where}: name must be kebab-case and equal directory '{expected_name}'"
        )
    description = _yaml_string(
        values.get("description", ""), f"{where}: description", failures
    )
    if description:
        if len(description.encode("utf-8")) > 600:
            failures.append(f"{where}: description exceeds 600 UTF-8 bytes")
        if "Triggers:" not in description:
            failures.append(f"{where}: description is missing literal 'Triggers:'")
        else:
            trigger_text = description.split("Triggers:", 1)[1]
            triggers = re.findall(r"(['\"])(.+?)\1", trigger_text)
            if not 2 <= len(triggers) <= 4:
                failures.append(f"{where}: Triggers must contain 2-4 quoted user phrasings")
    if "argument-hint" in values:
        _yaml_string(values["argument-hint"], f"{where}: argument-hint", failures)
    if "compatibility" in values:
        _yaml_string(values["compatibility"], f"{where}: compatibility", failures)
    raw_manual_only = values.get("disable-model-invocation")
    if expected_name in MANUAL_ONLY:
        if raw_manual_only != "true":
            failures.append(
                f"{where}: manual-only skill must contain frontmatter "
                "disable-model-invocation: true"
            )
    elif raw_manual_only is not None:
        if raw_manual_only != "true":
            failures.append(f"{where}: disable-model-invocation must be boolean true")
        failures.append(
            f"{where}: only pcf-deploy and service-onboarding may disable model invocation"
        )
    return body, failures


def _links(text: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2).strip()) for match in LINK_RE.finditer(text)]


def _target(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("<") and ">" in raw:
        return raw[1 : raw.index(">")]
    return raw.split()[0]


def _relative_target(raw: str) -> str | None:
    target = unquote(_target(raw))
    if not target or target.startswith("#"):
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith(("/", "\\")):
        return None
    return target.split("#", 1)[0].split("?", 1)[0]


def _check_markdown(path: Path, text: str, owned_root: Path) -> list[str]:
    failures = []
    visible = _strip_fences(text)
    without_links = LINK_RE.sub("", visible)
    for match in CODE_PATH_RE.finditer(without_links):
        line = visible[: match.start()].count("\n") + 1
        failures.append(
            f"{path.as_posix()}:{line}: code-span pointer must be a Markdown link: {match.group(1)}"
        )
    for _label, raw_target in _links(visible):
        relative = _relative_target(raw_target)
        if relative is None:
            continue
        destination = path.parent / Path(relative.replace("/", os.sep))
        lexical_destination = Path(os.path.abspath(destination))
        try:
            lexical_destination.relative_to(owned_root.absolute())
        except ValueError:
            failures.append(
                f"{path.as_posix()}: relative link escapes owned skill root: '{relative}'"
            )
            continue
        if not destination.exists():
            failures.append(
                f"{path.as_posix()}: dead link '{relative}'"
            )
    return failures


def _bundle_files(skill_root: Path):
    for kind in ("references", "assets", "scripts"):
        base = skill_root / kind
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                yield path


def _check_direct_bundle_links(skill_path: Path, body: str) -> list[str]:
    failures = []
    skill_root = skill_path.parent
    visible = _strip_fences(body)
    links = _links(visible)
    resolved = set()
    for _label, raw_target in links:
        relative = _relative_target(raw_target)
        if relative is not None:
            try:
                resolved.add((skill_path.parent / relative).resolve().relative_to(skill_root.resolve()).as_posix())
            except ValueError:
                pass
    for bundle in _bundle_files(skill_root):
        relative = bundle.relative_to(skill_root).as_posix()
        if relative in resolved:
            continue
        failures.append(
            f"{skill_path.as_posix()}: bundled file not linked directly from SKILL.md body: {relative}"
        )
    return failures


def _check_guide(root: Path) -> list[str]:
    """Tie the AGENTS.md fleet guide to the tree it describes.

    Three silent-failure classes, none of which any other check sees:
      * CLAUDE.md loads AGENTS.md via an `@AGENTS.md` import; drop that line and the guide silently
        loads empty for every Claude session while both files still exist.
      * A renamed script or doc leaves the guide pointing at nothing — a dead Markdown link that
        fails nowhere at runtime.
      * An inline-code path token (`scripts/gate_a.py`, `docs/README.md`) that stops resolving after
        a rename reads as live guidance and isn't.

    Inline-code tokens are checked only when their FIRST segment is a real top-level repo entry.
    That is what keeps this from false-positiving on generic mentions (`references/`, `assets/`) and
    on skill-relative link labels (`` [`agent-authoring/references/roster.md`](skills/...) `` — the
    code span is the label, unresolvable from root, and correctly skipped).
    """
    failures: list[str] = []
    claude_md = root / "CLAUDE.md"
    if claude_md.is_file():
        # The import must be a real top-level line, not a fenced example or a prose mention — those
        # satisfy a naive substring test while the guide still loads empty. Strip fences and require
        # a standalone `@AGENTS.md` line.
        claude_body = _strip_fences(claude_md.read_text(encoding="utf-8"))
        if not any(line.strip() == "@AGENTS.md" for line in claude_body.splitlines()):
            failures.append(
                "CLAUDE.md: missing top-level '@AGENTS.md' import line; the fleet guide would load empty"
            )
    guide = root / "AGENTS.md"
    if not guide.is_file():
        return failures  # self-gate: a synthetic root without the guide has nothing to check
    visible = _strip_fences(guide.read_text(encoding="utf-8"))
    for _label, raw_target in _links(visible):
        relative = _relative_target(raw_target)
        if relative is None:
            continue
        if not (root / Path(relative.replace("/", os.sep))).exists():
            failures.append(f"AGENTS.md: dead link '{relative}'")
    for match in re.finditer(r"`([^`]+)`", visible):
        token = match.group(1).strip()
        if "/" not in token or any(ch in token for ch in " :*") or token.startswith(("/", "#", "~")):
            continue  # commands, namespaces (`save-toolkit:x`), globs, absolute/home paths
        clean = token.rstrip("/")
        first = clean.split("/", 1)[0]
        if first in (".", "..") or not (root / first).exists():
            continue  # first segment is not a repo-root entry: a generic or skill-relative mention
        if not (root / Path(clean.replace("/", os.sep))).exists():
            failures.append(f"AGENTS.md: inline-code path does not resolve: '{token}'")
    return failures


def check(root: Path = ROOT) -> list[str]:
    root = Path(root).resolve()
    failures: list[str] = []
    failures.extend(_check_guide(root))
    skill_root = root / "skills"
    if skill_root.is_dir():
        for skill_path in sorted(skill_root.glob("*/SKILL.md")):
            try:
                text = skill_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                failures.append(f"{skill_path.as_posix()}: cannot read UTF-8: {exc}")
                continue
            body, frontmatter_failures = _check_skill_frontmatter(skill_path, text)
            failures.extend(frontmatter_failures)
            failures.extend(_check_markdown(skill_path, body, skill_path.parent))
            failures.extend(_check_direct_bundle_links(skill_path, body))
            references = skill_path.parent / "references"
            if references.is_dir():
                for reference in sorted(references.rglob("*.md")):
                    try:
                        failures.extend(
                            _check_markdown(
                                reference,
                                reference.read_text(encoding="utf-8"),
                                skill_path.parent,
                            )
                        )
                    except (OSError, UnicodeError) as exc:
                        failures.append(f"{reference.as_posix()}: cannot read UTF-8: {exc}")
    # Root guides and docs/. These were unchecked -- ~44 markdown files, including every citation in
    # the rules index, which exists precisely to point a reader at a primary source. A dead pointer
    # there sends someone looking for authority to a file that is not there.
    #
    # Historical documents are in scope on purpose: a superseded plan is still read, and this repo
    # has already shipped a review pointing at a file the same round deleted. What is NOT in scope
    # is anchor-only and cross-repo links, which `_check_markdown` already ignores.
    failures.extend(_check_live_doc_links(root))
    failures.extend(_check_evidence_banner(root))
    command_root = root / "commands"
    if command_root.is_dir():
        for command in sorted(command_root.glob("*.md")):
            try:
                failures.extend(
                    _check_markdown(
                        command,
                        command.read_text(encoding="utf-8"),
                        command_root,
                    )
                )
            except (OSError, UnicodeError) as exc:
                failures.append(f"{command.as_posix()}: cannot read UTF-8: {exc}")
    return failures


def main() -> int:
    failures = check(ROOT)
    if failures:
        print("check_links: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    print("check_links: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
