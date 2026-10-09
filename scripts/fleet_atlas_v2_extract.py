"""Pure, source-bound fleet extraction; no inspected module is imported or executed.

Each family emits an immutable bucket. Relationships resolve against immutable source
records, never a partially assembled graph. Proof replay independently rebuilds records
from the closed snapshot; candidate values and candidate citations are not premises.
"""
from __future__ import annotations

import ast
import hashlib
import json
import posixpath
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Container, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import cached_property, lru_cache
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any, Literal, NamedTuple, TypeAlias, cast
from urllib.parse import unquote, urlsplit

import fleet_frontmatter
from fleet_atlas_v2_model import (
    EDGE_ENDPOINTS,
    EDGE_TYPES,
    NODE_TYPES,
    WHOLE_DOCUMENT,
    Bucket,
    Fact,
    Node,
    NodeIndex,
    NodeRef,
    Predicate,
    Proof,
    Span,
    Value,
)
from fleet_atlas_v2_model import EvidenceClass as EC
from fleet_atlas_v2_model import ProofKind as PK
from fleet_atlas_v2_proofs import Derivation, Extraction
from fleet_atlas_v2_sources import Snapshot, Source

LIVE_DOCS = frozenset(('AGENTS.md', 'CONTRIBUTING.md', 'README.md', 'docs/README.md',
    'docs/rules.md', 'docs/schema-compatibility.md', 'docs/fleet-roadmap.md'))
ITEM = re.compile(r'\b[A-Z][A-Z0-9]*-\d{3}\b')
BATCH = re.compile(r'\b\d{8}T\d{6}Z-[0-9a-f]{8}\b')
DATE = re.compile(r'\b20\d\d-\d\d-\d\d\b')
LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
TARGET_LINK = re.compile(r'\]\(([^)]+)\)')
FIELD = re.compile(r'^\*\*([A-Za-z][A-Za-z ]+):\*\*\s*(.*)$')
SEPARATOR = re.compile(r'^\|\s*:?-{3,}')  # A Markdown table's header/body separator row.
EVALUATOR = 'fleet-source-replay/v2'


# Fact values must stay exact str (validate_value), so these are annotations, not enums.
Authority = Literal['canonical', 'live-contract', 'historical-evidence', 'generated', 'external']
State = Literal['live', 'proposed', 'historical', 'rejected', 'deprecated', 'generated']


@dataclass(frozen=True)
class Record:
    node: Node
    name: str
    authority: Authority
    state: State
    attrs: tuple[tuple[str, Value], ...]
    spans: tuple[Span, ...]
    family: str
    proof_kind: PK = PK.EXTRACTED
    evidence_class: EC = EC.EXTRACTED

    @cached_property
    def attributes(self) -> Mapping[str, Value]:
        """The frozen attrs pairs as a read-only mapping; identity still compares fields only."""
        return MappingProxyType(dict(self.attrs))


class RoadmapEntry(NamedTuple):
    """One roadmap item: its heading or row lines, field texts, and each field's spans."""
    item: str
    start: int
    end: int
    fields: Mapping[str, str]
    positions: Mapping[str, tuple[Span, ...]]


class GeneratedMapping(NamedTuple):
    """An adapter output, the canonical source it is generated from, and the mapping proof."""
    projection: str
    canonical: str
    proof: tuple[Span, ...]


class WriterProjection(NamedTuple):
    """A schema's declared output bound to the writer that actually produces it."""
    schema_id: str
    projection: str
    proof: tuple[Span, ...]


@dataclass(frozen=True)
class StageOutput:
    """A producer returns immutable data, never a graph or shared record builder."""
    records: tuple[Record, ...] = ()
    buckets: tuple[Bucket, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple) or not all(isinstance(r, Record) for r in self.records):
            raise TypeError('stage records must be a tuple of Record values')
        if not isinstance(self.buckets, tuple) or not all(isinstance(b, Bucket) for b in self.buckets):
            raise TypeError('stage buckets must be a tuple of Bucket values')


class Corpus:
    """One derivation's read-only view of its snapshot; shared inputs are parsed once.

    _derive builds a new Corpus for every derivation, so proof replay re-parses and
    re-derives each declaration rather than reusing the primary extraction's work.
    Views are lazy: a malformed input fails at its first use, as a direct parse would.
    Every stage of a derivation sees the same objects, so stages must never mutate them;
    parsed JSON stays plain dicts and lists because declarations are type-checked as dict.
    """

    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot = snapshot
        self.sources = snapshot.sources
        self.by_path: Mapping[str, Source] = MappingProxyType({s.path: s for s in snapshot.sources})
        self.schema_sources = tuple(s for s in snapshot.sources
                                    if s.path.startswith('schemas/') and s.path.endswith('.schema.json'))
        self._json: dict[str, Any] = {}
        self._headings: dict[str, Mapping[str, int]] = {}

    def get(self, path: str) -> Source | None:
        return self.by_path.get(path)

    def parsed(self, source: Source) -> Any:
        """The source's JSON document."""
        if source.path not in self._json:
            self._json[source.path] = json.loads(source.text)
        return self._json[source.path]

    def catalog_entries(self) -> list[dict[str, Any]]:
        catalog = self.get('schemas/catalog-v1.json')
        entries: list[dict[str, Any]] = self.parsed(catalog).get('schemas', []) if catalog else []
        return entries

    @cached_property
    def roadmap_entries(self) -> tuple[RoadmapEntry, ...]:
        """The live roadmap's items; the closed register is the only other roadmap-item source."""
        roadmap = self.get('docs/fleet-roadmap.md')
        return records_for_roadmap(roadmap) if roadmap else ()

    def headings(self, source: Source) -> Mapping[str, int]:
        """Markdown section anchors, numbered on repeats, to their heading line."""
        if source.path not in self._headings:
            headings, counts = {}, Counter[str]()
            for i, line in enumerate(source.lines, 1):
                if re.match(r'^#{1,6}\s', line):
                    key = anchor(line.lstrip('#').strip())
                    headings[key + (f'-{counts[key]}' if counts[key] else '')] = i
                    counts[key] += 1
            self._headings[source.path] = MappingProxyType(headings)
        return self._headings[source.path]

    @cached_property
    def generated(self) -> tuple[GeneratedMapping, ...]:
        return generated_mappings(self)

    @cached_property
    def projections(self) -> tuple[WriterProjection, ...]:
        return standalone_projections(self)


@dataclass(frozen=True)
class ExtractionStage:
    name: str
    requires: tuple[str, ...]
    produce: Callable[[Corpus, Mapping[str, StageOutput]], StageOutput]

    def __post_init__(self) -> None:
        if (not isinstance(self.requires, tuple) or len(set(self.requires)) != len(self.requires)
                or not all(isinstance(name, str) for name in self.requires)):
            raise TypeError('stage prerequisites must be unique immutable names')


def stable_id(prefix: str, *parts: str) -> str:
    return prefix + ':' + hashlib.sha256('\x1f'.join(parts).encode()).hexdigest()[:16]


def pairs(mapping: Mapping[Any, object]) -> tuple[tuple[str, Value], ...]:
    """A mapping as the sorted (name, frozen value) pairs that record attributes and fact qualifiers hold."""
    return tuple((str(k), freeze(v)) for k, v in sorted(mapping.items()))


def freeze(value: object) -> Value:
    if isinstance(value, dict):
        return pairs(value)
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(freeze(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value))
    if value is None or type(value) in (str, int, float, bool):
        return cast('Value', value)  # mypy cannot narrow on exact-type membership
    return str(value)  # YAML dates retain their textual value, never a mutable object.


def plain(text: str) -> str:
    return ' '.join(LINK.sub(r'\1', text).replace('`', '').replace('**', '').split())


def link_targets(text: str) -> tuple[str, ...]:
    # The destination remains parseable on the closing line of a wrapped or
    # nested-label link. Labels do not determine a repository target identity.
    return tuple(TARGET_LINK.findall(text))


def table_cells(line: str) -> list[str]:
    """Raw cells of a Markdown table row, without its outer pipes or surrounding whitespace."""
    return line.strip().strip('|').split('|')


def human_owner(owner: str) -> str:
    """The human owner an Owner field names before its first `component`, or ''."""
    prefix = owner.split('`', 1)[0].strip()
    return re.split(r'\s+owns?\b', prefix, maxsplit=1, flags=re.I)[0].strip(' .,:;')


def live_guide(path: str) -> bool:
    """Current guidance whose text is a live contract rather than historical evidence."""
    return path in LIVE_DOCS or (PurePosixPath(path).name in ('README.md', 'CHANGELOG.md')
                                 and not path.startswith('docs/reviews/'))


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def anchor(text: str) -> str:
    return re.sub(r'[^\w\- ]', '', plain(text).lower()).replace(' ', '-')


def spans(*values: Iterable[Span]) -> tuple[Span, ...]:
    return tuple(sorted(set(item for group in values for item in group)))


def whole(source: Source) -> tuple[Span, ...]:
    if not source.lines:
        raise ValueError(f'cannot invent a line citation for empty source: {source.path}')
    return (source.span(1, len(source.lines)),)


def _node_span(source: Source, node: ast.stmt | ast.expr) -> Span:
    """The lines a parsed statement or expression occupies; ast.parse sets every end_lineno."""
    assert node.end_lineno is not None
    return source.span(node.lineno, node.end_lineno)


# Block scalars may have tag/anchor properties and trailing header comments.
# Missing these forms lets prompt text fabricate scenario identity or routing.
NODE_PROPERTY = r'(?:&[^\s,\[\]{}]+|!<[^>]*>|![^\s,\[\]{}]*)'
YAML_PROPERTIES = r'(?:' + NODE_PROPERTY + r'[ \t]+)*'
PROPERTY_PREFIX = re.compile(YAML_PROPERTIES)
PROPERTY_TOKEN = re.compile(NODE_PROPERTY + r'(?=\s|$)')
BLOCK_SCALAR = re.compile(r'^' + YAML_PROPERTIES +
                          r'[|>](?:[1-9][+-]?|[+-][1-9]?)?(?:[ \t]+#.*)?$')


def _scalar_start(lines: Sequence[str], index: int, indent: int, value: str) -> tuple[int, str]:
    """An empty value or properties can precede a scalar on a later line."""
    while True:
        text = value + ' '
        properties = PROPERTY_PREFIX.match(text)
        assert properties is not None  # A repeated group matches, if only the empty prefix.
        value = text[properties.end():].strip()
        if value and not value.startswith('#'):
            return index, value
        following = index + 1
        while following < len(lines) and (not lines[following].strip()
                                         or lines[following].lstrip().startswith('#')):
            following += 1
        if following == len(lines):
            return index, ''
        raw = lines[following]
        if len(raw) - len(raw.lstrip(' ')) <= indent:
            return index, ''
        candidate = raw.strip()
        if candidate[:1] not in ('|', '>', '\"', "'", '{', '[', '&', '!'):
            return index, ''
        index, value = following, candidate


