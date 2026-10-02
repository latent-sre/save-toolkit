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
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import PurePosixPath as Path
from types import MappingProxyType
from typing import Callable, Mapping
from urllib.parse import unquote, urlsplit

import fleet_frontmatter
from fleet_atlas_v2_model import (Bucket, EvidenceClass as EC, Fact, Node, NodeIndex,
    NodeRef, Predicate, Proof, ProofKind as PK, Span, Value, WHOLE_DOCUMENT)
from fleet_atlas_v2_proofs import Derivation, Evaluator
from fleet_atlas_v2_sources import Snapshot, Source

NODE_TYPES = frozenset(('agent', 'skill', 'reference', 'bundle-file', 'command', 'rule',
    'decision', 'roadmap-item', 'review', 'scenario', 'test', 'schema', 'schema-projection',
    'generated-projection', 'capability', 'owner', 'probe', 'hook', 'document', 'validator'))
EDGE_TYPES = frozenset(('owns', 'routes_to', 'delegates_to', 'loads_when', 'governed_by',
    'constrained_by', 'verified_by', 'evidenced_by', 'depends_on', 'blocks', 'supersedes',
    'generated_from', 'near_miss_for', 'contradicts', 'cites'))
LIVE_DOCS = frozenset(('AGENTS.md', 'CONTRIBUTING.md', 'README.md', 'docs/README.md',
    'docs/rules.md', 'docs/schema-compatibility.md', 'docs/fleet-roadmap.md'))
ITEM = re.compile(r'\b[A-Z][A-Z0-9]*-\d{3}\b')
BATCH = re.compile(r'\b\d{8}T\d{6}Z-[0-9a-f]{8}\b')
DATE = re.compile(r'\b20\d\d-\d\d-\d\d\b')
LINK = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')
TARGET_LINK = re.compile(r'\]\(([^)]+)\)')
FIELD = re.compile(r'^\*\*([A-Za-z][A-Za-z ]+):\*\*\s*(.*)$')
EVALUATOR = 'fleet-source-replay/v2'


@dataclass(frozen=True)
class Extraction:
    buckets: tuple[Bucket, ...]
    predicates: tuple[Predicate, ...]
    evaluators: Mapping[str, Evaluator]


@dataclass(frozen=True)
class Record:
    node: Node
    name: str
    authority: str
    state: str
    attrs: tuple[tuple[str, Value], ...]
    spans: tuple[Span, ...]
    family: str
    proof_kind: PK = PK.EXTRACTED
    evidence_class: EC = EC.EXTRACTED


@dataclass(frozen=True)
class StageOutput:
    """A producer returns immutable data, never a graph or shared record builder."""
    records: tuple[Record, ...] = ()
    buckets: tuple[Bucket, ...] = ()

    def __post_init__(self):
        if not isinstance(self.records, tuple) or not all(isinstance(r, Record) for r in self.records):
            raise TypeError('stage records must be a tuple of Record values')
        if not isinstance(self.buckets, tuple) or not all(isinstance(b, Bucket) for b in self.buckets):
            raise TypeError('stage buckets must be a tuple of Bucket values')


@dataclass(frozen=True)
class ExtractionStage:
    name: str
    requires: tuple[str, ...]
    produce: Callable[[Snapshot, Mapping[str, StageOutput]], StageOutput]

    def __post_init__(self):
        if (not isinstance(self.requires, tuple) or len(set(self.requires)) != len(self.requires)
                or not all(isinstance(name, str) for name in self.requires)):
            raise TypeError('stage prerequisites must be unique immutable names')


def stable_id(prefix: str, *parts: str) -> str:
    return prefix + ':' + hashlib.sha256('\x1f'.join(parts).encode()).hexdigest()[:16]


def freeze(value) -> Value:
    if isinstance(value, dict):
        return tuple((str(k), freeze(v)) for k, v in sorted(value.items()))
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(freeze(v) for v in (sorted(value) if isinstance(value, (set, frozenset)) else value))
    if value is None or type(value) in (str, int, float, bool):
        return value
    return str(value)  # YAML dates retain their textual value, never a mutable object.


def plain(text: str) -> str:
    return ' '.join(LINK.sub(r'\1', text).replace('`', '').replace('**', '').split())


def link_targets(text):
    # The destination remains parseable on the closing line of a wrapped or
    # nested-label link. Labels do not determine a repository target identity.
    return tuple(('', target) for target in TARGET_LINK.findall(text))


def slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def anchor(text: str) -> str:
    return re.sub(r'[^\w\- ]', '', plain(text).lower()).replace(' ', '-')


def spans(*values) -> tuple[Span, ...]:
    return tuple(sorted(set(item for group in values for item in group)))


def whole(source: Source) -> tuple[Span, ...]:
    if not source.lines:
        raise ValueError(f'cannot invent a line citation for empty source: {source.path}')
    return (source.span(1, len(source.lines)),)


# Block scalars may have tag/anchor properties and trailing header comments.
# Missing these forms lets prompt text fabricate scenario identity or routing.
NODE_PROPERTY = r'(?:&[^\s,\[\]{}]+|!<[^>]*>|![^\s,\[\]{}]*)'
YAML_PROPERTIES = r'(?:' + NODE_PROPERTY + r'[ \t]+)*'
PROPERTY_PREFIX = re.compile(YAML_PROPERTIES)
PROPERTY_TOKEN = re.compile(NODE_PROPERTY + r'(?=\s|$)')
BLOCK_SCALAR = re.compile(r'^' + YAML_PROPERTIES +
                          r'[|>](?:[1-9][+-]?|[+-][1-9]?)?(?:[ \t]+#.*)?$')


def _scalar_start(lines, index, indent, value):
    """An empty value or properties can precede a scalar on a later line."""
    while True:
        text = value + ' '
        value = text[PROPERTY_PREFIX.match(text).end():].strip()
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


def _flow_scalar(lines, index, value):
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


def yaml_fields(source: Source, frontmatter=False):
    if frontmatter:
        parsed = fleet_frontmatter.parse(source.text, source.path, mode='lenient')
        return parsed.fields, (source.span(1, len(parsed.raw_lines) + 2),)
    # Deliberately the donor's scalar identity/routing subset, not executable YAML.
    # Prompt block scalars and fixtures cannot contribute top-level target identity.
    result, stack, block_indent = {}, [], None
    stack.append((-1, result))
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


def _scenario_scalar(value):
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


def records_for_roadmap(source: Source):
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
        result.append((item_id, start + 1, end, fields,
                       {k: (source.span(min(v), max(v)),) for k, v in positions.items()}))
    # The modern parked register is still live backlog, with its own row selector.
    for i, line in enumerate(source.lines, 1):
        cells = line.strip().strip('|').split('|')
        if len(cells) >= 2 and re.fullmatch(r'[A-Z][A-Z0-9]*-\d{3}', plain(cells[0])):
            item_id = plain(cells[0])
            if item_id not in {r[0] for r in result}:
                result.append((item_id, i, i, {'Status': 'deferred', 'Next action': cells[1].strip()},
                               {'Status': (source.span(i, i),), 'Next action': (source.span(i, i),)}))
    return tuple(result)


def status_marker(text: str) -> str:
    normalized = text.strip().strip('`*_ .').lower()
    return re.split(r'\s*(?:,|;|\(|—|–|\s-\s)\s*', normalized, maxsplit=1)[0].strip().strip('`*_ .')


def _ast(source: Source) -> ast.Module:
    return ast.parse(source.text, filename=source.path)


def assignment(source: Source, name: str):
    for node in _ast(source).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            try:
                return ast.literal_eval(node.value), (source.span(node.lineno, node.end_lineno),)
            except (ValueError, TypeError):
                return None, ()
    return None, ()


