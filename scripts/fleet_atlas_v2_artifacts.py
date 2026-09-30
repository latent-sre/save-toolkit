"""Single artifact verification boundary for fleet-atlas v2 build/check/query."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from fleet_atlas_v2_format import (
    API_VERSION, DETAIL_BUDGET, INDEX_BUDGET, PIPELINE, bounded_text, fact_line,
    graph_dict, parse_graph,
)
from fleet_atlas_v2_model import assemble, canonical_bytes, digest
from fleet_atlas_v2_proofs import VerifiedFacts, verify_facts
from fleet_atlas_v2_sources import Snapshot, current_snapshot, verify_revision


OUTPUT = Path("docs/fleet-atlas/v2")
_SEAL = object()


class ArtifactDrift(ValueError):
    """A stored graph, manifest, or view differs from its source-bound projection."""


VIEWS = {
    "capability-owner-map.md": frozenset({"owns", "delegates_to", "constrained_by"}),
    "claim-to-eval-map.md": frozenset({"verified_by", "near_miss_for"}),
    "decision-supersession-map.md": frozenset({"supersedes", "governed_by"}),
    "roadmap-dependency-map.md": frozenset({"depends_on", "blocks", "evidenced_by"}),
    "skill-reference-loading-map.md": frozenset({"loads_when"}),
    "contradictions-and-stale-evidence.md": frozenset({"contradicts", "unknown"}),
    "source-and-projection-map.md": frozenset({"generated_from", "governed_by", "delegates_to", "cites", "routes_to"}),
}


def extraction(snapshot: Snapshot):
    # Fixed trusted implementation import, never a module path from atlas content.
    from fleet_atlas_v2_extract import extract

    return extract(snapshot)


def verify_runtime_sources(snapshot: Snapshot) -> None:
    """The recorded source tree must contain the implementation actually in use."""
    directory = Path(__file__).resolve().parent
    modules = [*directory.glob("fleet_atlas_v2*.py"), directory / "fleet_frontmatter.py"]
    for path in sorted(modules):
        relative = "scripts/" + path.name
        expected = snapshot.source(relative).content.replace(b"\r\n", b"\n")
        actual = path.read_bytes().replace(b"\r\n", b"\n")
        if actual != expected:
            raise ValueError(f"running atlas implementation differs from recorded source: {relative}")


@dataclass(frozen=True)
class VerifiedDocument:
    facts: VerifiedFacts
    revision: str
    _seal: object = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _SEAL:
            raise ValueError("VerifiedDocument requires complete artifact verification")


def checked_facts(snapshot: Snapshot, loader: Callable = extraction) -> VerifiedFacts:
    result = loader(snapshot)
    graph = assemble(result.buckets, result.predicates)
    return verify_facts(graph, snapshot, result.predicates, result.evaluators)


def mermaid_label(value: str) -> str:
    # Mermaid's documented decimal entity syntax keeps syntax characters in the
    # display label, separate from the safe internal node identifier.
    return "".join(char if char.isalnum() or char in " ._:-/" else f"#{ord(char)};" for char in value)


def render_files(checked: VerifiedFacts) -> dict[str, bytes]:
    """Pure rendering over verified facts; file/CLI consumers use VerifiedDocument."""
    if not isinstance(checked, VerifiedFacts):
        raise TypeError("rendering requires proof-verified VerifiedFacts")
    snapshot = checked.snapshot
    header = (f"<!-- Generated fleet-atlas v2; canonical sources remain authoritative. -->\n"
              f"Source revision: `{snapshot.revision}`; input digest: `{snapshot.tree_digest}`.\n"
              "Repository relationships only; operational state and execution authority are not established.")
    files = {}
    nodes = {node.id: node for node in checked.graph.nodes}
    for filename, predicates in VIEWS.items():
        selected = []
        for fact in checked.graph.facts:
            include = fact.predicate in predicates
            if filename == "decision-supersession-map.md":
                include |= (nodes[fact.subject].type == "decision" and fact.predicate in
                            {"name", "state", "authority", "attr.date", "attr.status_text"})
                include |= (fact.predicate == "unknown" and str(dict(fact.qualifiers).get("code", ""))
                            .startswith(("extract.supersedes", "extract.rule-source")))
            elif filename == "roadmap-dependency-map.md":
                include |= (nodes[fact.subject].type == "roadmap-item" and fact.predicate in
                            {"name", "state", "authority", "attr.status", "attr.closed", "attr.owner"})
            if include:
                selected.append(fact)
        selected.sort(key=lambda fact: (fact.subject, fact.predicate, fact.id))
        files[filename] = bounded_text(header, (fact_line(fact, checked) for fact in selected), DETAIL_BUDGET)
    files["INDEX.md"] = bounded_text(
        header,
        ["# Fleet knowledge atlas", "Run `check` before trusting any view; stale output is unverified.",
         "`query impact <path-or-id>` traces recorded change relationships.",
         "`query guidance <terms...>` locates canonical investigation guidance.",
         *(f"- [{filename}]({filename})" for filename in sorted(VIEWS))], INDEX_BUDGET)
    for filename, predicate in (("delegation.mmd", "delegates_to"),
                                ("roadmap-dependency-map.mmd", "depends_on")):
        lines = []
        for fact in checked.graph.facts:
            if fact.predicate != predicate:
                continue
            # Internal IDs contain no source syntax; readable labels use Mermaid
            # entities. Full class, label and citations accompany the same record.
            source = "n" + digest(fact.subject.encode())[7:23]
            target = "n" + digest(str(fact.object).encode())[7:23]
            lines.append(f'  {source}["{mermaid_label(fact.subject)}"] --> '
                         f'{target}["{mermaid_label(str(fact.object))}"]\n  %% {fact_line(fact, checked)}')
        # Mermaid has a distinct comment syntax, but shares byte budgeting and facts.
        encoded = bounded_text("flowchart LR\n%% " + header.replace("\n", "\n%% "), lines, DETAIL_BUDGET)
        files[filename] = encoded.replace(b"<!-- {", b"%% {").replace(b"} -->\n", b"}\n")
        # Comment conversion only shortens output, so recompute self-reported size.
        marker_at = files[filename].rfind(b"\n%% {")
        prefix = files[filename][:marker_at + 4]
        info = json.loads(files[filename][marker_at + 4:])
        for _ in range(12):
            info["encodedBytes"] = len(prefix + canonical_bytes(info))
            content = prefix + canonical_bytes(info)
            if info["encodedBytes"] == len(content):
                break
        files[filename] = content
    document = {"apiVersion": API_VERSION, "kind": "FleetAtlas",
                "metadata": {"revision": snapshot.revision, "treeDigest": snapshot.tree_digest,
                             "dirty": False, "pipeline": PIPELINE},
                **graph_dict(checked.graph)}
    files["atlas.json"] = canonical_bytes(document)
    files["manifest.json"] = canonical_bytes({
        "apiVersion": "save-toolkit/fleet-atlas-manifest/v2",
        "files": {name: digest(content) for name, content in sorted(files.items())},
    })
    return files


def _safe_output(root: Path, *, create: bool) -> Path:
    root = root.resolve(strict=True)
    current = root
    for part in OUTPUT.parts:
        current = current / part
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("atlas output cannot traverse a symlink or junction")
        if create:
            current.mkdir(exist_ok=True)
        elif not current.is_dir():
            raise ValueError("atlas output is missing")
    if not current.resolve(strict=True).is_relative_to(root):
        raise ValueError("atlas output escapes repository")
    return current


def _read_files(directory: Path, names: set[str]) -> dict[str, bytes]:
    entries = {path.name: path for path in directory.iterdir()}
    if set(entries) != names:
        raise ArtifactDrift("atlas output membership differs from generated file set")
    files = {}
    for name, path in sorted(entries.items()):
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"atlas output is not a regular file: {name}")
        files[name] = path.read_bytes()
    return files


def _json(content: bytes) -> object:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON field: {key}")
            result[key] = value
        return result

    return json.loads(content, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid number: {value}")))


def verify(root: Path, loader: Callable = extraction) -> VerifiedDocument:
    """The one entry point used after build and by both check and query."""
    current = current_snapshot(root)
    if loader is extraction:
        verify_runtime_sources(current)
    output = _safe_output(root, create=False)
    atlas_path = output / "atlas.json"
    if atlas_path.is_symlink() or not atlas_path.is_file():
        raise ValueError("atlas.json is missing or not a regular file")
    document = _json(atlas_path.read_bytes())
    if (not isinstance(document, dict)
            or set(document) != {"apiVersion", "kind", "metadata", "nodes", "facts"}
            or document["apiVersion"] != API_VERSION or document["kind"] != "FleetAtlas"):
        raise ValueError("invalid atlas document")
    meta = document["metadata"]
    if (not isinstance(meta, dict) or set(meta) != {"revision", "treeDigest", "dirty", "pipeline"}
            or meta["dirty"] is not False or meta["pipeline"] != PIPELINE
            or not isinstance(meta["revision"], str)
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", meta["revision"])
            or meta["treeDigest"] != current.tree_digest):
        raise ValueError("atlas provenance is stale, invalid, or unverified")
    verify_revision(root, meta["revision"], current)
    snapshot = Snapshot(meta["revision"], current.sources)
    contract = loader(snapshot)
    graph = parse_graph({"nodes": document["nodes"], "facts": document["facts"]})
    checked = verify_facts(graph, snapshot, contract.predicates, contract.evaluators)
    if graph != assemble(contract.buckets, contract.predicates):
        raise ArtifactDrift("atlas graph differs from complete source extraction")
    expected = render_files(checked)
    actual = _read_files(output, set(expected))
    if actual != expected:
        differing = sorted(name for name in expected if actual[name] != expected[name])
        raise ArtifactDrift(f"atlas projection or manifest drift: {differing}")
    # Detect a moving checkout after proof replay or output reads too.
    after = current_snapshot(root)
    if after != current:
        raise ValueError("repository changed during atlas verification")
    return VerifiedDocument(checked, snapshot.revision, _SEAL)


def build(root: Path, loader: Callable = extraction) -> VerifiedDocument:
    snapshot = current_snapshot(root)
    if loader is extraction:
        verify_runtime_sources(snapshot)
    files = render_files(checked_facts(snapshot, loader))
    output = _safe_output(root, create=True)
    for path in output.iterdir():
        if path.name not in files or path.is_symlink() or not path.is_file():
            raise ValueError(f"unexpected output entry; inspect before rebuilding: {path.name}")
    if current_snapshot(root) != snapshot:
        raise ValueError("repository changed before atlas build write")
    for name in sorted(files, key=lambda item: (item == "manifest.json", item)):
        with tempfile.NamedTemporaryFile(dir=output, prefix=".atlas-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(files[name])
        try:
            os.replace(temporary, output / name)
        finally:
            if temporary.exists():
                temporary.unlink()
    return verify(root, loader)