def _flow_scalar(lines: Sequence[str], index: int, value: str) -> tuple[int, str]:
    """Consume a quoted/flow value through its terminator, never as mapping keys."""
    quote, escaped, closers, token_start, parts = None, False, [], True, []
    for current in range(index, len(lines)):
        text = value if current == index else lines[current]
        offset = 0
        while offset < len(text):
            char = text[offset]
            if quote:
                if escaped:
                    escaped = False
                elif quote == '\"' and char == '\\':
                    escaped = True
                elif char == quote:
                    if quote == "'" and text[offset + 1:offset + 2] == "'":
                        offset += 2
                        continue
                    quote = None
                    token_start = False
            elif char == '#' and (offset == 0 or text[offset - 1].isspace()):
                text = text[:offset]
                break
            elif char == '?' and token_start and (offset + 1 == len(text)
                                                   or text[offset + 1].isspace()):
                raise ValueError('explicit YAML flow keys are outside the metadata subset')
            elif token_start and char in '!&':
                property_token = PROPERTY_TOKEN.match(text, offset)
                if property_token:
                    offset = property_token.end()
                    continue
                token_start = False
            elif char in '\"\'' and token_start:
                quote = char
            elif char in '{[':
                closers.append('}' if char == '{' else ']')
                token_start = True
            elif char in '}]':
                if not closers or closers.pop() != char:
                    raise ValueError('mismatched YAML flow collection')
                token_start = False
            elif char in ',:':
                token_start = True
            elif not char.isspace():
                token_start = False
            if not quote and not closers:
                trailing = text[offset + 1:].strip()
                if trailing and not trailing.startswith('#'):
                    raise ValueError('unsupported text after YAML scalar')
                parts.append(text[:offset + 1].strip())
                return current, ' '.join(parts)
            offset += 1
        # A double-quoted escaped line break consumes the break, not the next quote.
        escaped = False
        parts.append(text.strip())
    raise ValueError('unterminated YAML quoted or flow scalar')


def frontmatter_fields(source: Source) -> tuple[dict[str, fleet_frontmatter.FrontmatterValue], tuple[Span, ...]]:
    """Component frontmatter through the fleet's shared parser, cited from the opening fence."""
    parsed = fleet_frontmatter.parse(source.text, source.path, mode='lenient')
    return parsed.fields, (source.span(1, len(parsed.raw_lines) + 2),)


def scenario_fields(source: Source) -> tuple[dict[str, Any], tuple[Span, ...]]:
    """Top-level scenario metadata, cited as the whole file."""
    # Deliberately the donor's scalar identity/routing subset, not executable YAML.
    # Prompt block scalars and fixtures cannot contribute top-level target identity.
    result: dict[str, Any] = {}
    stack, block_indent = [(-1, result)], None
    lines, index = source.lines, 0
    while index < len(lines):
        raw, current = lines[index], index
        index += 1
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        indent = len(raw) - len(raw.lstrip(' '))
        if block_indent is not None:
            if indent > block_indent:
                continue
            block_indent = None
        line = raw.strip()
        if line.startswith('-') or ':' not in line:
            continue
        key, value = line.split(':', 1)
        while stack[-1][0] >= indent:
            stack.pop()
        parent, value = stack[-1][1], value.strip()
        start, value = _scalar_start(lines, current, indent, value)
        if BLOCK_SCALAR.fullmatch(value):
            parent.pop(key, None)
            index = start + 1
            block_indent = indent
        elif not value:
            parent[key] = {}
            stack.append((indent, parent[key]))
        else:
            if value[:1] in ('\"', "'", '{', '['):
                end, value = _flow_scalar(lines, start, value)
                index = end + 1
            parent[key] = _scenario_scalar(value)
            # Scalar continuations cannot declare mapping keys, including when
            # tag/anchor properties put the block header on the following line.
            block_indent = indent
    return result, whole(source)


# Quoted or plain text, a number, a YAML keyword, or a one-line flow mapping of them.
ScenarioValue: TypeAlias = 'str | int | float | bool | dict[str, ScenarioValue] | None'


def _scenario_scalar(value: str) -> ScenarioValue:
    if value.startswith('{') and value.endswith('}'):
        return {key.strip(): _scenario_scalar(item.strip())
                for part in value[1:-1].split(',') for key, item in [part.split(':', 1)]}
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '\"\'':
        return value[1:-1]
    if re.fullmatch(r'-?\d+(?:\.\d+)?', value):
        return float(value) if '.' in value else int(value)
    return {'null': None, 'true': True, 'false': False}.get(value, value)


def yaml_key_spans(source: Source, keys: tuple[str, ...]) -> tuple[Span, ...]:
    starts = [(i, line.split(':', 1)[0]) for i, line in enumerate(source.lines, 1)
              if re.match(r'^[A-Za-z][A-Za-z_-]*:', line)]
    selected = [source.span(start, starts[n + 1][0] - 1 if n + 1 < len(starts) else len(source.lines))
                for n, (start, key) in enumerate(starts) if key in keys]
    return tuple(selected) or whole(source)


def records_for_roadmap(source: Source) -> tuple[RoadmapEntry, ...]:
    starts = [(i, m.group(1)) for i, line in enumerate(source.lines)
              if (m := re.match(r'^###\s+([A-Z][A-Z0-9]*-\d{3})\b', line))]
    result = []
    for n, (start, item_id) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(source.lines)
        fields, positions, current = {}, {}, None
        for i in range(start + 1, end):
            line = source.lines[i].strip()
            if line.startswith('## '):
                current = None
            if match := FIELD.match(line):
                current = match.group(1)
                fields[current] = match.group(2)
                positions[current] = [i + 1]
            elif current and line:
                fields[current] += ' ' + line
                positions[current].append(i + 1)
        result.append(RoadmapEntry(item_id, start + 1, end, MappingProxyType(fields), MappingProxyType(
            {k: (source.span(min(v), max(v)),) for k, v in positions.items()})))
    # The modern parked register is still live backlog, with its own row selector.
    for i, line in enumerate(source.lines, 1):
        cells = table_cells(line)
        if len(cells) >= 2 and re.fullmatch(r'[A-Z][A-Z0-9]*-\d{3}', plain(cells[0])):
            item_id = plain(cells[0])
            if item_id not in {entry.item for entry in result}:
                result.append(RoadmapEntry(item_id, i, i,
                                           MappingProxyType({'Status': 'deferred', 'Next action': cells[1].strip()}),
                                           MappingProxyType({'Status': (source.span(i, i),), 'Next action': (source.span(i, i),)})))
    return tuple(result)


def status_marker(text: str) -> str:
    normalized = text.strip().strip('`*_ .').lower()
    return re.split(r'\s*(?:,|;|\(|\u2014|\u2013|\s-\s)\s*', normalized, maxsplit=1)[0].strip().strip('`*_ .')


def _ast(source: Source) -> ast.Module:
    return ast.parse(source.text, filename=source.path)


def assignment(source: Source, name: str) -> tuple[Any, tuple[Span, ...]]:
    for node in _ast(source).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            assert isinstance(node, (ast.Assign, ast.AnnAssign))  # Only these have targets.
            try:
                # A bare annotation's None value raises ValueError, as any non-literal does.
                value = ast.literal_eval(node.value)  # type: ignore[arg-type]
                return value, (_node_span(source, node),)
            except (ValueError, TypeError):
                return None, ()
    return None, ()


def resolved_link(source: Source, raw: str, paths: Container[str]) -> tuple[str, str] | None:
    split = urlsplit(raw.strip().strip('<>'))
    if split.scheme or split.netloc:
        return None
    path = unquote(split.path)
    target = posixpath.normpath(posixpath.join(posixpath.dirname(source.path), path)) if path else source.path
    if target.startswith('../') or target not in paths:
        return None
    return target, unquote(split.fragment)


def _record(node_id: str, node_type: str, name: str, path: str, evidence: tuple[Span, ...], *,
            authority: Authority = 'canonical', state: State = 'live', attrs: dict[str, Any] | None = None,
            family: str = 'documents', selector: str = WHOLE_DOCUMENT, kind: PK = PK.EXTRACTED,
            cls: EC = EC.EXTRACTED) -> Record:
    return Record(Node(node_id, node_type, path, selector), name, authority, state,
                  pairs(attrs or {}), evidence, family, kind, cls)


def _record_builder(inputs: Mapping[str, StageOutput]) -> tuple[dict[str, Record], Callable[[Record], None]]:
    """Private construction state; only frozen records cross a stage boundary."""
    records: dict[str, Record] = {}
    def add(record: Record) -> None:
        if record.node.id in records and records[record.node.id] != record:
            raise ValueError(f'conflicting source declarations: {record.node.id}')
        records[record.node.id] = record
    for output in inputs.values():
        for record in output.records:
            add(record)
    return records, add


def _new_records(records: Mapping[str, Record], inputs: Mapping[str, StageOutput]) -> StageOutput:
    inherited = {record.node.id for output in inputs.values() for record in output.records}
    return StageOutput(tuple(records[key] for key in sorted(records) if key not in inherited))