def resolved_link(source: Source, raw: str, paths: set[str]):
    split = urlsplit(raw.strip().strip('<>'))
    if split.scheme or split.netloc:
        return None
    path = unquote(split.path)
    target = posixpath.normpath(posixpath.join(posixpath.dirname(source.path), path)) if path else source.path
    if target.startswith('../') or target not in paths:
        return None
    return target, unquote(split.fragment)


def _record(node_id, node_type, name, path, evidence, *, authority='canonical', state='live',
            attrs=None, family='documents', selector=WHOLE_DOCUMENT, kind=PK.EXTRACTED, cls=EC.EXTRACTED):
    return Record(Node(node_id, node_type, path, selector), name, authority, state,
                  freeze(attrs or {}), evidence, family, kind, cls)


def _record_builder(inputs):
    """Private construction state; only frozen records cross a stage boundary."""
    records = {}
    def add(record):
        if record.node.id in records and records[record.node.id] != record:
            raise ValueError(f'conflicting source declarations: {record.node.id}')
        records[record.node.id] = record
    for output in inputs.values():
        for record in output.records:
            add(record)
    return records, add


def _new_records(records, inputs):
    inherited = {record.node.id for output in inputs.values() for record in output.records}
    return StageOutput(tuple(records[key] for key in sorted(records) if key not in inherited))


