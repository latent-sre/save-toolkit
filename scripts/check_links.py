#!/usr/bin/env python3
"""Check canonical skill/command frontmatter, links, and bundle reachability.

The authored plugin sources live at root-level skills/ and commands/. Generated
host adapters are consequences and are checked separately by the adapter generator.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import fleet_frontmatter


ROOT = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parents[1]).resolve()
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
CODE_PATH_RE = re.compile(
    r"`((?:references|assets|scripts)/[A-Za-z0-9._/-]+)`"
)
# A reference naming its OWN parent skill by repo-rooted path (`skills/backend-craft/SKILL.md`
# inside skills/backend-craft/references/). It reads correct and is wrong everywhere it is read:
# not from the reference's own directory, and not in platforms/copilot/skills/, where the skill
# lives under a different prefix entirely. `../SKILL.md` is the form that resolves in both trees.
# CODE_PATH_RE never caught it because that pattern only covers bundle-internal prefixes, so eight
# of backend-craft's nine references carried a dead pointer through every green gate.
SELF_SKILL_PATH_RE = re.compile(r"`skills/(?P<name>[a-z0-9-]+)/SKILL\.md`")
# Documents whose links must RESOLVE, checked for nothing else.
#
# Scope is every document a dead pointer can be REPAIRED in: the root guides, the roadmap, the live
# reference contracts. These were checked by nothing, and a dead pointer in any of them sends
# someone looking for authority to a file that is not there.
#
# Repairability is the whole selection rule, and it is why docs/decisions/ is NOT here. An accepted
# ADR is append-only and immutable (commands/adr.md); the only sanctioned way to change one is to
# write a successor. Gating a file the rules forbid repairing turns every retention pass into a red
# gate with no legal fix -- 14 such links did exactly that on 2026-09-02. CONTRIBUTING's retention
# policy is that an evidence packet is kept only while something cites it -- but citation used to be
# unenforced: a packet could sit uncited indefinitely and nothing failed. `_check_uncited_review_packets`
# below makes citation a gate: an uncited packet under docs/reviews/ now fails Gate A directly,
# rather than waiting on a human retention pass. A record citing a removed packet is that policy
# working. Recover any removed packet from git.
#
# docs/reviews/ stays: retained packets cite each other, and a retention pass that keeps a packet
# while deleting one it cites leaves an active item's evidence chain ending at a missing file, and
# did -- six such links survived a green `check_links` because this directory was not read. Unlike
# an ADR, a retained packet may be edited or dropped, so a red here has a legal fix.
#
# Only resolvability is asserted. The skill rules applied elsewhere in this file (owned-root
# containment, code-span pointers must be Markdown links) are conventions for skill bundles; docs
# legitimately link across the whole repository and cite scripts inline.
LIVE_DOC_ROOTS = (
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CHANGELOG.md",
    "evals/README.md",
    # These two moved under sandbox/ on 2026-09-02. A LIVE_DOC_ROOTS entry naming a path that no
    # longer exists is skipped by the is_file() filter below -- silently, so the gate reports
    # coverage it is not providing. Any rename here has to land in the same commit as the move.
    "sandbox/graph-sandbox/AGENTS.md",
    "sandbox/graph-sandbox/contract.md",
    ".github/pull_request_template.md",
    ".github/copilot-instructions.md",
    "commands/adr.md",
)
LIVE_DOC_DIR_GLOBS = (
    ("docs", "*.md"),
    ("docs/probes", "*.md"),
    ("docs/reviews", "*.md"),
)


def _iter_doc_paths(
    root: Path, roots: tuple[str, ...], globs: tuple[tuple[str, str], ...]
) -> list[Path]:
    targets: list[Path] = [root / name for name in roots]
    for relative, pattern in globs:
        directory = root / relative
        if directory.is_dir():
            targets.extend(sorted(directory.glob(pattern)))
    return [path for path in targets if path.is_file()]


def _check_live_doc_links(root: Path) -> list[str]:
    # Canonicalize the root before comparing anything against it. The containment test below builds
    # its left side with .resolve(), so an UNRESOLVED root makes the two sides disagree about the
    # same directory and every legitimate link reports as escaping. That is not theoretical: macOS
    # hands out `/var/folders/...` that resolves to `/private/var/...` and Windows hands out 8.3
    # short paths, so this passed on Linux and failed both other CI legs.
    root = Path(root).resolve()
    failures: list[str] = []
    for path in _iter_doc_paths(root, LIVE_DOC_ROOTS, LIVE_DOC_DIR_GLOBS):
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


def _tracked_review_packets(root: Path) -> list[Path]:
    """Every git-tracked file under docs/reviews/, via `git ls-files` (never a directory read).

    `git ls-files` excludes untracked files by construction, so an untracked packet is never
    considered here -- the citation gate cannot see, and must not see, a file no one has committed.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "docs/reviews"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"check_links: git unavailable, skipping the uncited-evidence check ({exc})")
        return []
    return [root / line for line in result.stdout.splitlines() if line.strip()]