def _component_records(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    records, add = _record_builder(inputs)
    for source in corpus.sources:
        path, p = source.path, PurePosixPath(source.path)
        if path.startswith(('agents/', 'commands/')) and len(p.parts) == 2 and p.suffix == '.md':
            kind = 'agent' if path.startswith('agents/') else 'command'
            data, proof = frontmatter_fields(source)
            attrs: dict[str, Any] = {'description': str(data.get('description', '')).strip()}
            if kind == 'agent':
                tools = data.get('tools', [])
                tools = tools if isinstance(tools, list) else [str(tools)]
                grants = sorted({name.strip().removeprefix('save-toolkit:') for match in re.finditer(r'Agent\(([^)]+)\)', ' '.join(tools)) for name in match.group(1).split(',')})
                attrs.update(tools=tools, grants=grants)
            else:
                attrs.update(argument_hint=str(data.get('argument-hint', '')), manual_only=str(data.get('disable-model-invocation', '')).lower() == 'true')
            add(_record(f'{kind}:{p.stem}', kind, p.stem, path, proof, attrs=attrs, family='components'))
            if kind == 'agent':
                add(_record(f'owner:{p.stem}', 'owner', p.stem, path, proof, attrs={'kind': 'agent'}, selector=f'owner:{p.stem}', family='owners'))
        elif path.startswith('skills/') and len(p.parts) >= 3:
            skill, tail = p.parts[1], '/'.join(p.parts[2:])
            if tail == 'SKILL.md':
                data, proof = frontmatter_fields(source)
                add(_record(f'skill:{skill}', 'skill', skill, path, spans(proof, whole(source)), attrs={
                    'description': str(data.get('description', '')).strip(), 'manual_only': str(data.get('disable-model-invocation', '')).lower() == 'true', 'bytes': len(source.content)}, family='components'))
            elif tail.startswith('references/') and p.suffix == '.md':
                add(_record(f'reference:{skill}/{tail.removeprefix("references/")}', 'reference', f'{skill}/{p.name}', path, whole(source), attrs={'skill': skill, 'bytes': len(source.content)}, family='components'))
            elif '/' not in tail or tail.split('/')[0] in ('scripts', 'assets', 'templates'):
                add(_record(f'bundle-file:{skill}/{tail}', 'bundle-file', f'{skill}/{tail}', path, whole(source), attrs={'skill': skill}, family='components'))
        elif path.startswith('docs/decisions/') and p.suffix == '.md':
            header = source.lines[:14]
            status = next(((i, re.sub(r'^[>*+\- ]*', '', line).replace('**', '')) for i, line in enumerate(header, 1)
                          if re.match(r'(?i)^status\s*:', re.sub(r'^[>*+\- ]*', '', line).replace('**', ''))), None)
            text = status[1].split(':', 1)[1].strip() if status else ''
            word = status_marker(text).split(' ', 1)[0]
            states: dict[str, State] = {'accepted': 'live', 'proposed': 'proposed', 'superseded': 'historical', 'rejected': 'rejected', 'deprecated': 'deprecated'}
            state = states.get(word, 'historical')
            date = DATE.search('\n'.join(header))
            add(_record(f'decision:{p.stem}', 'decision', p.stem, path, (source.span(1, min(14, len(source.lines))),),
                attrs={'date': date.group() if date else '', 'status_text': text[:200]}, authority='live-contract' if state == 'live' else 'historical-evidence', state=state, family='decisions'))
        elif path.startswith('docs/reviews/') and p.suffix == '.md':
            batch = re.search(r'-eval-(\d{8}T\d{6}Z-[0-9a-f]{8})\.md$', p.name)
            date = DATE.match(p.name)
            attrs = {'date': date.group() if date else '', 'banner': 'Status' in '\n'.join(source.lines[:8]), 'batches': sorted(set(BATCH.findall(source.text)))}
            if batch:
                attrs['batch'] = batch.group(1)
            review_id = p.relative_to('docs/reviews').with_suffix('').as_posix()
            add(_record(f'review:{review_id}', 'review', p.stem, path, whole(source), attrs=attrs,
                authority='generated' if batch else 'historical-evidence', state='generated' if batch else 'historical', family='reviews'))
        elif path.startswith(('evals/scenarios/', 'evals/build-scenarios/')) and p.suffix in ('.yaml', '.yml'):
            meta, _ = scenario_fields(source)
            if 'id' not in meta:
                continue
            routing = meta.get('routing') or {}
            alt = routing.get('expected_alternative')
            alt = alt if isinstance(alt, str) else f'{alt.get("kind")}:{alt.get("name")}' if isinstance(alt, dict) else ''
            add(_record(f'scenario:{meta["id"]}', 'scenario', str(meta['id']), path,
                yaml_key_spans(source, ('id', 'mode', 'split', 'routing', 'threshold', 'agent', 'target', 'skill')),
                authority='live-contract', attrs={'mode': meta.get('mode', ''), 'split': meta.get('split', ''), 'expect': routing.get('expect', ''), 'threshold': meta.get('threshold'), 'expected_alternative': alt, 'file': path}, family='scenarios'))
        elif path.startswith(('scripts/', 'evals/')) and len(p.parts) == 2 and p.name.startswith('test_') and p.suffix == '.py':
            add(_record(f'test:{path}', 'test', path, path, whole(source), family='tests'))
        elif path.startswith('docs/probes/') and len(p.parts) == 3:
            roadmap = corpus.get('docs/fleet-roadmap.md')
            links = tuple(roadmap.span(i, i) for i, line in enumerate(roadmap.lines, 1) if any(
                (resolved_link(roadmap, raw, corpus.by_path) or (None,))[0] == path for raw in link_targets(line))) if roadmap else ()
            add(_record(f'probe:{p.stem}', 'probe', p.stem, path, spans(whole(source), links or (whole(roadmap) if roadmap else ())),
                authority='live-contract' if links else 'historical-evidence', state='live' if links else 'historical',
                attrs={'linked_from_roadmap': bool(links)}, family='probes', kind=PK.JOINED))
    return _new_records(records, inputs)


def _roadmap_records(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    records, add = _record_builder(inputs)
    roadmap = corpus.get('docs/fleet-roadmap.md')
    if roadmap:
        for item, start, _, fields, positions in corpus.roadmap_entries:
            proof = spans((roadmap.span(start, start),), *(positions.values()))
            add(_record(f'roadmap-item:{item}', 'roadmap-item', item, roadmap.path, proof,
                authority='live-contract', attrs={'status': status_marker(fields.get('Status', '')), 'status_text': fields.get('Status', '')[:200], 'owner': fields.get('Owner', '')[:200], 'fields': sorted(fields)}, family='roadmap', selector=item, kind=PK.NORMALIZED, cls=EC.CONTRACT))
            owner = fields.get('Owner', '')
            proof = positions.get('Owner', ())
            if not proof:
                continue
            components = {r.name for r in records.values() if r.node.type in ('skill', 'command')}
            for name in re.findall(r'`([a-z][a-z0-9-]+)`', owner):
                if f'owner:{name}' not in records and name not in components:
                    add(_record(f'owner:{name}', 'owner', name, roadmap.path, proof, authority='external', attrs={'kind': 'human'}, family='owners', selector=f'owner:{name}'))
            human = human_owner(owner)
            if human:
                key = f'owner:{slug(human)}'
                if key not in records:
                    add(_record(key, 'owner', human, roadmap.path, proof, authority='external', attrs={'kind': 'human'}, family='owners', selector=key))
    closed = corpus.get('docs/roadmap-closed.md')
    if closed:
        for i, line in enumerate(closed.lines, 1):
            cells = table_cells(line)
            if len(cells) < 3 or not line.startswith('| `'):
                continue
            for item in ITEM.findall(cells[0]):
                if f'roadmap-item:{item}' not in records:
                    add(_record(f'roadmap-item:{item}', 'roadmap-item', item, closed.path, (closed.span(i, i),),
                        authority='historical-evidence', state='historical', attrs={'closed': cells[1].strip(), 'disposition': plain(cells[2])[:200]}, family='roadmap', selector=item))
    return _new_records(records, inputs)


def _rule_records(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    records, add = _record_builder(inputs)
    rules = corpus.get('docs/rules.md')
    if rules:
        section, section_line = '', None
        for i, line in enumerate(rules.lines, 1):
            if line.startswith('## '):
                section, section_line = line[3:].strip(), i
            if not _table_data(rules.lines, i):
                continue
            cells = table_cells(line)
            if len(cells) < 2:
                continue
            statement = plain(cells[0])
            key = stable_id('rule', rules.path, statement)
            proof = (rules.span(i, i),) + ((rules.span(section_line, section_line),) if section_line else ())
            add(_record(key, 'rule', statement[:80], rules.path, spans(proof), authority='live-contract', attrs={'section': section, 'statement': statement, 'source_text': plain(cells[1])}, family='rules', selector=key))
    return _new_records(records, inputs)


def _schema_records(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    records, add = _record_builder(inputs)
    catalog = corpus.get('schemas/catalog-v1.json')
    if catalog:
        for entry in corpus.catalog_entries():
            proof = whole(catalog)  # All catalog fields determine identity/path/state/relations.
            path = entry['canonical_path']
            add(_record(f'schema:{entry["id"]}', 'schema', entry['id'], path, proof, authority='live-contract', attrs={'status': entry['status'], 'version': entry['version']}, family='schemas', selector=f'schema:{entry["id"]}', cls=EC.CONTRACT))
            for projection in entry.get('generated_projections', []):
                if projection.startswith('docs/fleet-atlas/'):
                    add(_record(f'schema-projection:{projection}', 'schema-projection', projection, projection, proof,
                        authority='generated', state='generated', attrs={'schema': entry['id']}, family='schemas'))
    catalog_paths = {r.node.path for r in records.values() if r.node.type == 'schema'}
    for source in corpus.schema_sources:
        if source.path in catalog_paths:
            continue
        declaration = corpus.parsed(source)
        if not isinstance(declaration, dict):
            continue
        name = PurePosixPath(source.path).name.removesuffix('.schema.json')
        attrs = {target: declaration[key] for key, target in
                 (('$id', 'schema_uri'), ('$schema', 'dialect'), ('title', 'title'), ('type', 'type'))
                 if key in declaration}
        add(_record(f'schema:{name}', 'schema', name, source.path, whole(source),
                    authority='live-contract', attrs=attrs, family='schemas'))
    for schema_id, projection, proof in corpus.projections:
        add(_record(f'schema-projection:{projection}', 'schema-projection', projection, projection, proof,
                    authority='generated', state='generated', attrs={'schema': schema_id.removeprefix('schema:')},
                    family='schemas', cls=EC.CONTRACT, kind=PK.JOINED))
    return _new_records(records, inputs)


def _roster_records(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    records, add = _record_builder(inputs)
    roster = corpus.get('AGENTS.md')
    if roster:
        for i, cells in roster_rows(roster):
            name = plain(cells[0])
            if f'agent:{name}' not in records:
                continue
            lane = plain(cells[1])
            key = 'capability:' + slug(lane)[:60]
            if key not in records:
                add(_record(key, 'capability', lane, roster.path, (roster.span(i, i),), attrs={'lane': lane},
                    selector=key, family='owners', kind=PK.INFERRED, cls=EC.INFERRED))
    return _new_records(records, inputs)


def _contract_records(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    sources = corpus.by_path
    records, add = _record_builder(inputs)
    hook = corpus.get('hooks/hooks.json')
    if hook and 'readonly-guard.py' in hook.text:
        add(_record('hook:readonly-guard', 'hook', 'readonly-guard', hook.path, whole(hook), authority='live-contract', attrs={'matcher': 'Bash'}, selector='hook:readonly-guard', family='contracts', cls=EC.CONTRACT))
    for projection, canonical, proof in corpus.generated:
        if projection in sources:
            add(_record('generated-projection:' + projection, 'generated-projection', projection, projection,
                spans(proof, whole(sources[projection]), whole(sources[canonical])), authority='generated', state='generated',
                attrs={'bytes': len(sources[projection].content)}, family='generated', cls=EC.CONTRACT, kind=PK.JOINED))
    return _new_records(records, inputs)


def _resolve_catalog(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    sources = corpus.by_path
    records, add = _record_builder(inputs)
    catalog = corpus.get('schemas/catalog-v1.json')
    # A unique catalog schema represents its complete canonical file. If another
    # domain record already owns that whole-file selector, keep the typed schema ID.
    for key, record in tuple(records.items()):
        if record.node.type == 'schema' and not any(
            other.node.id != key and other.node.path == record.node.path
            and (other.node.selector == WHOLE_DOCUMENT or other.node.type == 'schema')
            for other in records.values()
        ):
            records[key] = replace(record, node=replace(record.node, selector=WHOLE_DOCUMENT))
    # Exact full-file targets are explicit; no path-first selection erases domain nodes.
    needed = {p for p in sources if live_guide(p)}
    needed.update(r.node.path for r in records.values())
    needed.update(mapping.canonical for mapping in corpus.generated)
    if 'scripts/fleet_atlas_v2_extract.py' in sources:
        needed.add('scripts/fleet_atlas_v2_extract.py')
    for source in corpus.sources:
        if source.path.endswith('.md'):
            needed.update(hit[0] for raw in link_targets(source.text) if (hit := resolved_link(source, raw, sources)))
    if catalog:
        needed.update(e['validator'] for e in corpus.catalog_entries() if e.get('validator') in sources)
    for source in corpus.schema_sources:
        declaration = corpus.parsed(source)
        if isinstance(declaration, dict) and declaration.get('x-fleet-validator') in sources:
            needed.add(declaration['x-fleet-validator'])
    for path in sorted(needed):
        if path not in sources or not sources[path].content:
            continue
        whole_records = [r for r in records.values() if r.node.path == path and r.node.selector == WHOLE_DOCUMENT]
        if not whole_records:
            typ = 'validator' if path.startswith('scripts/') and path.endswith('.py') else 'document'
            authority: Authority = 'live-contract' if live_guide(path) else 'historical-evidence' if path.startswith('docs/') else 'canonical'
            add(_record(f'{typ}:{path}', typ, path, path, whole(sources[path]), authority=authority))
    return StageOutput(tuple(records[k] for k in sorted(records)))


def _table_data(lines: Sequence[str], i: int) -> bool:
    line = lines[i - 1].strip()
    return line.startswith('|') and not SEPARATOR.match(line) and not (i < len(lines) and SEPARATOR.match(lines[i].strip()))


def roster_rows(source: Source) -> Iterator[tuple[int, tuple[str, ...]]]:
    active = False
    for i, line in enumerate(source.lines, 1):
        if not active:
            active = line.startswith('|') and 'Delegates to' in line
            continue
        if not line.startswith('|'):
            break
        cells = tuple(cell.strip() for cell in line.strip('|').split('|'))
        if _table_data(source.lines, i) and len(cells) >= 4:
            yield i, cells


def _path_expression(node: ast.AST, environment: Mapping[str, str]) -> str | None:
    """Interpret only path construction syntax; never eval a source expression."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return environment.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = _path_expression(node.left, environment), _path_expression(node.right, environment)
        return posixpath.join(left, right) if isinstance(left, str) and isinstance(right, str) else None
    if isinstance(node, ast.JoinedStr):
        pieces = []
        for piece in node.values:
            part = _path_expression(piece.value if isinstance(piece, ast.FormattedValue) else piece, environment)
            if not isinstance(part, str):
                return None
            pieces.append(part)
        return ''.join(pieces)
    if isinstance(node, ast.Attribute):
        value = _path_expression(node.value, environment)
        if isinstance(value, str) and node.attr in ('stem', 'name', 'suffix'):
            return str(getattr(PurePosixPath(value), node.attr))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == 'Path' and len(node.args) == 1:
            return _path_expression(node.args[0], environment)
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'relative_to' and len(node.args) == 1:
            value, base = _path_expression(node.func.value, environment), _path_expression(node.args[0], environment)
            if isinstance(value, str) and isinstance(base, str):
                try:
                    return PurePosixPath(value).relative_to(base).as_posix()
                except ValueError:
                    return None
    return None


def generated_mappings(corpus: Corpus) -> tuple[GeneratedMapping, ...]:
    source = corpus.get('scripts/generate_platform_adapters.py')
    if source is None:
        return ()
    tree = _ast(source)
    constants, constant_spans = {'root': ''}, {}
    for statement in (s for s in tree.body if isinstance(s, ast.Assign)):
        for target in statement.targets:
            if isinstance(target, ast.Name) and (value := _path_expression(statement.value, constants)) is not None:
                constants[target.id] = value
                constant_spans[target.id] = _node_span(source, statement)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'expected_outputs'), None)
    if function is None:
        return ()
    assert function.end_lineno is not None  # ast.parse sets every end_lineno.
    bound_constants = sorted({n.id for n in ast.walk(function) if isinstance(n, ast.Name)} & constant_spans.keys())
    parent = {child: node for node in ast.walk(function) for child in ast.iter_child_nodes(node)}
    result: dict[tuple[str, str], tuple[Span, ...]] = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == 'outputs'):
                continue
            loops, cursor = [], parent.get(node)
            while cursor is not None:
                if isinstance(cursor, ast.For):
                    loops.append(cursor)
                cursor = parent.get(cursor)
            family = next((loop.iter.id for loop in loops if isinstance(loop.target, ast.Name) and loop.target.id == 'source'
                           and isinstance(loop.iter, ast.Name) and loop.iter.id in ('agents', 'commands', 'skill_files')), None)
            if family:
                inputs = [s.path for s in corpus.sources if
                          (family == 'agents' and re.fullmatch(r'agents/[^/]+\.md', s.path)) or
                          (family == 'commands' and re.fullmatch(r'commands/[^/]+\.md', s.path)) or
                          (family == 'skill_files' and s.path.startswith('skills/'))]
            else:
                inputs = [constants['COPILOT_HOOKS_SOURCE']] if 'COPILOT_HOOKS_SOURCE' in constants and 'HOOKS' in ast.unparse(target.slice) else []
            for canonical in inputs:
                environment = {**constants, 'source': canonical,
                               'relative': canonical.removeprefix('skills/')}
                projection = _path_expression(target.slice, environment)
                if not projection:
                    continue
                # The full mapping body includes branch predicates and output expressions, not
                # merely a matching signature; constants bind the output-root declarations.
                proof = spans((source.span(function.lineno + 1, function.end_lineno),),
                              tuple(constant_spans[name] for name in bound_constants))
                key = projection, canonical
                result[key] = spans(result.get(key, ()), proof)
    return tuple(GeneratedMapping(projection, canonical, proof) for (projection, canonical), proof in sorted(result.items()))


def _writer_filenames(render: ast.FunctionDef, safe: ast.FunctionDef, build: ast.FunctionDef) -> set[str]:
    """Recognize the closed mapping->return->iteration->payload->publish chain.

    This intentionally abstains on other writer shapes. Occurrences of familiar
    names, discarded calls and assignments in unrelated branches are not lineage.
    """
    def assigned(function: ast.FunctionDef, name: str) -> list[ast.Assign]:
        return [node for node in ast.walk(function) if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]

    def returns_variable(function: ast.FunctionDef, name: str) -> bool:
        returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
        return (len(returns) == 1 and function.body[-1] is returns[0]
                and isinstance(returns[0].value, ast.Name) and returns[0].value.id == name)

    def direct_call_assignment(function: ast.FunctionDef, name: str, callable_name: str) -> bool:
        bound = assigned(function, name)
        return (len(bound) == 1 and bound[0] in function.body
                and isinstance(bound[0].value, ast.Call)
                and isinstance(bound[0].value.func, ast.Name)
                and bound[0].value.func.id == callable_name)

    mapping = assigned(render, 'files')
    if not (len(mapping) == 1 and mapping[0] in render.body
            and isinstance(mapping[0].value, ast.Dict) and not mapping[0].value.keys
            and returns_variable(render, 'files')):
        return set()
    # Do not trust a declared dictionary if another call can remove or replace its
    # entries, or if an alias is allowed to mutate it beyond the recognized writes.
    for function in (render, build):
        for node in ast.walk(function):
            if isinstance(node, ast.Delete):
                return set()
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name) and node.value.id == 'files':
                return set()
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == 'files' and node.func.attr not in ('items', 'keys', 'values', 'get')):
                    return set()
                if (any(isinstance(arg, ast.Name) and arg.id == 'files' for arg in (*node.args, *(k.value for k in node.keywords)))
                        and not (isinstance(node.func, ast.Name) and node.func.id == 'sorted')):
                    return set()
    writes = {target.slice.value for node in render.body if isinstance(node, ast.Assign)
              for target in node.targets if isinstance(target, ast.Subscript)
              and isinstance(target.value, ast.Name) and target.value.id == 'files'
              and isinstance(target.slice, ast.Constant) and isinstance(target.slice.value, str)
              and mapping[0].lineno < node.lineno < render.body[-1].lineno}
    safe_current = assigned(safe, 'current')
    safe_loop = next((n for n in safe.body if isinstance(n, ast.For)
                      and ast.unparse(n.target) == 'part' and ast.unparse(n.iter) == 'OUTPUT.parts'), None)
    if (not returns_variable(safe, 'current') or len(safe_current) != 2 or safe_loop is None
            or ast.unparse(safe_current[0].value) != 'root'
            or safe_current[0] not in safe.body or safe_current[1] not in safe_loop.body
            or ast.unparse(safe_current[1].value) != 'current / part'):
        return set()
    if not (direct_call_assignment(build, 'files', 'render_files')
            and direct_call_assignment(build, 'output', '_safe_output')):
        return set()
    if any(isinstance(n, ast.Return) and n is not build.body[-1] for n in ast.walk(build)):
        return set()
    if any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Subscript)
           and isinstance(t.value, ast.Name) and t.value.id == 'files' for t in n.targets)
           for n in ast.walk(build)):
        return set()
    for loop in (n for n in build.body if isinstance(n, ast.For) and ast.unparse(n.target) == 'name'):
        iterator = loop.iter
        if not (ast.unparse(iterator) == 'files' or (isinstance(iterator, ast.Call)
                and isinstance(iterator.func, ast.Name) and iterator.func.id == 'sorted'
                and iterator.args and ast.unparse(iterator.args[0]) == 'files')):
            continue
        if max(assigned(build, 'files')[0].lineno, assigned(build, 'output')[0].lineno) >= loop.lineno:
            continue
        temporary_writes = []
        for block in (n for n in loop.body if isinstance(n, ast.With)):
            for item in block.items:
                call = item.context_expr
                if (not isinstance(call, ast.Call) or ast.unparse(call.func) != 'tempfile.NamedTemporaryFile'
                        or not isinstance(item.optional_vars, ast.Name)
                        or not any(k.arg == 'dir' and ast.unparse(k.value) == 'output' for k in call.keywords)):
                    continue
                handle = item.optional_vars.id
                bindings = [n for n in block.body if isinstance(n, ast.Assign)
                            and any(isinstance(t, ast.Name) and t.id == 'temporary' for t in n.targets)
                            and ast.unparse(n.value) == f'Path({handle}.name)']
                payloads = [n for n in block.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
                            and ast.unparse(n.value.func) == f'{handle}.write' and len(n.value.args) == 1
                            and ast.unparse(n.value.args[0]) == 'files[name]']
                if len(bindings) == len(payloads) == 1:
                    temporary_writes.append(block)
        if len(temporary_writes) != 1 or len(assigned(build, 'temporary')) != 1:
            continue
        assert temporary_writes[0].end_lineno is not None  # ast.parse sets every end_lineno.
        publications = []
        for child in loop.body:
            body = child.body if isinstance(child, ast.Try) else [child]
            for statement in body:
                if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                        and ast.unparse(statement.value.func) == 'os.replace'
                        and [ast.unparse(arg) for arg in statement.value.args] == ['temporary', 'output / name']
                        and statement.lineno > temporary_writes[0].end_lineno):
                    publications.append(statement)
        if len(publications) == 1:
            return writes
    return set()


def standalone_projections(corpus: Corpus) -> tuple[WriterProjection, ...]:
    """Bind the v2 schema's explicit output declaration to its actual writer mapping.

    Merely declaring an output, mentioning its path, or having a function with the
    expected name does not establish the generated relationship.
    """
    sources = corpus.by_path
    implementation = corpus.get('scripts/fleet_atlas_v2_artifacts.py')
    if implementation is None:
        return ()
    tree = _ast(implementation)
    assignments = [n for n in tree.body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'OUTPUT' for t in n.targets)]
    if len(assignments) != 1:
        return ()
    output = _path_expression(assignments[0].value, {})
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    if not output or not {'render_files', '_safe_output', 'build'} <= functions.keys():
        return ()
    render, safe, build = (functions[name] for name in ('render_files', '_safe_output', 'build'))
    writes = _writer_filenames(render, safe, build)
    if not writes:
        return ()
    mapping_proof = tuple(_node_span(implementation, n) for n in (assignments[0], render, safe, build))
    result = []
    for source in corpus.schema_sources:
        declaration = corpus.parsed(source)
        if not isinstance(declaration, dict):
            continue
        validator = declaration.get('x-fleet-validator')
        if validator not in sources:
            continue
        assert validator is not None  # sources holds only str paths.
        for projection in declaration.get('x-fleet-generated-projections', []):
            if projection in {posixpath.join(output, filename) for filename in writes}:
                result.append(WriterProjection('schema:' + PurePosixPath(source.path).name.removesuffix('.schema.json'), projection,
                                               spans(whole(source), mapping_proof, whole(sources[validator]))))
    return tuple(result)


# A repository-root binding: both forms explicitly derive the directory from the test's own location.
REPOSITORY_ROOT = re.compile(r'Path\(__file__\)\.resolve\(\)\.(?:parents\[1\]|parent\.parent)')


def rooted_reads(source: Source) -> tuple[tuple[str, tuple[Span, ...]], ...]:
    """Rooted read dependencies only, with binding and helper-body provenance.

    A literal, fixture write, temporary-root read or shadowed ROOT is not verification
    authority. This recognizes static paths and first-argument read helpers, not arbitrary
    Python dataflow. Unresolved dynamic paths yield no verified_by claim.
    """
    tree = _ast(source)
    path_imports = tuple(_node_span(source, node) for node in tree.body
                         if isinstance(node, ast.ImportFrom) and node.module == 'pathlib'
                         and any(alias.name == 'Path' and alias.asname in (None, 'Path') for alias in node.names))
    bindings: dict[str, list[ast.Assign]] = {}
    for statement in (s for s in tree.body if isinstance(s, ast.Assign)):
        for target in statement.targets:
            if isinstance(target, ast.Name):
                bindings.setdefault(target.id, []).append(statement)
    pathlib_path = bool(path_imports) and not bindings.get('Path')
    root_bindings = {name: declarations[0] for name, declarations in bindings.items() if len(declarations) == 1
                     and REPOSITORY_ROOT.fullmatch(ast.unparse(declarations[0].value)) and pathlib_path}
    # Nearest enclosing function of every node (the module for top-level code), computed
    # in one breadth-first pass: a parent is always visited before its children.
    enclosing: dict[ast.AST, ast.AST] = {tree: tree}
    for node in ast.walk(tree):
        inner = node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else enclosing[node]
        for child in ast.iter_child_nodes(node):
            enclosing[child] = inner
    scope_roots: dict[ast.AST, Mapping[str, ast.Assign]] = {}
    def roots_in(call_scope: ast.AST) -> Mapping[str, ast.Assign]:
        """Repository-root bindings visible in one scope; a pure function of that scope."""
        if call_scope in scope_roots:
            return scope_roots[call_scope]
        stores = [n for n in ast.walk(call_scope) if isinstance(n, ast.Name)
                  and isinstance(n.ctx, ast.Store) and enclosing[n] is call_scope] if call_scope is not tree else []
        shadowed = {n.id for n in stores}
        parameters: set[str] = set()
        if isinstance(call_scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = {a.arg for a in (*call_scope.args.posonlyargs, *call_scope.args.args, *call_scope.args.kwonlyargs)}
            shadowed.update(parameters)
        bindings_here = {name: declaration for name, declaration in root_bindings.items() if name not in shadowed}
        if call_scope is not tree and pathlib_path and 'Path' not in shadowed:
            for declaration in ast.walk(call_scope):
                if not isinstance(declaration, ast.Assign) or enclosing[declaration] is not call_scope:
                    continue
                if not REPOSITORY_ROOT.fullmatch(ast.unparse(declaration.value)):
                    continue
                for target in declaration.targets:
                    if (isinstance(target, ast.Name) and target.id not in parameters
                            and sum(n.id == target.id for n in stores) == 1):
                        bindings_here[target.id] = declaration
        scope_roots[call_scope] = MappingProxyType(bindings_here)
        return scope_roots[call_scope]
    def rooted(expression: ast.expr, call_scope: ast.AST,
               substitutions: Mapping[str, str] | None = None) -> tuple[str, tuple[Span, ...]] | None:
        substituted = substitutions or {}
        bindings_here = roots_in(call_scope)
        environment = {name: '' for name in bindings_here}
        environment.update(substituted)
        value = _path_expression(expression, environment)
        names = {n.id for n in ast.walk(expression) if isinstance(n, ast.Name)}
        bound_roots = (names & bindings_here.keys()) - substituted.keys()
        if value and (bound_roots or names & substituted.keys()) and not value.startswith(('/', '../')):
            proof = tuple(_node_span(source, bindings_here[n]) for n in sorted(bound_roots))
            return value, spans(proof, path_imports) if bound_roots else proof
        return None
    def read_expression(call: ast.Call) -> ast.expr | None:
        if isinstance(call.func, ast.Attribute) and call.func.attr in ('read_text', 'read_bytes'):
            return call.func.value
        if isinstance(call.func, ast.Name) and call.func.id == 'open' and call.args:
            position, expression = 1, call.args[0]
        elif isinstance(call.func, ast.Attribute) and call.func.attr == 'open':
            position, expression = 0, call.func.value
        else:
            return None
        mode_node = next((k.value for k in call.keywords if k.arg == 'mode'), call.args[position] if len(call.args) > position else ast.Constant('r'))
        if not isinstance(mode_node, ast.Constant) or not isinstance(mode_node.value, str) or any(c in mode_node.value for c in 'wax+'):
            return None
        return expression
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    written: set[str] = set()
    def write_expression(call: ast.Call) -> ast.expr | None:
        if isinstance(call.func, ast.Attribute) and call.func.attr in ('write_text', 'write_bytes'):
            return call.func.value
        if isinstance(call.func, ast.Name) and call.func.id == 'open' and call.args and read_expression(call) is None:
            return call.args[0]
        if isinstance(call.func, ast.Attribute) and call.func.attr == 'open' and read_expression(call) is None:
            return call.func.value
        return None

    def parameters(function: ast.FunctionDef, call: ast.Call, caller_scope: ast.AST,
                   substitutions: Mapping[str, str]) -> dict[str, str]:
        positional = (*function.args.posonlyargs, *function.args.args)
        arguments = {parameter.arg: value for parameter, value in zip(positional, call.args, strict=False)}  # a call may omit defaulted parameters
        arguments.update({keyword.arg: keyword.value for keyword in call.keywords if keyword.arg})
        values: dict[str, str] = {}
        for name, value in arguments.items():
            hit = rooted(value, caller_scope, substitutions)
            if hit:
                values[name] = hit[0]
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                values[name] = value.value
        return values

    def helper_writes(function: ast.FunctionDef, substitutions: Mapping[str, str], visiting: set[str]) -> set[str]:
        if function.name in visiting:
            # Recursive/mutually recursive helper effects are not proved read-only.
            return set(substitutions.values())
        effects: set[str] = set()
        for call in (n for n in ast.walk(function) if isinstance(n, ast.Call)):
            expression = write_expression(call)
            if expression is not None:
                hit = rooted(expression, function, substitutions)
                effects.update((hit[0],) if hit else substitutions.values())
            elif isinstance(call.func, ast.Name) and call.func.id in functions:
                callee = functions[call.func.id]
                effects.update(helper_writes(callee, parameters(callee, call, function, substitutions), visiting | {function.name}))
        return effects

    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    for call in calls:
        expression = write_expression(call)
        if expression is not None and (hit := rooted(expression, enclosing[call])):
            written.add(hit[0])
        if isinstance(call.func, ast.Name) and call.func.id in functions:
            function = functions[call.func.id]
            written.update(helper_writes(function, parameters(function, call, enclosing[call], {}), set()))
    found: dict[str, tuple[Span, ...]] = {}
    for call in calls:
        expression = read_expression(call)
        candidates = []
        if expression is not None:
            hit = rooted(expression, enclosing[call])
            if hit:
                candidates.append((hit[0], spans(hit[1], (_node_span(source, call),))))
        elif isinstance(call.func, ast.Name) and call.func.id in functions and call.args:
            function = functions[call.func.id]
            if not function.args.args:
                continue
            parameter = function.args.args[0].arg
            arg = _path_expression(call.args[0], {})
            rooted_arg = rooted(call.args[0], enclosing[call])
            for helper_call in (n for n in ast.walk(function) if isinstance(n, ast.Call)):
                expr = read_expression(helper_call)
                if expr is None:
                    continue
                if rooted_arg and isinstance(expr, ast.Name) and expr.id == parameter:
                    candidates.append((rooted_arg[0], spans(rooted_arg[1], (_node_span(source, function), _node_span(source, call)))))
                elif isinstance(arg, str):
                    hit = rooted(expr, function, {parameter: arg})
                    # A helper parameter alone is not rooted; an actual repository ROOT must
                    # also appear in its read expression.
                    if hit and hit[1]:
                        candidates.append((hit[0], spans(hit[1], (_node_span(source, function), _node_span(source, call)))))
        for path, proof in candidates:
            if path not in written:
                found[path] = spans(found.get(path, ()), proof)
    return tuple(sorted(found.items()))


class _Relations:
    """The relationship pass's shared state over one derivation's records.

    Emitters add facts only through add(), directly or via edge(), link() and unknown():
    repeated claims merge their witnesses, and a conflicting claim under the same identity
    fails the derivation.
    """

    def __init__(self, corpus: Corpus, records: tuple[Record, ...]) -> None:
        self.corpus = corpus
        self.sources = corpus.by_path
        self.records = records
        self.by_id = {r.node.id: r for r in records}
        self.by_path: dict[str, list[Record]] = {}
        for r in records:
            self.by_path.setdefault(r.node.path, []).append(r)
        self.index = NodeIndex(tuple(r.node for r in records))
        self.facts: dict[str, Fact] = {}

    def add(self, fact: Fact) -> None:
        previous = self.facts.get(fact.id)
        if previous and previous != fact:
            if (previous.subject, previous.predicate, previous.object, previous.qualifiers, previous.evidence_class, previous.proof.kind) != (fact.subject, fact.predicate, fact.object, fact.qualifiers, fact.evidence_class, fact.proof.kind):
                raise ValueError(f'conflicting extracted relationship: {fact.id}')
            # Facts added here cite spans only, so neither proof holds a FactRef.
            inputs = cast('tuple[Span, ...]', previous.proof.inputs + fact.proof.inputs)
            fact = replace(fact, proof=replace(fact.proof, inputs=spans(inputs)))
        self.facts[fact.id] = fact

    def edge(self, kind: str, subject: str, target: str, proof: tuple[Span, ...], *, attrs: dict[str, Any] | None = None,
             key: str = '', cls: EC = EC.EXTRACTED, proof_kind: PK | None = None) -> None:
        if subject not in self.by_id or target not in self.by_id:
            return
        proof_kind = proof_kind or (PK.INFERRED if cls == EC.INFERRED else PK.JOINED if len({p.path for p in proof}) > 1 else PK.EXTRACTED)
        self.add(Fact(stable_id('edge', kind, subject, target, key), subject, kind, target, cls,
                      Proof(proof_kind, spans(proof), EVALUATOR), pairs(attrs or {})))

    def link(self, kind: str, subject: str, dest: Record, raw: str, witness: tuple[Span, ...], *, key: str = '') -> None:
        """An edge along a resolved link; a section link also cites the section it selects."""
        if '#' not in raw:
            self.edge(kind, subject, dest.node.id, witness, key=key)
            return
        # A section-scoped claim and a bare file claim are different facts;
        # repeated links to the same section still merge all their witnesses.
        section = raw.split('#', 1)[1]
        self.edge(kind, subject, dest.node.id, spans(witness, dest.spans), key=key + '#anchor=' + section,
                  attrs={'anchor': section})

    def owner(self, name: str) -> str:
        """The node an Owner field's `name` denotes: the agent of that name, else its owner node."""
        return f'agent:{name}' if f'agent:{name}' in self.by_id else f'owner:{name}'

    def unknown(self, subject: str, code: str, message: str, proof: tuple[Span, ...], needed: str, *,
                absence: bool = False) -> None:
        self.add(Fact(stable_id('unknown', code, subject, message), subject, 'unknown', message, EC.UNKNOWN,
                      Proof(PK.ABSENCE if absence else PK.COMPUTED, spans(proof), EVALUATOR,
                            self.corpus.snapshot.tree_digest if absence else None), pairs({'code': code, 'neededEvidence': needed, 'path': self.by_id[subject].node.path})))

    def resolve(self, source: Source, raw: str, *, types: set[str] | None = None) -> Record | None:
        hit = resolved_link(source, raw, self.sources)
        if not hit:
            return None
        path, fragment = hit
        candidates = [r for r in self.by_path.get(path, ()) if not types or r.node.type in types]
        if fragment:
            matches = [r for r in candidates if fragment in (r.node.selector, r.node.id, anchor(r.name))
                       or (r.node.type == 'roadmap-item' and fragment.startswith(r.name.lower() + '-'))]
            if len(matches) > 1:
                raise ValueError(f'ambiguous typed link: {source.path} -> {raw}')
            if matches:
                return matches[0]
            # A real section of an otherwise whole-document entity remains that
            # entity, with the exact selector witness retained in its edge proof.
            target_source = self.sources[path]
            headings = self.corpus.headings(target_source)
            whole_candidates = [r for r in candidates if r.node.selector == WHOLE_DOCUMENT]
            if fragment in headings and len(whole_candidates) == 1:
                target = whole_candidates[0]
                line = headings[fragment]
                return replace(target, spans=spans(target.spans, (target_source.span(line, line),)))
            return None
        if types and len(candidates) == 1:
            return candidates[0]
        try:
            return self.by_id[self.index.resolve(NodeRef(path, None, WHOLE_DOCUMENT)).id]
        except ValueError:
            return None


def _agent_method_edges(rel: _Relations, record: Record, source: Source) -> None:
    """A method table or Load line selecting a skill for a stated condition."""
    # header_line is read only under nonempty load_columns, which its table header sets with it.
    load_columns: tuple[int, ...] = ()
    header_line, inferred_method = 0, False
    for i, line in enumerate(source.lines, 1):
        stripped = line.strip()
        if stripped.startswith('|') and i < len(source.lines) and SEPARATOR.match(source.lines[i].strip()):
            headers = [plain(cell) for cell in table_cells(line)]
            load_columns = tuple(j for j, header in enumerate(headers) if re.search(r'\b(?:load|skill|method)\b', header, re.I))
            inferred_method = not any(re.search(r'\b(?:load|skill)\b', headers[j], re.I) for j in load_columns)
            header_line = i
            continue
        if not stripped.startswith('|'):
            load_columns = ()
        if load_columns and _table_data(source.lines, i):
            cells = table_cells(line)
            selected = ' '.join(cells[j] for j in load_columns if j < len(cells))
            condition = plain(cells[0])
            proof: tuple[Span, ...] = (source.span(header_line, header_line), source.span(i, i))
        elif re.match(r'^Load\s+`', stripped):
            selected, condition, proof = stripped, plain(stripped), (source.span(i, i),)
            inferred_method = False
        else:
            continue
        for name in re.findall(r'`([a-z][a-z0-9-]+)`', selected):
            target = f'skill:{name}'
            if target in rel.by_id:
                rel.edge('loads_when', record.node.id, target, spans(proof, rel.by_id[target].spans),
                         key=condition, attrs={'predicate': condition, 'via': 'agent-method'},
                         cls=EC.INFERRED if inferred_method else EC.EXTRACTED,
                         proof_kind=PK.INFERRED if inferred_method else PK.JOINED)


def _bundle_citation(rel: _Relations, record: Record, source: Source) -> None:
    skill = record.attributes['skill']
    rel.edge('cites', f'skill:{skill}', record.node.id, record.spans)


def _skill_reference_edges(rel: _Relations, record: Record, source: Source) -> None:
    """Each linked reference, with the routing-table condition that loads it."""
    references, routing = defaultdict(list), defaultdict(list)
    for i, line in enumerate(source.lines, 1):
        targets = [raw for raw in link_targets(line) if raw.startswith(('references/', './references/'))]
        if targets and _table_data(source.lines, i):
            predicate = plain(line.strip('|').split('|')[0])
            for target in targets:
                routing[target].append((predicate, i))
        for target in targets:
            references[target].append(i)
    for target, positions in references.items():
        dest = rel.resolve(source, target, types={'reference'})
        if not dest:
            rel.unknown(record.node.id, 'extract.skill-link-unresolved', f'{source.path}:{positions[0]} links {target}, which does not exist', (source.span(positions[0], positions[0]),), 'Restore the file or remove the link', absence=True)
            continue
        for predicate, row in routing.get(target, [('UNKNOWN', positions[0])]):
            rel.edge('loads_when', record.node.id, dest.node.id, (source.span(row, row),), attrs={'predicate': predicate}, key=predicate)


def _rule_source_edges(rel: _Relations, record: Record, source: Source) -> None:
    node = record.node
    row = next((p for p in record.spans if p.start_line == p.end_line and source.lines[p.start_line - 1].startswith('|')), None)
    if row:
        links = link_targets(source.lines[row.start_line - 1])
        if not links:
            rel.unknown(node.id, 'extract.rule-source-unlinked', f'{source.path}:{row.start_line} names its source in prose only: {cast("str", record.attributes["source_text"])[:80]}', (row,), 'Link the primary source')
        for raw in links:
            dest = rel.resolve(source, raw)
            if dest:
                rel.link('governed_by', node.id, dest, raw, (row,))
            else:
                rel.unknown(node.id, 'extract.rule-source-missing', f'{source.path}:{row.start_line} links {raw}, which does not resolve', (row,), 'Fix the link or supply its target', absence=True)


def _review_citations(rel: _Relations, record: Record, source: Source) -> None:
    node = record.node
    for i, line in enumerate(source.lines, 1):
        for raw in link_targets(line):
            dest = rel.resolve(source, raw)
            if dest and dest.node.id != node.id:
                rel.link('cites', node.id, dest, raw, (source.span(i, i),), key=str(i))
            elif resolved_link(source, raw, rel.sources) and '#' in raw:
                rel.unknown(node.id, 'extract.link-selector-unresolved', f'{source.path}:{i} selector does not resolve: {raw}', (source.span(i, i),), 'Correct the section selector or restore its exact target', absence=True)


def _scenario_edges(rel: _Relations, record: Record, source: Source) -> None:
    """A scenario verifies its target, or records a routing near miss and its alternative."""
    node = record.node
    data, _ = scenario_fields(source)
    routing = data.get('routing') or {}
    target = data.get('target') or ({'kind': 'agent', 'name': data['agent']} if data.get('agent') else {'kind': 'skill', 'name': data['skill']} if data.get('skill') else {})
    target_id = f'{target.get("kind")}:{target.get("name")}'
    proof = yaml_key_spans(source, ('target', 'agent', 'skill', 'routing', 'mode'))
    if target_id not in rel.by_id:
        rel.unknown(node.id, 'extract.scenario-target-missing', f'{source.path} targets {target_id}, which has no node', proof, 'Retarget the scenario or restore the component', absence=True)
    elif routing.get('expect') == 'not_fire':
        alt = routing.get('expected_alternative')
        rel.edge('near_miss_for', node.id, target_id, proof, attrs={'expected_alternative': record.attributes['expected_alternative']})
        if isinstance(alt, dict):
            rel.edge('routes_to', node.id, f'{alt.get("kind")}:{alt.get("name")}', proof, attrs={'via': 'expected_alternative'})
    else:
        rel.edge('verified_by', target_id, node.id, proof, attrs={'mode': data.get('mode', '')})
    for item in sorted(set(ITEM.findall(source.text))):
        rel.edge('cites', node.id, f'roadmap-item:{item}', source.locate(item), attrs={'via': 'comment'}, cls=EC.INFERRED)


def _test_verifications(rel: _Relations, record: Record, source: Source) -> None:
    for path, proof in rooted_reads(source):
        if path not in rel.sources:
            continue
        dest = rel.resolve(source, '../' + path)
        if dest:
            rel.edge('verified_by', dest.node.id, record.node.id, proof, attrs={'via': 'file-read'})


def _decision_supersessions(rel: _Relations, record: Record, source: Source) -> None:
    node, sources = record.node, rel.sources
    for i, line in enumerate(source.lines[:14], 1):
        for item in re.findall(r'disposes\s+`([A-Z][A-Z0-9]*-\d{3})`', line):
            rel.edge('supersedes', node.id, f'roadmap-item:{item}', (source.span(i, i),), key='disposes', attrs={'relation': 'disposes'})
        match = re.search(r'\*\*Supersedes:?\*\*:?\s*(.+)|^-?\s*Supersedes:\s*(.+)', line, re.I)
        if match:
            text = (match.group(1) or match.group(2)).strip()
            resolved = [dest for raw in link_targets(line) if (dest := rel.resolve(source, raw))]
            if not resolved:
                rel.unknown(node.id, 'extract.supersedes-unresolved', f'{source.path}:{i} supersedes {text[:120]!r} but names no linked target', (source.span(i, i),), 'Link the superseded decision, rule row, or document')
            for dest in resolved:
                rel.edge('supersedes', node.id, dest.node.id, (source.span(i, i),), attrs={'relation': 'supersedes', 'text': text[:200]})
                needle = text[:40]
                if needle and dest.node.path in sources and needle in sources[dest.node.path].text:
                    rel.edge('contradicts', node.id, dest.node.id, spans((source.span(i, i),), sources[dest.node.path].locate(needle)), key='superseded_text_present', attrs={'detector': 'superseded_text_present', 'message': f'{dest.node.path} still contains superseded text: {needle!r}'}, cls=EC.INFERRED)


def _component_owner_edges(rel: _Relations, record: Record, source: Source) -> None:
    """An Owner line in a skill or command body naming the agent or owner that owns it."""
    for i, line in enumerate(source.lines, 1):
        if not re.match(r'^\*\*Owner:\*\*', line):
            continue
        for name in re.findall(r'`([a-z][a-z0-9-]+)`\s+owns?\b', line):
            owner = rel.owner(name)
            rel.edge('owns', owner, record.node.id, spans((source.span(i, i),), rel.by_id[owner].spans if owner in rel.by_id else ()),
                     attrs={'field': 'Owner'}, proof_kind=PK.JOINED)


# Per-record emitters, in the order each record's relationships are derived.
RECORD_EMITTERS = {
    'agent': (_agent_method_edges,),
    'bundle-file': (_bundle_citation,),
    'skill': (_skill_reference_edges, _component_owner_edges),
    'rule': (_rule_source_edges,),
    'review': (_review_citations,),
    'scenario': (_scenario_edges,),
    'test': (_test_verifications,),
    'decision': (_decision_supersessions,),
    'command': (_component_owner_edges,),
}


def _roadmap_edges(rel: _Relations) -> None:
    """Roadmap items' mentioned dependencies and Owner-field ownership."""
    by_id = rel.by_id
    for item, _, _, fields, positions in rel.corpus.roadmap_entries:
        subject = f'roadmap-item:{item}'
        for field, value in fields.items():
            for other in set(ITEM.findall(value)) - {item}:
                rel.edge('depends_on', subject, f'roadmap-item:{other}', positions[field], key=field,
                         attrs={'field': field, 'detector': 'check_plan_status.prerequisites' if field == 'Prerequisites' else 'extract.roadmap-mention'},
                         cls=EC.CONTRACT if field == 'Prerequisites' else EC.INFERRED)
        owner = fields.get('Owner', '')
        proof = positions.get('Owner', ())
        if proof:
            # A repeated mention re-adds an identical fact, which add() keeps once.
            for name, _ in re.findall(r'`([a-z][a-z0-9-]+)`([^`]*)', owner):
                if f'owner:{name}' in by_id:
                    rel.edge('owns', f'owner:{name}', subject, proof, attrs={'field': 'Owner'})
            human = human_owner(owner)
            if human:
                rel.edge('owns', f'owner:{slug(human)}', subject, proof, attrs={'field': 'Owner'})
            for match in re.finditer(r'`([a-z][a-z0-9-]+)`\s+owns?\b([^.;]+)', owner):
                for name in re.findall(r'`([a-z][a-z0-9-]+)`', match.group(2)):
                    for typ in ('skill', 'command'):
                        target = f'{typ}:{name}'
                        if target in by_id:
                            rel.edge('owns', rel.owner(match.group(1)), target, spans(proof, by_id[target].spans), attrs={'field': 'Owner'}, proof_kind=PK.JOINED)


def _evidence_edges(rel: _Relations) -> set[str]:
    """Roadmap items' and decisions' evidence links and batch joins; returns the reviews they cite.

    Evidence links resolve the selected decision/review, never whichever node sharing
    its path happened to be created first. Batch joins cite BOTH determining records.
    """
    records, sources = rel.records, rel.sources
    incoming_reviews: set[str] = set()
    for record in records:
        if record.node.type not in ('roadmap-item', 'decision'):
            continue
        source = sources[record.node.path]
        if record.node.type == 'roadmap-item':
            if source.path == 'docs/roadmap-closed.md':
                ranges = [(p.start_line, p.end_line) for p in record.spans]
            else:
                ranges = [(entry.start, entry.end) for entry in rel.corpus.roadmap_entries if entry.item == record.name]
        else:
            ranges = [(1, len(source.lines))]
        for i in sorted({i for start, end in ranges for i in range(start, end + 1)}):
            line = source.lines[i - 1]
            for raw in link_targets(line):
                dest = rel.resolve(source, raw, types={'review', 'decision'})
                if dest and dest.node.type in ('review', 'decision') and dest.node.id != record.node.id:
                    rel.link('evidenced_by', record.node.id, dest, raw, (source.span(i, i),))
                    incoming_reviews.add(dest.node.id)
            for batch in set(BATCH.findall(line)):
                targets = [r for r in records if r.node.type == 'review'
                           and batch in cast('tuple[str, ...]', r.attributes.get('batches', ()))]
                if not targets and record.node.type == 'roadmap-item':
                    rel.unknown(record.node.id, 'extract.batch-unresolved', f'{source.path}:{i} cites batch {batch} with no review', (source.span(i, i),), 'Retain the durable review behind the batch', absence=True)
                for target in targets:
                    rel.edge('evidenced_by', record.node.id, target.node.id,
                             spans((source.span(i, i),), sources[target.node.path].locate(batch)), key=batch,
                             attrs={'batch': batch}, proof_kind=PK.JOINED)
                    incoming_reviews.add(target.node.id)
    return incoming_reviews


def _catalog_edges(rel: _Relations) -> None:
    catalog = rel.corpus.get('schemas/catalog-v1.json')
    if not catalog:
        return
    for entry in rel.corpus.catalog_entries():
        subject = f'schema:{entry["id"]}'
        validator = entry.get('validator')
        if validator in rel.sources:
            assert validator is not None  # sources holds only str paths.
            dest = rel.resolve(catalog, '../' + validator)
            if dest:
                rel.edge('constrained_by', subject, dest.node.id, whole(catalog), attrs={'via': 'catalog-v1.json'}, cls=EC.CONTRACT)
        for projection in entry.get('generated_projections', []):
            targets = [r for r in rel.by_path.get(projection, ()) if r.node.type in ('generated-projection', 'schema-projection')]
            for target in targets:
                rel.edge('constrained_by', target.node.id, subject, whole(catalog), attrs={'via': 'catalog-v1.json'}, cls=EC.CONTRACT)
            if not targets:
                rel.unknown(subject, 'extract.schema-projection-unresolved', f'{entry["id"]} declares generated_projections {projection}, which has no node yet', whole(catalog), 'Build the declared projection or correct its catalog entry', absence=True)


def _declared_schema_edges(rel: _Relations) -> None:
    """A standalone schema's declared validator and writer-proved projections."""
    declared = {(schema_id, projection): proof for schema_id, projection, proof in rel.corpus.projections}
    for source in rel.corpus.schema_sources:
        declaration = rel.corpus.parsed(source)
        if not isinstance(declaration, dict):
            continue
        subject = 'schema:' + PurePosixPath(source.path).name.removesuffix('.schema.json')
        if subject not in rel.by_id:
            continue
        validator = declaration.get('x-fleet-validator')
        if validator:
            if validator in rel.sources:
                target = rel.index.resolve(NodeRef(validator, None, WHOLE_DOCUMENT))
                rel.edge('constrained_by', subject, target.id, whole(source), attrs={'via': 'schema-declaration'})
            else:
                rel.unknown(subject, 'extract.schema-validator-unresolved', f'{source.path} declares missing validator {validator}', whole(source), 'Restore the declared validator or correct the schema declaration', absence=True)
        for projection in declaration.get('x-fleet-generated-projections', []):
            if (subject, projection) in declared:
                rel.edge('constrained_by', 'schema-projection:' + projection, subject, declared[subject, projection],
                         attrs={'via': 'schema-declaration-and-writer'}, cls=EC.CONTRACT, proof_kind=PK.JOINED)
            else:
                rel.unknown(subject, 'extract.schema-projection-unproved', f'{source.path} declares {projection} without a resolved writer mapping', whole(source), 'Bind the declared output to the actual writer mapping', absence=True)


def _generated_edges(rel: _Relations) -> None:
    for projection, canonical, proof in rel.corpus.generated:
        generated = 'generated-projection:' + projection
        if generated not in rel.by_id:
            continue
        source = rel.sources[canonical]
        target = rel.index.resolve(NodeRef(canonical, None, WHOLE_DOCUMENT))
        rel.edge('generated_from', generated, target.id, spans(proof, whole(source)),
                 attrs={'via': 'generate_platform_adapters.expected_outputs'}, cls=EC.CONTRACT, proof_kind=PK.JOINED)


def _roster_edges(rel: _Relations) -> None:
    """Validated delegation, the roster's lanes and delegation claims, and guard wiring."""
    corpus, by_id = rel.corpus, rel.by_id
    validator = corpus.get('scripts/validate_fleet.py')
    expected, expected_proof = assignment(validator, 'EXPECTED_DELEGATION') if validator else (None, ())
    roster = corpus.get('AGENTS.md')
    rows = {plain(cells[0]): (roster.span(i, i), cells) for i, cells in roster_rows(roster)} if roster else {}
    if isinstance(expected, dict):
        for agent, targets in sorted(expected.items()):
            subject = f'agent:{agent}'
            if subject not in by_id:
                continue
            granted = set(cast('tuple[str, ...]', by_id[subject].attributes['grants']))
            if granted != set(targets):
                rel.unknown(subject, 'cite.delegation-mismatch', f'agents/{agent}.md grants {sorted(granted)} but EXPECTED_DELEGATION says {sorted(targets)}', spans(expected_proof, by_id[subject].spans), 'Reconcile the agent frontmatter and validated delegation contract')
            else:
                for target in sorted(targets):
                    rel.edge('delegates_to', subject, f'agent:{target}', spans(expected_proof, by_id[subject].spans), cls=EC.CONTRACT, proof_kind=PK.JOINED)
            if agent in rows:
                row, cells = rows[agent]
                stated = set(re.findall(r'`([a-z0-9-]+)`', cells[-1]))
                if stated != set(targets):
                    rel.edge('contradicts', subject, 'document:AGENTS.md', spans(expected_proof, (row,)), key='delegation_mismatch',
                             attrs={'detector': 'delegation_mismatch', 'message': f'roster says {agent} delegates to {sorted(stated)}; validate_fleet enforces {sorted(targets)}'}, cls=EC.INFERRED)
    for agent, (row, cells) in rows.items():
        rel.edge('owns', f'agent:{agent}', 'capability:' + slug(plain(cells[1]))[:60], (row,), attrs={'via': 'roster-lane'}, cls=EC.INFERRED)
    generator = corpus.get('scripts/generate_platform_adapters.py')
    guarded, guarded_proof = assignment(generator, 'GUARDED_AGENTS') if generator else (None, ())
    hook = corpus.get('hooks/hooks.json')
    if hook and 'hook:readonly-guard' in by_id and isinstance(guarded, (set, tuple, list)):
        for agent in sorted(guarded):
            roster_proof = (rows[agent][0],) if agent in rows else ()
            rel.edge('constrained_by', f'agent:{agent}', 'hook:readonly-guard', spans(guarded_proof, whole(hook), roster_proof),
                     attrs={'via': 'generate_platform_adapters.GUARDED_AGENTS'}, cls=EC.CONTRACT, proof_kind=PK.JOINED)


def _stale_evidence(rel: _Relations) -> None:
    """Staleness is advisory for every dated live status, never an artifact-check failure."""
    for record in rel.records:
        if record.node.type == 'roadmap-item' and record.state == 'live':
            date = DATE.search(str(record.attributes.get('status_text', '')))
            evidence = [rel.by_id[cast('str', f.object)] for f in rel.facts.values() if f.subject == record.node.id and f.predicate == 'evidenced_by']
            dated = [r for r in evidence if r.attributes.get('date')]
            newest = max((cast('str', r.attributes['date']) for r in dated), default='')
            if date and newest and newest < date.group():
                rel.unknown(record.node.id, 'stale.evidence-predates-status', f'{record.name} status is dated {date.group()} but its newest cited evidence is {newest}', spans(record.spans, *(r.spans for r in dated)), 'Cite the evidence behind the current status or revise the status')


def _uncited_reviews(rel: _Relations, incoming_reviews: set[str]) -> None:
    """Reviews no roadmap item, decision, review, live guide or closed entry cites."""
    for source in rel.corpus.sources:
        if source.path in LIVE_DOCS or PurePosixPath(source.path).name in ('README.md', 'CHANGELOG.md') or source.path == 'docs/roadmap-closed.md':
            for raw in link_targets(source.text):
                target = rel.resolve(source, raw, types={'review'})
                if target and target.node.type == 'review':
                    incoming_reviews.add(target.node.id)
    incoming_reviews.update(cast('str', f.object) for f in rel.facts.values() if f.predicate in ('cites', 'evidenced_by'))
    for record in rel.records:
        if record.node.type == 'review' and record.node.id not in incoming_reviews:
            rel.unknown(record.node.id, 'stale.review-uncited', f'{record.node.path} is cited by no roadmap item, decision, review, or live guide', record.spans,
                        'Remove unneeded review evidence or restore its authoritative citation', absence=True)


def _retired_names(rel: _Relations) -> None:
    """The first line of each scanned component that names a retired fleet unit."""
    corpus = rel.corpus
    stale_source = corpus.get('scripts/check_stale_names.py')
    if stale_source is None:
        return
    retired, retired_proof = assignment(stale_source, 'STALE')
    if not isinstance(retired, tuple):
        return
    scanned = ('agents/', 'skills/', 'commands/', 'evals/scenarios/')
    exempt = {PurePosixPath(s.path).stem for s in corpus.sources if s.path.startswith(scanned)} & set(retired)
    siblings, _ = assignment(stale_source, 'SIBLING_REPOSITORIES')
    if isinstance(siblings, (set, frozenset, tuple)):
        exempt.update(siblings)
    # Older declarations wrap the literal in frozenset; recover that closed
    # literal constructor without importing the inspected checker.
    for declaration in _ast(stale_source).body:
        if (isinstance(declaration, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SIBLING_REPOSITORIES' for t in declaration.targets)
                and isinstance(declaration.value, ast.Call) and isinstance(declaration.value.func, ast.Name)
                and declaration.value.func.id == 'frozenset' and len(declaration.value.args) == 1):
            exempt.update(ast.literal_eval(declaration.value.args[0]))
    retired_name: re.Pattern[str] | None = None  # Compiled at first use, where the declaration was always read.
    for record in rel.records:
        if not record.node.path.startswith(scanned):
            continue
        source = rel.sources[record.node.path]
        for i, line in enumerate(source.lines, 1):
            found: str | None = None
            retired_name = retired_name or re.compile(
                r'(?<![a-z0-9-])(' + '|'.join(re.escape(name) for name in retired) + r')(?![a-z0-9-])')
            for match in retired_name.finditer(line):
                before = line[match.start() - 1] if match.start() else ''
                after = line[match.end():]
                if match.group(1) in exempt and (before == '/' or after.startswith(('/', '.md'))):
                    continue
                found = match.group(1)
                break
            if found:
                rel.unknown(record.node.id, 'stale.retired-name', f'{source.path}:{i}: stale fleet-unit name {found!r}', spans((source.span(i, i),), retired_proof), 'Resolve the stale fleet name or document its valid path exemption')
                break


def _blocks_emission(rel: _Relations) -> None:
    """The extractor emits no blocks edge; queries derive blocks by reversing depends_on."""
    implementation = rel.corpus.get('scripts/fleet_atlas_v2_extract.py')
    implementation_id = 'validator:scripts/fleet_atlas_v2_extract.py'
    if implementation and implementation_id in rel.by_id:
        rel.add(Fact(stable_id('fact', implementation_id, 'attr.blocks_emission'), implementation_id, 'attr.blocks_emission',
                     'no direct blocks edge; query reverses depends_on', EC.EXTRACTED,
                     Proof(PK.ABSENCE, whole(implementation), EVALUATOR, rel.corpus.snapshot.tree_digest)))


def _relations(corpus: Corpus, records: tuple[Record, ...]) -> tuple[Fact, ...]:
    rel = _Relations(corpus, records)
    for record in records:
        source = rel.sources.get(record.node.path)
        if source is None:
            continue
        for emit in RECORD_EMITTERS.get(record.node.type, ()):
            emit(rel, record, source)
    _roadmap_edges(rel)
    incoming_reviews = _evidence_edges(rel)
    _catalog_edges(rel)
    _declared_schema_edges(rel)
    _generated_edges(rel)
    _roster_edges(rel)
    # Both advisory passes read the relationships emitted above, so they run after them.
    _stale_evidence(rel)
    _uncited_reviews(rel, incoming_reviews)
    _retired_names(rel)
    _blocks_emission(rel)
    return tuple(rel.facts[key] for key in sorted(rel.facts))


def _guidance(corpus: Corpus, records: tuple[Record, ...]) -> tuple[Fact, ...]:
    """Complete body paragraphs, split by encoded size without dropping long lines."""
    output: list[Fact] = []
    for record in records:
        if (record.node.selector != WHOLE_DOCUMENT or record.authority not in ('canonical', 'live-contract')
                or record.state != 'live' or not record.node.path.endswith('.md')
                or record.node.type not in ('agent', 'skill', 'reference', 'command', 'document')):
            continue
        source = corpus.snapshot.source(record.node.path)
        start = 0
        if source.lines and source.lines[0] == '---':
            start = next((i + 1 for i, line in enumerate(source.lines[1:], 1) if line == '---'), 0)
        for paragraph, heading, heading_line in _paragraphs(source.lines[start:], start + 1):
            text = '\n'.join(line for _, line in paragraph)
            proof: tuple[Span, ...] = (source.span(paragraph[0][0], paragraph[-1][0]),)
            if heading_line:
                proof = spans(proof, (source.span(heading_line, heading_line),))
            offset = 0
            while offset < len(text):
                chunk = text[offset:].encode('utf-8')[:2400].decode('utf-8', errors='ignore')
                end = offset + len(chunk)
                output.append(Fact(stable_id('guidance', record.node.id, str(paragraph[0][0]), str(offset)),
                    record.node.id, 'guidance', chunk, EC.EXTRACTED, Proof(PK.EXTRACTED, proof, EVALUATOR),
                    pairs({'heading': heading, 'start_offset': offset, 'end_offset': end})))
                offset = end
    return tuple(output)


def _paragraphs(lines: Sequence[str], first_line: int) -> Iterator[tuple[list[tuple[int, str]], str, int | None]]:
    """Yield (numbered lines, heading, heading line) for each run of non-blank lines.

    A heading line closes the paragraph before it, which keeps the earlier heading, and opens
    its own paragraph under the new one.
    """
    paragraph: list[tuple[int, str]] = []
    heading, heading_line = '', None
    for i, line in enumerate(lines, first_line):
        if line.startswith('#'):
            if paragraph:
                yield paragraph, heading, heading_line
                paragraph = []
            heading, heading_line = line.lstrip('#').strip(), i
        if line.strip():
            paragraph.append((i, line))
        elif paragraph:
            yield paragraph, heading, heading_line
            paragraph = []
    if paragraph:
        yield paragraph, heading, heading_line


# Record fields whose value the extractor derives rather than quotes: a count, list,
# flag, filename-derived identity, or the donor's bounded display value of a longer field.
COMPUTED_FIELDS = frozenset(('authority', 'attr.bytes', 'attr.fields', 'attr.batches', 'attr.batch', 'attr.banner',
                             'attr.linked_from_roadmap', 'attr.kind', 'attr.skill', 'attr.file',
                             'attr.status_text', 'attr.owner', 'attr.disposition'))
# Record fields mapped onto a closed vocabulary or normalised text.
NORMALIZED_FIELDS = frozenset(('state', 'attr.manual_only', 'attr.grants', 'attr.description'))


def _field_proof_kind(record: Record, predicate: str) -> PK:
    if record.evidence_class == EC.INFERRED:
        return PK.INFERRED
    if predicate in COMPUTED_FIELDS or (predicate == 'name' and record.node.type != 'scenario'):
        return PK.COMPUTED  # A scenario's name is its quoted id; others are filenames, identities or rows.
    if predicate in NORMALIZED_FIELDS or (predicate == 'attr.status' and record.node.type == 'roadmap-item'):
        return PK.NORMALIZED
    return record.proof_kind


def _record_facts(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    records = inputs['catalog'].records
    buckets: dict[str, tuple[list[Node], list[Fact]]] = {}
    for record in records:
        nodes, facts = buckets.setdefault(record.family, ([], []))
        nodes.append(record.node)
        fields = (('name', record.name), ('authority', record.authority), ('state', record.state), *(('attr.' + key, value) for key, value in record.attrs))
        for predicate, value in fields:
            facts.append(Fact(stable_id('fact', record.node.id, predicate), record.node.id, predicate, value,
                record.evidence_class, Proof(_field_proof_kind(record, predicate), record.spans, EVALUATOR)))
    return StageOutput(buckets=tuple(Bucket(name, tuple(sorted(nodes)), tuple(sorted(facts, key=lambda f: f.id)))
                 for name, (nodes, facts) in sorted(buckets.items())))


def _relationship_facts(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    return StageOutput(buckets=(Bucket('relationships', (), _relations(corpus, inputs['catalog'].records)),))


def _guidance_facts(corpus: Corpus, inputs: Mapping[str, StageOutput]) -> StageOutput:
    facts = _guidance(corpus, inputs['catalog'].records)
    return StageOutput(buckets=(Bucket('guidance', (), tuple(sorted(facts, key=lambda fact: fact.id))),))


# Dependency names are the complete input contract for each producer. Source-only
# declarations are independent; resolution explicitly waits for every declaration
# family. No producer is passed the mutable scheduler state or an assembled graph.
EXTRACTION_STAGES = (
    ExtractionStage('components', (), _component_records),
    ExtractionStage('roadmap', ('components',), _roadmap_records),
    ExtractionStage('rules', (), _rule_records),
    ExtractionStage('schemas', (), _schema_records),
    ExtractionStage('roster', ('components',), _roster_records),
    ExtractionStage('contracts', (), _contract_records),
    ExtractionStage('catalog', ('components', 'roadmap', 'rules', 'schemas', 'roster', 'contracts'), _resolve_catalog),
    ExtractionStage('record-facts', ('catalog',), _record_facts),
    ExtractionStage('relationships', ('catalog',), _relationship_facts),
    ExtractionStage('guidance', ('catalog',), _guidance_facts),
)


def _derive(snapshot: Snapshot, stages: Iterable[ExtractionStage] = EXTRACTION_STAGES) -> tuple[Bucket, ...]:
    registered: dict[str, ExtractionStage] = {}
    for stage in stages:
        if stage.name in registered:
            raise ValueError(f'duplicate extraction stage: {stage.name}')
        registered[stage.name] = stage
    for stage in registered.values():
        missing = set(stage.requires) - registered.keys()
        if missing:
            raise ValueError(f'missing extraction prerequisites for {stage.name}: {sorted(missing)}')
    # Validate the complete dependency plan before invoking any producer.
    available: set[str] = set()
    pending, plan = dict(registered), []
    while pending:
        ready = sorted(name for name, stage in pending.items() if set(stage.requires) <= available)
        if not ready:
            raise ValueError(f'extraction dependency cycle: {sorted(pending)}')
        for name in ready:
            plan.append(pending.pop(name))
            available.add(name)
    # A fresh corpus per derivation: replay never sees the primary extraction's views.
    corpus = Corpus(snapshot)
    completed: dict[str, StageOutput] = {}
    for stage in plan:
        inputs = MappingProxyType({name: completed[name] for name in stage.requires})
        output = stage.produce(corpus, inputs)
        if not isinstance(output, StageOutput):
            raise TypeError(f'extraction stage {stage.name} did not return frozen StageOutput')
        completed[stage.name] = output
    return tuple(sorted((bucket for output in completed.values() for bucket in output.buckets),
                        key=lambda bucket: bucket.extractor))


@lru_cache(maxsize=2)
def _replayed(snapshot: Snapshot) -> Mapping[str, Fact]:
    # Separate source reconstruction, not a cache populated by submitted candidate facts.
    return MappingProxyType({f.id: f for bucket in _derive(snapshot) for f in bucket.facts})


def replay(fact: Fact, snapshot: Snapshot, _verified_premises: Mapping[str, Fact]) -> Derivation:
    expected = _replayed(snapshot).get(fact.id)
    if expected is None or (expected.subject, expected.predicate) != (fact.subject, fact.predicate):
        raise ValueError(f'claim not produced by its source authority: {fact.id}')
    return Derivation(expected.object, expected.evidence_class, expected.proof, expected.qualifiers)


def extract(snapshot: Snapshot, *, stages: Iterable[ExtractionStage] = EXTRACTION_STAGES) -> Extraction:
    buckets = _derive(snapshot, stages)
    fields = {f.predicate for b in buckets for f in b.facts} - EDGE_TYPES
    # All source spans are replayed; joined proofs may include canonical targets and
    # controlling validators in addition to their declaration source.
    authority = ('*.md', '*.py', '*.json', '*.csv', '*.yaml', '*.yml', '*.toml', '*.txt', '*.sh', '*.ps1', '*.js', '*.ts', '*.html', '*.css', '*.svg', '*.ini', '*.cfg')
    predicates = tuple(Predicate(name, frozenset(source), frozenset(target), authority)
                       for name, (source, target) in sorted(EDGE_ENDPOINTS.items()))
    predicates += tuple(Predicate(name, NODE_TYPES, None, authority, None if name in ('unknown', 'guidance') else 1)
                        for name in sorted(fields))
    return Extraction(buckets, predicates, MappingProxyType({EVALUATOR: replay}))