def _component_records(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    for source in snapshot.sources:
        path, p = source.path, Path(source.path)
        if path.startswith(('agents/', 'commands/')) and len(p.parts) == 2 and p.suffix == '.md':
            kind = 'agent' if path.startswith('agents/') else 'command'
            data, proof = yaml_fields(source, True)
            attrs = {'description': str(data.get('description', '')).strip()}
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
                data, proof = yaml_fields(source, True)
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
            state = {'accepted': 'live', 'proposed': 'proposed', 'superseded': 'historical', 'rejected': 'rejected', 'deprecated': 'deprecated'}.get(word, 'historical')
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
            data, _ = yaml_fields(source)
            if 'id' not in data:
                continue
            routing = data.get('routing') or {}
            alt = routing.get('expected_alternative')
            alt = alt if isinstance(alt, str) else f'{alt.get("kind")}:{alt.get("name")}' if isinstance(alt, dict) else ''
            add(_record(f'scenario:{data["id"]}', 'scenario', str(data['id']), path,
                yaml_key_spans(source, ('id', 'mode', 'split', 'routing', 'threshold', 'agent', 'target', 'skill')),
                authority='live-contract', attrs={'mode': data.get('mode', ''), 'split': data.get('split', ''), 'expect': routing.get('expect', ''), 'threshold': data.get('threshold'), 'expected_alternative': alt, 'file': path}, family='scenarios'))
        elif path.startswith(('scripts/', 'evals/')) and len(p.parts) == 2 and p.name.startswith('test_') and p.suffix == '.py':
            add(_record(f'test:{path}', 'test', path, path, whole(source), family='tests'))
        elif path.startswith('docs/probes/') and len(p.parts) == 3:
            roadmap = sources.get('docs/fleet-roadmap.md')
            links = tuple(roadmap.span(i, i) for i, line in enumerate(roadmap.lines, 1) if any(
                (resolved_link(roadmap, raw, set(sources)) or (None,))[0] == path for _, raw in link_targets(line))) if roadmap else ()
            add(_record(f'probe:{p.stem}', 'probe', p.stem, path, spans(whole(source), links or (whole(roadmap) if roadmap else ())),
                authority='live-contract' if links else 'historical-evidence', state='live' if links else 'historical',
                attrs={'linked_from_roadmap': bool(links)}, family='probes', kind=PK.JOINED))
    return _new_records(records, inputs)


def _roadmap_records(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    roadmap = sources.get('docs/fleet-roadmap.md')
    if roadmap:
        for item, start, end, fields, positions in records_for_roadmap(roadmap):
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
            prefix = owner.split('`', 1)[0].strip()
            human = re.split(r'\s+owns?\b', prefix, maxsplit=1, flags=re.I)[0].strip(' .,:;')
            if human:
                key = f'owner:{slug(human)}'
                if key not in records:
                    add(_record(key, 'owner', human, roadmap.path, proof, authority='external', attrs={'kind': 'human'}, family='owners', selector=key))
    closed = sources.get('docs/roadmap-closed.md')
    if closed:
        for i, line in enumerate(closed.lines, 1):
            cells = line.strip().strip('|').split('|')
            if len(cells) < 3 or not line.startswith('| `'):
                continue
            for item in ITEM.findall(cells[0]):
                if f'roadmap-item:{item}' not in records:
                    add(_record(f'roadmap-item:{item}', 'roadmap-item', item, closed.path, (closed.span(i, i),),
                        authority='historical-evidence', state='historical', attrs={'closed': cells[1].strip(), 'disposition': plain(cells[2])[:200]}, family='roadmap', selector=item))
    return _new_records(records, inputs)


def _rule_records(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    rules = sources.get('docs/rules.md')
    if rules:
        section, section_line = '', None
        for i, line in enumerate(rules.lines, 1):
            if line.startswith('## '):
                section, section_line = line[3:].strip(), i
            if not _table_data(rules.lines, i):
                continue
            cells = line.strip().strip('|').split('|')
            if len(cells) < 2:
                continue
            statement = plain(cells[0]); key = stable_id('rule', rules.path, statement)
            proof = (rules.span(i, i),) + ((rules.span(section_line, section_line),) if section_line else ())
            add(_record(key, 'rule', statement[:80], rules.path, spans(proof), authority='live-contract', attrs={'section': section, 'statement': statement, 'source_text': plain(cells[1])}, family='rules', selector=key))
    return _new_records(records, inputs)


def _schema_records(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    catalog = sources.get('schemas/catalog-v1.json')
    if catalog:
        data = json.loads(catalog.text)
        for entry in data.get('schemas', []):
            proof = whole(catalog)  # All catalog fields determine identity/path/state/relations.
            path = entry['canonical_path']
            add(_record(f'schema:{entry["id"]}', 'schema', entry['id'], path, proof, authority='live-contract', attrs={'status': entry['status'], 'version': entry['version']}, family='schemas', selector=f'schema:{entry["id"]}', cls=EC.CONTRACT))
            for projection in entry.get('generated_projections', []):
                if projection.startswith('docs/fleet-atlas/'):
                    add(_record(f'schema-projection:{projection}', 'schema-projection', projection, projection, proof,
                        authority='generated', state='generated', attrs={'schema': entry['id']}, family='schemas'))
    catalog_paths = {r.node.path for r in records.values() if r.node.type == 'schema'}
    for source in snapshot.sources:
        if (not source.path.startswith('schemas/') or not source.path.endswith('.schema.json')
                or source.path in catalog_paths):
            continue
        declaration = json.loads(source.text)
        if not isinstance(declaration, dict):
            continue
        name = Path(source.path).name.removesuffix('.schema.json')
        attrs = {target: declaration[key] for key, target in
                 (('$id', 'schema_uri'), ('$schema', 'dialect'), ('title', 'title'), ('type', 'type'))
                 if key in declaration}
        add(_record(f'schema:{name}', 'schema', name, source.path, whole(source),
                    authority='live-contract', attrs=attrs, family='schemas'))
    for schema_id, projection, proof in standalone_projections(snapshot):
        add(_record(f'schema-projection:{projection}', 'schema-projection', projection, projection, proof,
                    authority='generated', state='generated', attrs={'schema': schema_id.removeprefix('schema:')},
                    family='schemas', cls=EC.CONTRACT, kind=PK.JOINED))
    return _new_records(records, inputs)


def _roster_records(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    roster = sources.get('AGENTS.md')
    if roster:
        for i, cells in roster_rows(roster):
            name = plain(cells[0])
            if f'agent:{name}' not in records:
                continue
            lane = plain(cells[1]); key = 'capability:' + slug(lane)[:60]
            if key not in records:
                add(_record(key, 'capability', lane, roster.path, (roster.span(i, i),), attrs={'lane': lane},
                    selector=key, family='owners', kind=PK.INFERRED, cls=EC.INFERRED))
    return _new_records(records, inputs)


def _contract_records(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    hook = sources.get('hooks/hooks.json')
    if hook and 'readonly-guard.py' in hook.text:
        add(_record('hook:readonly-guard', 'hook', 'readonly-guard', hook.path, whole(hook), authority='live-contract', attrs={'matcher': 'Bash'}, selector='hook:readonly-guard', family='contracts', cls=EC.CONTRACT))
    for projection, canonical, proof in generated_mappings(snapshot):
        if projection in sources:
            add(_record('generated-projection:' + projection, 'generated-projection', projection, projection,
                spans(proof, whole(sources[projection]), whole(sources[canonical])), authority='generated', state='generated',
                attrs={'bytes': len(sources[projection].content)}, family='generated', cls=EC.CONTRACT, kind=PK.JOINED))
    return _new_records(records, inputs)


def _resolve_catalog(snapshot, inputs):
    sources = {s.path: s for s in snapshot.sources}
    records, add = _record_builder(inputs)
    catalog = sources.get('schemas/catalog-v1.json')
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
    paths = set(sources)
    needed = {p for p in paths if p in LIVE_DOCS or (Path(p).name in ('README.md', 'CHANGELOG.md') and not p.startswith('docs/reviews/'))}
    needed.update(r.node.path for r in records.values())
    needed.update(canonical for _, canonical, _ in generated_mappings(snapshot))
    if 'scripts/fleet_atlas_v2_extract.py' in sources:
        needed.add('scripts/fleet_atlas_v2_extract.py')
    for source in snapshot.sources:
        if source.path.endswith('.md'):
            needed.update(hit[0] for _, raw in link_targets(source.text) if (hit := resolved_link(source, raw, paths)))
    if catalog:
        needed.update(e['validator'] for e in json.loads(catalog.text).get('schemas', []) if e.get('validator') in sources)
    for source in snapshot.sources:
        if source.path.startswith('schemas/') and source.path.endswith('.schema.json'):
            declaration = json.loads(source.text)
            if isinstance(declaration, dict) and declaration.get('x-fleet-validator') in sources:
                needed.add(declaration['x-fleet-validator'])
    for path in sorted(needed):
        if path not in sources or not sources[path].content:
            continue
        whole_records = [r for r in records.values() if r.node.path == path and r.node.selector == WHOLE_DOCUMENT]
        if not whole_records:
            typ = 'validator' if path.startswith('scripts/') and path.endswith('.py') else 'document'
            live_guide = path in LIVE_DOCS or (Path(path).name in ('README.md', 'CHANGELOG.md') and not path.startswith('docs/reviews/'))
            authority = 'live-contract' if live_guide else 'historical-evidence' if path.startswith('docs/') else 'canonical'
            add(_record(f'{typ}:{path}', typ, path, path, whole(sources[path]), authority=authority))
    return StageOutput(tuple(records[k] for k in sorted(records)))


def _table_data(lines, i):
    line = lines[i - 1].strip()
    return line.startswith('|') and not re.match(r'^\|\s*:?-{3,}', line) and not (i < len(lines) and re.match(r'^\|\s*:?-{3,}', lines[i].strip()))


def roster_rows(source):
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


def _path_expression(node, environment):
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
        for value in node.values:
            part = _path_expression(value.value if isinstance(value, ast.FormattedValue) else value, environment)
            if not isinstance(part, str):
                return None
            pieces.append(part)
        return ''.join(pieces)
    if isinstance(node, ast.Attribute):
        value = _path_expression(node.value, environment)
        if isinstance(value, str) and node.attr in ('stem', 'name', 'suffix'):
            return str(getattr(Path(value), node.attr))
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == 'Path' and len(node.args) == 1:
            return _path_expression(node.args[0], environment)
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'relative_to' and len(node.args) == 1:
            value, base = _path_expression(node.func.value, environment), _path_expression(node.args[0], environment)
            if isinstance(value, str) and isinstance(base, str):
                try:
                    return Path(value).relative_to(base).as_posix()
                except ValueError:
                    return None
    return None


def generated_mappings(snapshot):
    try:
        source = snapshot.source('scripts/generate_platform_adapters.py')
    except ValueError:
        return ()
    tree = _ast(source)
    constants, constant_spans = {'root': ''}, {}
    for statement in tree.body:
        targets = statement.targets if isinstance(statement, ast.Assign) else []
        for target in targets:
            if isinstance(target, ast.Name) and (value := _path_expression(statement.value, constants)) is not None:
                constants[target.id] = value
                constant_spans[target.id] = source.span(statement.lineno, statement.end_lineno)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'expected_outputs'), None)
    if function is None:
        return ()
    parent = {child: node for node in ast.walk(function) for child in ast.iter_child_nodes(node)}
    result = {}
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == 'outputs'):
                continue
            loops, cursor = [], node
            while cursor in parent:
                cursor = parent[cursor]
                if isinstance(cursor, ast.For):
                    loops.append(cursor)
            loop = next((loop for loop in loops if isinstance(loop.target, ast.Name) and loop.target.id == 'source'
                         and isinstance(loop.iter, ast.Name) and loop.iter.id in ('agents', 'commands', 'skill_files')), None)
            if loop:
                family = loop.iter.id
                inputs = [s.path for s in snapshot.sources if
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
                names = {n.id for n in ast.walk(function) if isinstance(n, ast.Name)}
                proof = spans((source.span(function.lineno + 1, function.end_lineno),),
                              tuple(constant_spans[name] for name in sorted(names & constant_spans.keys())))
                key = projection, canonical
                result[key] = spans(result.get(key, ()), proof)
    return tuple((projection, canonical, proof) for (projection, canonical), proof in sorted(result.items()))


def _writer_filenames(render, safe, build):
    """Recognize the closed mapping->return->iteration->payload->publish chain.

    This intentionally abstains on other writer shapes. Occurrences of familiar
    names, discarded calls and assignments in unrelated branches are not lineage.
    """
    def assigned(function, name):
        return [node for node in ast.walk(function) if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]

    def returns_variable(function, name):
        returns = [node for node in ast.walk(function) if isinstance(node, ast.Return)]
        return (len(returns) == 1 and function.body[-1] is returns[0]
                and isinstance(returns[0].value, ast.Name) and returns[0].value.id == name)

    def direct_call_assignment(function, name, callable_name):
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
                if any(isinstance(arg, ast.Name) and arg.id == 'files' for arg in (*node.args, *(k.value for k in node.keywords))):
                    if not (isinstance(node.func, ast.Name) and node.func.id == 'sorted'):
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
        publications = []
        for block in loop.body:
            body = block.body if isinstance(block, ast.Try) else [block]
            for statement in body:
                if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
                        and ast.unparse(statement.value.func) == 'os.replace'
                        and [ast.unparse(arg) for arg in statement.value.args] == ['temporary', 'output / name']
                        and statement.lineno > temporary_writes[0].end_lineno):
                    publications.append(statement)
        if len(publications) == 1:
            return writes
    return set()


def standalone_projections(snapshot):
    """Bind the v2 schema's explicit output declaration to its actual writer mapping.

    Merely declaring an output, mentioning its path, or having a function with the
    expected name does not establish the generated relationship.
    """
    sources = {s.path: s for s in snapshot.sources}
    implementation = sources.get('scripts/fleet_atlas_v2_artifacts.py')
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
    mapping_proof = tuple(implementation.span(n.lineno, n.end_lineno) for n in (assignments[0], render, safe, build))
    result = []
    for source in snapshot.sources:
        if not source.path.startswith('schemas/') or not source.path.endswith('.schema.json'):
            continue
        declaration = json.loads(source.text)
        if not isinstance(declaration, dict):
            continue
        validator = declaration.get('x-fleet-validator')
        if validator not in sources:
            continue
        for projection in declaration.get('x-fleet-generated-projections', []):
            if projection in {posixpath.join(output, filename) for filename in writes}:
                result.append(('schema:' + Path(source.path).name.removesuffix('.schema.json'), projection,
                               spans(whole(source), mapping_proof, whole(sources[validator]))))
    return tuple(result)


def test_file_reads(source: Source) -> tuple[tuple[str, tuple[Span, ...]], ...]:
    """Rooted read dependencies only, with binding and helper-body provenance.

    A literal, fixture write, temporary-root read or shadowed ROOT is not verification
    authority. This recognizes static paths and first-argument read helpers, not arbitrary
    Python dataflow. Unresolved dynamic paths yield no verified_by claim.
    """
    tree = _ast(source)
    path_imports = tuple(source.span(node.lineno, node.end_lineno) for node in tree.body
                         if isinstance(node, ast.ImportFrom) and node.module == 'pathlib'
                         and any(alias.name == 'Path' and alias.asname in (None, 'Path') for alias in node.names))
    bindings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings.setdefault(target.id, []).append(node)
    root_bindings = {}
    for name, declarations in bindings.items():
        if len(declarations) != 1:
            continue
        node = declarations[0]
        expression = ast.unparse(node.value)
        # Both forms explicitly derive the repository directory from this test's location.
        if path_imports and not bindings.get('Path') and re.fullmatch(r'Path\(__file__\)\.resolve\(\)\.(?:parents\[1\]|parent\.parent)', expression):
            root_bindings[name] = node
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    def scope(call):
        cursor = call
        while cursor in parents:
            cursor = parents[cursor]
            if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return cursor
        return tree
    def rooted(expression, call_scope, substitutions=None):
        substituted = substitutions or {}
        stores = [n for n in ast.walk(call_scope) if isinstance(n, ast.Name)
                  and isinstance(n.ctx, ast.Store) and scope(n) is call_scope] if call_scope is not tree else []
        shadowed = {n.id for n in stores}
        parameters = set()
        if isinstance(call_scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parameters = {a.arg for a in (*call_scope.args.posonlyargs, *call_scope.args.args, *call_scope.args.kwonlyargs)}
            shadowed.update(parameters)
        bindings_here = {name: declaration for name, declaration in root_bindings.items() if name not in shadowed}
        if call_scope is not tree and path_imports and not bindings.get('Path') and 'Path' not in shadowed:
            for declaration in ast.walk(call_scope):
                if not isinstance(declaration, ast.Assign) or scope(declaration) is not call_scope:
                    continue
                if not re.fullmatch(r'Path\(__file__\)\.resolve\(\)\.(?:parents\[1\]|parent\.parent)', ast.unparse(declaration.value)):
                    continue
                for target in declaration.targets:
                    if (isinstance(target, ast.Name) and target.id not in parameters
                            and sum(n.id == target.id for n in stores) == 1):
                        bindings_here[target.id] = declaration
        environment = {name: '' for name in bindings_here}
        environment.update(substituted)
        value = _path_expression(expression, environment)
        names = {n.id for n in ast.walk(expression) if isinstance(n, ast.Name)}
        bound_roots = (names & bindings_here.keys()) - substituted.keys()
        if value and (bound_roots or names & substituted.keys()) and not value.startswith(('/', '../')):
            proof = tuple(source.span(bindings_here[n].lineno, bindings_here[n].end_lineno) for n in sorted(bound_roots))
            return value, spans(proof, path_imports) if bound_roots else proof
        return None
    def read_expression(call):
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
    written = set()
    def write_expression(call):
        expression = None
        if isinstance(call.func, ast.Attribute) and call.func.attr in ('write_text', 'write_bytes'):
            expression = call.func.value
        elif isinstance(call.func, ast.Name) and call.func.id == 'open' and call.args and read_expression(call) is None:
            expression = call.args[0]
        elif isinstance(call.func, ast.Attribute) and call.func.attr == 'open' and read_expression(call) is None:
            expression = call.func.value
        return expression

    def parameters(function, call, caller_scope, substitutions):
        positional = (*function.args.posonlyargs, *function.args.args)
        arguments = {parameter.arg: value for parameter, value in zip(positional, call.args)}
        arguments.update({keyword.arg: keyword.value for keyword in call.keywords if keyword.arg})
        values = {}
        for name, value in arguments.items():
            hit = rooted(value, caller_scope, substitutions)
            if hit:
                values[name] = hit[0]
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                values[name] = value.value
        return values

    def helper_writes(function, substitutions, visiting):
        if function.name in visiting:
            # Recursive/mutually recursive helper effects are not proved read-only.
            return set(substitutions.values())
        effects = set()
        for call in (n for n in ast.walk(function) if isinstance(n, ast.Call)):
            expression = write_expression(call)
            if expression is not None:
                hit = rooted(expression, function, substitutions)
                effects.update((hit[0],) if hit else substitutions.values())
            elif isinstance(call.func, ast.Name) and call.func.id in functions:
                callee = functions[call.func.id]
                effects.update(helper_writes(callee, parameters(callee, call, function, substitutions), visiting | {function.name}))
        return effects

    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        expression = write_expression(call)
        if expression is not None and (hit := rooted(expression, scope(call))):
            written.add(hit[0])
        if isinstance(call.func, ast.Name) and call.func.id in functions:
            function = functions[call.func.id]
            written.update(helper_writes(function, parameters(function, call, scope(call), {}), set()))
    found = {}
    for call in (n for n in ast.walk(tree) if isinstance(n, ast.Call)):
        expression = read_expression(call)
        candidates = []
        if expression is not None:
            hit = rooted(expression, scope(call))
            if hit:
                candidates.append((hit[0], spans(hit[1], (source.span(call.lineno, call.end_lineno),))))
        elif isinstance(call.func, ast.Name) and call.func.id in functions and call.args:
            function = functions[call.func.id]
            if not function.args.args:
                continue
            parameter = function.args.args[0].arg
            arg = _path_expression(call.args[0], {})
            rooted_arg = rooted(call.args[0], scope(call))
            for helper_call in (n for n in ast.walk(function) if isinstance(n, ast.Call)):
                expr = read_expression(helper_call)
                if expr is None:
                    continue
                if rooted_arg and isinstance(expr, ast.Name) and expr.id == parameter:
                    candidates.append((rooted_arg[0], spans(rooted_arg[1], (source.span(function.lineno, function.end_lineno), source.span(call.lineno, call.end_lineno)))))
                elif isinstance(arg, str):
                    hit = rooted(expr, function, {parameter: arg})
                    # A helper parameter alone is not rooted; an actual repository ROOT must
                    # also appear in its read expression.
                    if hit and hit[1]:
                        candidates.append((hit[0], spans(hit[1], (source.span(function.lineno, function.end_lineno), source.span(call.lineno, call.end_lineno)))))
        for path, proof in candidates:
            if path not in written:
                found[path] = spans(found.get(path, ()), proof)
    return tuple(sorted(found.items()))


def _relations(snapshot, records):
    sources = {s.path: s for s in snapshot.sources}
    by_id = {r.node.id: r for r in records}
    index = NodeIndex(tuple(r.node for r in records))
    facts = {}
    def add(fact):
        previous = facts.get(fact.id)
        if previous and previous != fact:
            if (previous.subject, previous.predicate, previous.object, previous.qualifiers, previous.evidence_class, previous.proof.kind) != (fact.subject, fact.predicate, fact.object, fact.qualifiers, fact.evidence_class, fact.proof.kind):
                raise ValueError(f'conflicting extracted relationship: {fact.id}')
            fact = Fact(fact.id, fact.subject, fact.predicate, fact.object, fact.evidence_class,
                        Proof(fact.proof.kind, spans(previous.proof.inputs, fact.proof.inputs), EVALUATOR, fact.proof.scope_digest), fact.qualifiers)
        facts[fact.id] = fact
    def edge(kind, subject, target, proof, *, attrs=None, key='', cls=EC.EXTRACTED, proof_kind=None):
        if subject not in by_id or target not in by_id:
            return
        if attrs and 'anchor' in attrs:
            # A section-scoped claim and a bare file claim are different facts;
            # repeated links to the same section still merge all their witnesses.
            key += '#anchor=' + attrs['anchor']
        proof_kind = proof_kind or (PK.INFERRED if cls == EC.INFERRED else PK.JOINED if len({p.path for p in proof}) > 1 else PK.EXTRACTED)
        add(Fact(stable_id('edge', kind, subject, target, key), subject, kind, target, cls,
                 Proof(proof_kind, spans(proof), EVALUATOR), freeze(attrs or {})))
    def unknown(subject, code, message, proof, needed, *, absence=False):
        add(Fact(stable_id('unknown', code, subject, message), subject, 'unknown', message, EC.UNKNOWN,
                 Proof(PK.ABSENCE if absence else PK.COMPUTED, spans(proof), EVALUATOR,
                       snapshot.tree_digest if absence else None), freeze({'code': code, 'neededEvidence': needed, 'path': by_id[subject].node.path})))
    def resolve(source, raw, *, types=None):
        hit = resolved_link(source, raw, set(sources))
        if not hit:
            return None
        path, fragment = hit
        candidates = [r for r in records if r.node.path == path and (not types or r.node.type in types)]
        if fragment:
            matches = [r for r in candidates if fragment in (r.node.selector, r.node.id, anchor(r.name))
                       or (r.node.type == 'roadmap-item' and fragment.startswith(r.name.lower() + '-'))]
            if len(matches) > 1:
                raise ValueError(f'ambiguous typed link: {source.path} -> {raw}')
            if matches:
                return matches[0]
            # A real section of an otherwise whole-document entity remains that
            # entity, with the exact selector witness retained in its edge proof.
            target_source = sources[path]
            headings, counts = {}, {}
            for i, line in enumerate(target_source.lines, 1):
                if re.match(r'^#{1,6}\s', line):
                    key = anchor(line.lstrip('#').strip())
                    count = counts.get(key, 0)
                    headings[key + (f'-{count}' if count else '')] = i
                    counts[key] = count + 1
            whole_candidates = [r for r in candidates if r.node.selector == WHOLE_DOCUMENT]
            if fragment in headings and len(whole_candidates) == 1:
                target = whole_candidates[0]
                line = headings[fragment]
                return replace(target, spans=spans(target.spans, (target_source.span(line, line),)))
            return None
        if types and len(candidates) == 1:
            return candidates[0]
        try:
            return by_id[index.resolve(NodeRef(path, None, WHOLE_DOCUMENT)).id]
        except ValueError:
            return None
    roadmap = sources.get('docs/fleet-roadmap.md')
    for record in records:
        node = record.node
        source = sources.get(node.path)
        if source is None:
            continue
        if node.type == 'agent':
            load_columns, header_line, inferred_method = (), None, False
            for i, line in enumerate(source.lines, 1):
                stripped = line.strip()
                if stripped.startswith('|') and i < len(source.lines) and re.match(r'^\|\s*:?-{3,}', source.lines[i].strip()):
                    headers = [plain(cell) for cell in stripped.strip('|').split('|')]
                    load_columns = tuple(j for j, header in enumerate(headers) if re.search(r'\b(?:load|skill|method)\b', header, re.I))
                    inferred_method = not any(re.search(r'\b(?:load|skill)\b', headers[j], re.I) for j in load_columns)
                    header_line = i
                    continue
                if not stripped.startswith('|'):
                    load_columns, header_line = (), None
                if load_columns and _table_data(source.lines, i):
                    cells = stripped.strip('|').split('|')
                    selected = ' '.join(cells[j] for j in load_columns if j < len(cells))
                    condition = plain(cells[0])
                    proof = (source.span(header_line, header_line), source.span(i, i))
                elif re.match(r'^Load\s+`', stripped):
                    selected, condition, proof = stripped, plain(stripped), (source.span(i, i),)
                    inferred_method = False
                else:
                    continue
                for name in re.findall(r'`([a-z][a-z0-9-]+)`', selected):
                    target = f'skill:{name}'
                    if target in by_id:
                        edge('loads_when', node.id, target, spans(proof, by_id[target].spans),
                             key=condition, attrs={'predicate': condition, 'via': 'agent-method'},
                             cls=EC.INFERRED if inferred_method else EC.EXTRACTED,
                             proof_kind=PK.INFERRED if inferred_method else PK.JOINED)
        if node.type == 'bundle-file':
            skill = dict(record.attrs)['skill']
            edge('cites', f'skill:{skill}', node.id, record.spans)
        if node.type == 'skill':
            references, routing = {}, {}
            for i, line in enumerate(source.lines, 1):
                targets = [raw for _, raw in link_targets(line) if raw.startswith(('references/', './references/'))]
                if targets and _table_data(source.lines, i):
                    predicate = plain(line.strip('|').split('|')[0])
                    for target in targets:
                        routing.setdefault(target, []).append((predicate, i))
                for target in targets:
                    references.setdefault(target, []).append(i)
            for target, positions in references.items():
                dest = resolve(source, target, types={'reference'})
                if not dest:
                    unknown(node.id, 'extract.skill-link-unresolved', f'{source.path}:{positions[0]} links {target}, which does not exist', (source.span(positions[0], positions[0]),), 'Restore the file or remove the link', absence=True)
                    continue
                for predicate, line in routing.get(target, [('UNKNOWN', positions[0])]):
                    edge('loads_when', node.id, dest.node.id, (source.span(line, line),), attrs={'predicate': predicate}, key=predicate)
        if node.type == 'rule':
            row = next((p for p in record.spans if p.start_line == p.end_line and source.lines[p.start_line - 1].startswith('|')), None)
            if row:
                links = link_targets(source.lines[row.start_line - 1])
                if not links:
                    unknown(node.id, 'extract.rule-source-unlinked', f'{source.path}:{row.start_line} names its source in prose only: {dict(record.attrs)["source_text"][:80]}', (row,), 'Link the primary source')
                for _, raw in links:
                    dest = resolve(source, raw)
                    if dest:
                        edge('governed_by', node.id, dest.node.id, spans((row,), dest.spans) if '#' in raw else (row,), attrs={'anchor': raw.split('#', 1)[1]} if '#' in raw else None)
                    else:
                        unknown(node.id, 'extract.rule-source-missing', f'{source.path}:{row.start_line} links {raw}, which does not resolve', (row,), 'Fix the link or supply its target', absence=True)
        if node.type == 'review':
            for i, line in enumerate(source.lines, 1):
                for _, raw in link_targets(line):
                    dest = resolve(source, raw)
                    if dest and dest.node.id != node.id:
                        proof = spans((source.span(i, i),), dest.spans) if '#' in raw else (source.span(i, i),)
                        edge('cites', node.id, dest.node.id, proof, key=str(i), attrs={'anchor': raw.split('#', 1)[1]} if '#' in raw else None)
                    elif resolved_link(source, raw, set(sources)) and '#' in raw:
                        unknown(node.id, 'extract.link-selector-unresolved', f'{source.path}:{i} selector does not resolve: {raw}', (source.span(i, i),), 'Correct the section selector or restore its exact target', absence=True)
        if node.type == 'scenario':
            data, _ = yaml_fields(source); routing = data.get('routing') or {}
            target = data.get('target') or ({'kind': 'agent', 'name': data['agent']} if data.get('agent') else {'kind': 'skill', 'name': data['skill']} if data.get('skill') else {})
            target_id = f'{target.get("kind")}:{target.get("name")}'
            proof = yaml_key_spans(source, ('target', 'agent', 'skill', 'routing', 'mode'))
            if target_id not in by_id:
                unknown(node.id, 'extract.scenario-target-missing', f'{source.path} targets {target_id}, which has no node', proof, 'Retarget the scenario or restore the component', absence=True)
            elif routing.get('expect') == 'not_fire':
                alt = routing.get('expected_alternative')
                edge('near_miss_for', node.id, target_id, proof, attrs={'expected_alternative': dict(record.attrs)['expected_alternative']})
                if isinstance(alt, dict):
                    edge('routes_to', node.id, f'{alt.get("kind")}:{alt.get("name")}', proof, attrs={'via': 'expected_alternative'})
            else:
                edge('verified_by', target_id, node.id, proof, attrs={'mode': data.get('mode', '')})
            for item in sorted(set(ITEM.findall(source.text))):
                edge('cites', node.id, f'roadmap-item:{item}', source.locate(item), attrs={'via': 'comment'}, cls=EC.INFERRED)
        if node.type == 'test':
            for path, proof in test_file_reads(source):
                if path not in sources:
                    continue
                dest = resolve(source, '../' + path)
                if dest:
                    edge('verified_by', dest.node.id, node.id, proof, attrs={'via': 'file-read'})
        if node.type == 'decision':
            for i, line in enumerate(source.lines[:14], 1):
                for item in re.findall(r'disposes\s+`([A-Z][A-Z0-9]*-\d{3})`', line):
                    edge('supersedes', node.id, f'roadmap-item:{item}', (source.span(i, i),), key='disposes', attrs={'relation': 'disposes'})
                match = re.search(r'\*\*Supersedes:?\*\*:?\s*(.+)|^-?\s*Supersedes:\s*(.+)', line, re.I)
                if match:
                    text = (match.group(1) or match.group(2)).strip()
                    resolved = [dest for _, raw in link_targets(line) if (dest := resolve(source, raw))]
                    if not resolved:
                        unknown(node.id, 'extract.supersedes-unresolved', f'{source.path}:{i} supersedes {text[:120]!r} but names no linked target', (source.span(i, i),), 'Link the superseded decision, rule row, or document')
                    for dest in resolved:
                        edge('supersedes', node.id, dest.node.id, (source.span(i, i),), attrs={'relation': 'supersedes', 'text': text[:200]})
                        needle = text[:40]
                        if needle and dest.node.path in sources and needle in sources[dest.node.path].text:
                            edge('contradicts', node.id, dest.node.id, spans((source.span(i, i),), sources[dest.node.path].locate(needle)), key='superseded_text_present', attrs={'detector': 'superseded_text_present', 'message': f'{dest.node.path} still contains superseded text: {needle!r}'}, cls=EC.INFERRED)
        if node.type in ('skill', 'command'):
            for i, line in enumerate(source.lines, 1):
                if not re.match(r'^\*\*Owner:\*\*', line):
                    continue
                for owner in re.findall(r'`([a-z][a-z0-9-]+)`\s+owns?\b', line):
                    subject = f'agent:{owner}' if f'agent:{owner}' in by_id else f'owner:{owner}'
                    edge('owns', subject, node.id, spans((source.span(i, i),), by_id[subject].spans if subject in by_id else ()), attrs={'field': 'Owner'}, proof_kind=PK.JOINED)
    if roadmap:
        for item, start, end, fields, positions in records_for_roadmap(roadmap):
            subject = f'roadmap-item:{item}'
            for field, value in fields.items():
                for other in set(ITEM.findall(value)) - {item}:
                    edge('depends_on', subject, f'roadmap-item:{other}', positions[field], key=field,
                         attrs={'field': field, 'detector': 'check_plan_status.prerequisites' if field == 'Prerequisites' else 'extract.roadmap-mention'},
                         cls=EC.CONTRACT if field == 'Prerequisites' else EC.INFERRED)
            owner = fields.get('Owner', '')
            proof = positions.get('Owner', ())
            if proof:
                mentioned = {m: suffix for m, suffix in re.findall(r'`([a-z][a-z0-9-]+)`([^`]*)', owner)}
                for name in mentioned:
                    if f'owner:{name}' in by_id:
                        edge('owns', f'owner:{name}', subject, proof, attrs={'field': 'Owner'})
                prefix = owner.split('`', 1)[0].strip()
                human = re.split(r'\s+owns?\b', prefix, maxsplit=1, flags=re.I)[0].strip(' .,:;')
                if human:
                    edge('owns', f'owner:{slug(human)}', subject, proof, attrs={'field': 'Owner'})
                for match in re.finditer(r'`([a-z][a-z0-9-]+)`\s+owns?\b([^.;]+)', owner):
                    for name in re.findall(r'`([a-z][a-z0-9-]+)`', match.group(2)):
                        for typ in ('skill', 'command'):
                            target = f'{typ}:{name}'
                            if target in by_id:
                                subject = f'agent:{match.group(1)}' if f'agent:{match.group(1)}' in by_id else f'owner:{match.group(1)}'
                                edge('owns', subject, target, spans(proof, by_id[target].spans), attrs={'field': 'Owner'}, proof_kind=PK.JOINED)
    # Evidence links resolve the selected decision/review, never whichever node sharing
    # its path happened to be created first. Batch joins cite BOTH determining records.
    incoming_reviews = set()
    for record in records:
        if record.node.type not in ('roadmap-item', 'decision'):
            continue
        source = sources[record.node.path]
        if record.node.type == 'roadmap-item':
            if source.path == 'docs/roadmap-closed.md':
                ranges = [(p.start_line, p.end_line) for p in record.spans]
            else:
                ranges = [(start, end) for item, start, end, _, _ in records_for_roadmap(source) if item == record.name]
        else:
            ranges = [(1, len(source.lines))]
        for i in sorted({i for start, end in ranges for i in range(start, end + 1)}):
            line = source.lines[i - 1]
            for _, raw in link_targets(line):
                dest = resolve(source, raw, types={'review', 'decision'})
                if dest and dest.node.type in ('review', 'decision') and dest.node.id != record.node.id:
                    proof = spans((source.span(i, i),), dest.spans) if '#' in raw else (source.span(i, i),)
                    edge('evidenced_by', record.node.id, dest.node.id, proof, attrs={'anchor': raw.split('#', 1)[1]} if '#' in raw else None)
                    incoming_reviews.add(dest.node.id)
            for batch in set(BATCH.findall(line)):
                targets = [r for r in records if r.node.type == 'review' and batch in dict(r.attrs).get('batches', ())]
                if not targets and record.node.type == 'roadmap-item':
                    unknown(record.node.id, 'extract.batch-unresolved', f'{source.path}:{i} cites batch {batch} with no review', (source.span(i, i),), 'Retain the durable review behind the batch', absence=True)
                for target in targets:
                    edge('evidenced_by', record.node.id, target.node.id,
                         spans((source.span(i, i),), sources[target.node.path].locate(batch)), key=batch,
                         attrs={'batch': batch}, proof_kind=PK.JOINED)
                    incoming_reviews.add(target.node.id)
    catalog = sources.get('schemas/catalog-v1.json')
    if catalog:
        for entry in json.loads(catalog.text).get('schemas', []):
            subject = f'schema:{entry["id"]}'
            validator = entry.get('validator')
            if validator in sources:
                dest = resolve(catalog, '../' + validator)
                if dest:
                    edge('constrained_by', subject, dest.node.id, whole(catalog), attrs={'via': 'catalog-v1.json'}, cls=EC.CONTRACT)
            for projection in entry.get('generated_projections', []):
                targets = [r for r in records if r.node.path == projection and r.node.type in ('generated-projection', 'schema-projection')]
                for target in targets:
                    edge('constrained_by', target.node.id, subject, whole(catalog), attrs={'via': 'catalog-v1.json'}, cls=EC.CONTRACT)
                if not targets:
                    unknown(subject, 'extract.schema-projection-unresolved', f'{entry["id"]} declares generated_projections {projection}, which has no node yet', whole(catalog), 'Build the declared projection or correct its catalog entry', absence=True)
    declared = {(schema_id, projection): proof for schema_id, projection, proof in standalone_projections(snapshot)}
    for source in snapshot.sources:
        if not source.path.startswith('schemas/') or not source.path.endswith('.schema.json'):
            continue
        declaration = json.loads(source.text)
        if not isinstance(declaration, dict):
            continue
        subject = 'schema:' + Path(source.path).name.removesuffix('.schema.json')
        if subject not in by_id:
            continue
        validator = declaration.get('x-fleet-validator')
        if validator:
            if validator in sources:
                target = index.resolve(NodeRef(validator, None, WHOLE_DOCUMENT))
                edge('constrained_by', subject, target.id, whole(source), attrs={'via': 'schema-declaration'})
            else:
                unknown(subject, 'extract.schema-validator-unresolved', f'{source.path} declares missing validator {validator}', whole(source), 'Restore the declared validator or correct the schema declaration', absence=True)
        for projection in declaration.get('x-fleet-generated-projections', []):
            if (subject, projection) in declared:
                edge('constrained_by', 'schema-projection:' + projection, subject, declared[subject, projection],
                     attrs={'via': 'schema-declaration-and-writer'}, cls=EC.CONTRACT, proof_kind=PK.JOINED)
            else:
                unknown(subject, 'extract.schema-projection-unproved', f'{source.path} declares {projection} without a resolved writer mapping', whole(source), 'Bind the declared output to the actual writer mapping', absence=True)
    for projection, canonical, proof in generated_mappings(snapshot):
        generated = 'generated-projection:' + projection
        if generated not in by_id:
            continue
        source = sources[canonical]
        target = index.resolve(NodeRef(canonical, None, WHOLE_DOCUMENT))
        edge('generated_from', generated, target.id, spans(proof, whole(source)),
             attrs={'via': 'generate_platform_adapters.expected_outputs'}, cls=EC.CONTRACT, proof_kind=PK.JOINED)
    validator = sources.get('scripts/validate_fleet.py')
    expected, expected_proof = assignment(validator, 'EXPECTED_DELEGATION') if validator else (None, ())
    roster = sources.get('AGENTS.md')
    rows = {plain(cells[0]): (i, cells) for i, cells in roster_rows(roster)} if roster else {}
    if isinstance(expected, dict):
        for agent, targets in sorted(expected.items()):
            subject = f'agent:{agent}'
            if subject not in by_id:
                continue
            granted = set(dict(by_id[subject].attrs)['grants'])
            if granted != set(targets):
                unknown(subject, 'cite.delegation-mismatch', f'agents/{agent}.md grants {sorted(granted)} but EXPECTED_DELEGATION says {sorted(targets)}', spans(expected_proof, by_id[subject].spans), 'Reconcile the agent frontmatter and validated delegation contract')
            else:
                for target in sorted(targets):
                    edge('delegates_to', subject, f'agent:{target}', spans(expected_proof, by_id[subject].spans), cls=EC.CONTRACT, proof_kind=PK.JOINED)
            if agent in rows:
                i, cells = rows[agent]
                stated = set(re.findall(r'`([a-z0-9-]+)`', cells[-1]))
                if stated != set(targets):
                    edge('contradicts', subject, 'document:AGENTS.md', spans(expected_proof, (roster.span(i, i),)), key='delegation_mismatch',
                        attrs={'detector': 'delegation_mismatch', 'message': f'roster says {agent} delegates to {sorted(stated)}; validate_fleet enforces {sorted(targets)}'}, cls=EC.INFERRED)
    for agent, (i, cells) in rows.items():
        edge('owns', f'agent:{agent}', 'capability:' + slug(plain(cells[1]))[:60], (roster.span(i, i),), attrs={'via': 'roster-lane'}, cls=EC.INFERRED)
    generator = sources.get('scripts/generate_platform_adapters.py')
    guarded, guarded_proof = assignment(generator, 'GUARDED_AGENTS') if generator else (None, ())
    hook = sources.get('hooks/hooks.json')
    if hook and 'hook:readonly-guard' in by_id and isinstance(guarded, (set, tuple, list)):
        for agent in sorted(guarded):
            roster_proof = (roster.span(rows[agent][0], rows[agent][0]),) if agent in rows else ()
            edge('constrained_by', f'agent:{agent}', 'hook:readonly-guard', spans(guarded_proof, whole(hook), roster_proof),
                attrs={'via': 'generate_platform_adapters.GUARDED_AGENTS'}, cls=EC.CONTRACT, proof_kind=PK.JOINED)
    # Staleness is advisory for every dated live status, never an artifact-check failure.
    for record in records:
        if record.node.type == 'roadmap-item' and record.state == 'live':
            date = DATE.search(str(dict(record.attrs).get('status_text', '')))
            evidence = [by_id[f.object] for f in facts.values() if f.subject == record.node.id and f.predicate == 'evidenced_by']
            dated = [(r, dict(r.attrs).get('date')) for r in evidence if dict(r.attrs).get('date')]
            if date and dated and max(d for _, d in dated) < date.group():
                newest = max(d for _, d in dated)
                unknown(record.node.id, 'stale.evidence-predates-status', f'{record.name} status is dated {date.group()} but its newest cited evidence is {newest}', spans(record.spans, *(r.spans for r, _ in dated)), 'Cite the evidence behind the current status or revise the status')
    for source in snapshot.sources:
        if source.path in LIVE_DOCS or Path(source.path).name in ('README.md', 'CHANGELOG.md') or source.path == 'docs/roadmap-closed.md':
            for _, raw in link_targets(source.text):
                target = resolve(source, raw, types={'review'})
                if target and target.node.type == 'review':
                    incoming_reviews.add(target.node.id)
    incoming_reviews.update(f.object for f in facts.values() if f.predicate in ('cites', 'evidenced_by'))
    for record in records:
        if record.node.type == 'review' and record.node.id not in incoming_reviews:
            unknown(record.node.id, 'stale.review-uncited', f'{record.node.path} is cited by no roadmap item, decision, review, or live guide', record.spans,
                    'Remove unneeded review evidence or restore its authoritative citation', absence=True)
    stale_source = sources.get('scripts/check_stale_names.py')
    retired, retired_proof = assignment(stale_source, 'STALE') if stale_source else (None, ())
    if isinstance(retired, tuple):
        scanned = ('agents/', 'skills/', 'commands/', 'evals/scenarios/')
        exempt = {Path(s.path).stem for s in snapshot.sources if s.path.startswith(scanned)} & set(retired)
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
        for record in records:
            if not record.node.path.startswith(scanned):
                continue
            source = sources[record.node.path]
            for i, line in enumerate(source.lines, 1):
                found = None
                for match in re.finditer(r'(?<![a-z0-9-])(' + '|'.join(re.escape(name) for name in retired) + r')(?![a-z0-9-])', line):
                    before = line[match.start() - 1] if match.start() else ''
                    after = line[match.end():]
                    if match.group(1) in exempt and (before == '/' or after.startswith(('/', '.md'))):
                        continue
                    found = match.group(1)
                    break
                if found:
                    unknown(record.node.id, 'stale.retired-name', f'{source.path}:{i}: stale fleet-unit name {found!r}', spans((source.span(i, i),), retired_proof), 'Resolve the stale fleet name or document its valid path exemption')
                    break
    implementation = sources.get('scripts/fleet_atlas_v2_extract.py')
    implementation_id = 'validator:scripts/fleet_atlas_v2_extract.py'
    if implementation and implementation_id in by_id:
        add(Fact(stable_id('fact', implementation_id, 'attr.blocks_emission'), implementation_id, 'attr.blocks_emission',
                 'no direct blocks edge; query reverses depends_on', EC.EXTRACTED,
                 Proof(PK.ABSENCE, whole(implementation), EVALUATOR, snapshot.tree_digest)))
    return tuple(facts[key] for key in sorted(facts))


# Endpoint authority is explicit, while trusted replay enforces syntax-level authority:
# a path literal inside a test never becomes a verified_by edge merely by matching a glob.
EDGE_ENDPOINTS = {
    'owns': ({'owner', 'agent'}, NODE_TYPES),
    'routes_to': ({'scenario'}, {'agent', 'skill', 'command'}),
    'delegates_to': ({'agent'}, {'agent'}),
    'loads_when': ({'skill', 'agent'}, {'reference', 'skill'}),
    'governed_by': ({'rule'}, NODE_TYPES),
    'constrained_by': (NODE_TYPES, {'hook', 'schema', 'validator', 'document'}),
    'verified_by': (NODE_TYPES, {'scenario', 'test'}),
    'evidenced_by': ({'roadmap-item', 'decision'}, {'decision', 'review'}),
    'depends_on': ({'roadmap-item'}, {'roadmap-item'}),
    'blocks': ({'roadmap-item'}, {'roadmap-item'}),
    'supersedes': ({'decision'}, NODE_TYPES),
    'generated_from': ({'generated-projection'}, NODE_TYPES),
    'near_miss_for': ({'scenario'}, {'agent', 'skill', 'command'}),
    'contradicts': (NODE_TYPES, NODE_TYPES),
    'cites': (NODE_TYPES, NODE_TYPES),
}


def _guidance(snapshot, records):
    """Complete body paragraphs, split by encoded size without dropping long lines."""
    output = []
    for record in records:
        if (record.node.selector != WHOLE_DOCUMENT or record.authority not in ('canonical', 'live-contract')
                or record.state != 'live' or not record.node.path.endswith('.md')
                or record.node.type not in ('agent', 'skill', 'reference', 'command', 'document')):
            continue
        source = snapshot.source(record.node.path)
        start = 0
        if source.lines and source.lines[0] == '---':
            start = next((i + 1 for i, line in enumerate(source.lines[1:], 1) if line == '---'), 0)
        paragraph, heading, heading_line = [], '', None

        def emit():
            if not paragraph:
                return
            text = '\n'.join(line for _, line in paragraph)
            offset = 0
            while offset < len(text):
                chunk = text[offset:].encode('utf-8')[:2400].decode('utf-8', errors='ignore')
                end = offset + len(chunk)
                proof = (source.span(paragraph[0][0], paragraph[-1][0]),)
                if heading_line:
                    proof = spans(proof, (source.span(heading_line, heading_line),))
                output.append(Fact(stable_id('guidance', record.node.id, str(paragraph[0][0]), str(offset)),
                    record.node.id, 'guidance', chunk, EC.EXTRACTED, Proof(PK.EXTRACTED, proof, EVALUATOR),
                    freeze({'heading': heading, 'start_offset': offset, 'end_offset': end})))
                offset = end
            paragraph.clear()

        for i, line in enumerate(source.lines[start:], start + 1):
            if line.startswith('#'):
                emit()
                heading, heading_line = line.lstrip('#').strip(), i
            if line.strip():
                paragraph.append((i, line))
            else:
                emit()
        emit()
    return tuple(output)


def _record_facts(snapshot, inputs):
    records = inputs['catalog'].records
    buckets = {}
    for record in records:
        nodes, facts = buckets.setdefault(record.family, ([], []))
        nodes.append(record.node)
        fields = (('name', record.name), ('authority', record.authority), ('state', record.state)) + tuple(('attr.' + key, value) for key, value in record.attrs)
        for predicate, value in fields:
            kind = record.proof_kind
            if record.evidence_class == EC.INFERRED:
                kind = PK.INFERRED
            elif predicate == 'authority' or predicate in ('attr.bytes', 'attr.fields', 'attr.batches', 'attr.batch', 'attr.banner',
                                                         'attr.linked_from_roadmap', 'attr.kind', 'attr.skill', 'attr.file'):
                kind = PK.COMPUTED
            elif predicate == 'name' and record.node.type != 'scenario':
                kind = PK.COMPUTED  # Filename, stable identity, row excerpt or declared owner.
            elif predicate in ('state', 'attr.manual_only', 'attr.grants', 'attr.description'):
                kind = PK.NORMALIZED
            elif predicate == 'attr.status' and record.node.type == 'roadmap-item':
                kind = PK.NORMALIZED
            elif predicate in ('attr.status_text', 'attr.owner', 'attr.disposition'):
                kind = PK.COMPUTED  # The donor's bounded display value, not the entire field.
            facts.append(Fact(stable_id('fact', record.node.id, predicate), record.node.id, predicate, value,
                record.evidence_class, Proof(kind, record.spans, EVALUATOR)))
    return StageOutput(buckets=tuple(Bucket(name, tuple(sorted(nodes)), tuple(sorted(facts, key=lambda f: f.id)))
                 for name, (nodes, facts) in sorted(buckets.items())))


def _relationship_facts(snapshot, inputs):
    return StageOutput(buckets=(Bucket('relationships', (), _relations(snapshot, inputs['catalog'].records)),))


def _guidance_facts(snapshot, inputs):
    facts = _guidance(snapshot, inputs['catalog'].records)
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


def _derive(snapshot, stages=EXTRACTION_STAGES):
    registered = {}
    for stage in stages:
        if stage.name in registered:
            raise ValueError(f'duplicate extraction stage: {stage.name}')
        registered[stage.name] = stage
    for stage in registered.values():
        missing = set(stage.requires) - registered.keys()
        if missing:
            raise ValueError(f'missing extraction prerequisites for {stage.name}: {sorted(missing)}')
    # Validate the complete dependency plan before invoking any producer.
    pending, plan, available = dict(registered), [], set()
    while pending:
        ready = sorted(name for name, stage in pending.items() if set(stage.requires) <= available)
        if not ready:
            raise ValueError(f'extraction dependency cycle: {sorted(pending)}')
        for name in ready:
            plan.append(pending.pop(name))
            available.add(name)
    completed = {}
    for stage in plan:
        inputs = MappingProxyType({name: completed[name] for name in stage.requires})
        output = stage.produce(snapshot, inputs)
        if not isinstance(output, StageOutput):
            raise TypeError(f'extraction stage {stage.name} did not return frozen StageOutput')
        completed[stage.name] = output
    return tuple(sorted((bucket for output in completed.values() for bucket in output.buckets),
                        key=lambda bucket: bucket.extractor))


@lru_cache(maxsize=2)
def _replayed(snapshot):
    # Separate source reconstruction, not a cache populated by submitted candidate facts.
    return MappingProxyType({f.id: f for bucket in _derive(snapshot) for f in bucket.facts})


def replay(fact, snapshot, _verified_premises):
    expected = _replayed(snapshot).get(fact.id)
    if expected is None or (expected.subject, expected.predicate) != (fact.subject, fact.predicate):
        raise ValueError(f'claim not produced by its source authority: {fact.id}')
    return Derivation(expected.object, expected.evidence_class, expected.proof, expected.qualifiers)


def extract(snapshot: Snapshot, *, stages=EXTRACTION_STAGES) -> Extraction:
    buckets = _derive(snapshot, stages)
    fields = {f.predicate for b in buckets for f in b.facts} - EDGE_TYPES
    # All source spans are replayed; joined proofs may include canonical targets and
    # controlling validators in addition to their declaration source.
    authority = ('*.md', '*.py', '*.json', '*.yaml', '*.yml', '*.toml', '*.txt', '*.sh', '*.ps1', '*.js', '*.ts', '*.html', '*.css', '*.svg', '*.ini', '*.cfg')
    predicates = tuple(Predicate(name, frozenset(source), frozenset(target), authority)
                       for name, (source, target) in sorted(EDGE_ENDPOINTS.items()))
    predicates += tuple(Predicate(name, NODE_TYPES, None, authority, None if name in ('unknown', 'guidance') else 1)
                        for name in sorted(fields))
    return Extraction(buckets, predicates, MappingProxyType({EVALUATOR: replay}))