def _citing_candidates(root: Path) -> list[Path]:
    """Every file a review packet may legitimately be cited from."""
    files: list[Path] = list(_iter_doc_paths(root, LIVE_DOC_ROOTS, LIVE_DOC_DIR_GLOBS))
    decisions = root / "docs" / "decisions"
    if decisions.is_dir():
        files.extend(sorted(decisions.glob("*.md")))
    evals_dir = root / "evals"
    if evals_dir.is_dir():
        files.extend(sorted(evals_dir.rglob("*.yaml")))
        files.extend(sorted(evals_dir.glob("*.py")))
    scripts_dir = root / "scripts"
    if scripts_dir.is_dir():
        files.extend(sorted(scripts_dir.glob("*.py")))
    roadmap = root / "docs" / "fleet-roadmap.md"
    if roadmap.is_file() and roadmap not in files:
        files.append(roadmap)
    return files


def _citation_keys(relative: str) -> list[str]:
    """Path substrings that count as citing this packet, absolute and one-level-relative.

    A flat packet (`docs/reviews/2026-08-30-x.md`) is cited only by its own path. A directory-shaped
    packet (a README plus a manifest and patches, e.g. `2026-08-12-incident-navigation-preservation/`)
    is one evidence unit with one citable entry point -- citing the packet's directory, the way the
    2026-08-22 ADR cites its README, covers every file inside, the same way a skill bundle's files
    need not each be linked externally.
    """
    after_reviews = relative.split("docs/reviews/", 1)[1]
    top = after_reviews.split("/", 1)[0]
    return [relative, f"reviews/{after_reviews}", f"docs/reviews/{top}", f"reviews/{top}"]


def _check_uncited_review_packets(root: Path) -> list[str]:
    """A retained packet earns its keep by being cited; an uncited one fails the gate.

    Citation is checked by path substring across the live documents, decisions, eval scenarios and
    harness, and validator scripts -- never against the packet's own text, so a packet cannot cite
    itself into compliance.
    """
    packets = _tracked_review_packets(root)
    if not packets:
        return []
    candidates = []
    for path in _citing_candidates(root):
        try:
            candidates.append((path.resolve(), path.read_text(encoding="utf-8")))
        except (OSError, UnicodeError):
            continue
    failures = []
    for packet in packets:
        if not packet.is_file():
            continue
        relative = packet.relative_to(root).as_posix()
        resolved_packet = packet.resolve()
        keys = _citation_keys(relative)
        cited = any(
            any(key in text for key in keys)
            for resolved, text in candidates
            if resolved != resolved_packet
        )
        if not cited:
            failures.append(f"uncited evidence packet: {relative}")
    return failures


ALLOWED_KEYS = {
    "name",
    "description",
    "argument-hint",
    "disable-model-invocation",
    "compatibility",
}
# Skills that must carry `disable-model-invocation: true`, and the only ones allowed to. Each is
# explicit-only because autonomous invocation would be an effect or a cost the caller did not ask
# for: `pcf-deploy` coordinates approved production effects. Adding a name here is a decision:
# state why the skill cannot be model-invoked, and keep the message below in sync.
MANUAL_ONLY = {"pcf-deploy"}
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


def _yaml_string(
    value: object, style: str | None, where: str, failures: list[str]
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{where}: value must be one nonblank YAML string")
        return None
    if style == "single-quoted-unmatched":
        failures.append(f"{where}: invalid quoted string")
        return None
    if style == "plain":
        if value.startswith("[") or value.startswith("{"):
            failures.append(f"{where}: value must be a string, not a collection")
            return None
        if YAML_NON_STRING.fullmatch(value):
            failures.append(f"{where}: value must be a YAML string, not an implicit scalar")
            return None
    return value


def _check_skill_frontmatter(path: Path, text: str) -> tuple[str, list[str]]:
    parsed = fleet_frontmatter.parse(text, path, mode="lenient")
    values = parsed.fields
    styles = parsed.styles
    body = parsed.body
    failures = list(parsed.problems)
    where = path.as_posix()
    expected_name = path.parent.name
    unknown = sorted(set(values) - ALLOWED_KEYS)
    if unknown:
        failures.append(f"{where}: unknown frontmatter key(s): {', '.join(unknown)}")
    name = _yaml_string(
        values.get("name", ""), styles.get("name"), f"{where}: name", failures
    )
    if name:
        if len(name) > 64:
            failures.append(f"{where}: name exceeds 64 characters")
        if not NAME_RE.fullmatch(name) or name != expected_name:
            failures.append(
                f"{where}: name must be kebab-case and equal directory '{expected_name}'"
            )
    description = _yaml_string(
        values.get("description", ""),
        styles.get("description"),
        f"{where}: description",
        failures,
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
        _yaml_string(
            values["argument-hint"],
            styles.get("argument-hint"),
            f"{where}: argument-hint",
            failures,
        )
    if "compatibility" in values:
        compatibility_style = styles.get("compatibility")
        compatibility = _yaml_string(
            values["compatibility"],
            compatibility_style,
            f"{where}: compatibility",
            failures,
        )
        if compatibility_style == "block":
            failures.append(
                f"{where}: compatibility must use a single-line scalar so its "
                "500-character limit is measured exactly"
            )
        elif compatibility and len(compatibility) > 500:
            failures.append(f"{where}: compatibility exceeds 500 characters")
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
            f"{where}: only {', '.join(sorted(MANUAL_ONLY))} may disable model invocation"
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


def _check_self_skill_pointer(path: Path, text: str, skill_name: str) -> list[str]:
    """Reject a reference pointing at its own SKILL.md by repo-rooted path.

    Only the self-pointer is rejected, and only inside that skill's own bundle. A reference may
    legitimately name a *sibling* skill's file to describe ownership, and drill scenario assets
    quote paths from systems that are not this repository at all -- neither is a broken pointer.
    """
    failures = []
    for match in SELF_SKILL_PATH_RE.finditer(_strip_fences(text)):
        if match.group("name") != skill_name:
            continue
        failures.append(
            f"{path.as_posix()}: reference points at its own skill by repo-rooted path "
            f"'{match.group(0).strip('`')}'; use '../SKILL.md', which resolves in the canonical "
            "tree and in platforms/copilot/skills/"
        )
    return failures


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
    for path in sorted(skill_root.iterdir()):
        if path.is_file() and path.name != "SKILL.md":
            yield path
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
      * An inline-code path token (`scripts/gate_a.py`, `docs/fleet-roadmap.md`) that stops
        resolving after a rename reads as live guidance and isn't.

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
                        reference_text = reference.read_text(encoding="utf-8")
                        failures.extend(
                            _check_markdown(
                                reference,
                                reference_text,
                                skill_path.parent,
                            )
                        )
                        failures.extend(
                            _check_self_skill_pointer(
                                reference, reference_text, skill_path.parent.name
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
    failures.extend(_check_uncited_review_packets(root))
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
