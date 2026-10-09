"""Source authority and donor semantic regressions for the v2 extractors (no model)."""
import dataclasses
import random
import unittest
from pathlib import Path

from fleet_atlas_v2_extract import extract, rooted_reads, scenario_fields, EDGE_TYPES, NODE_TYPES
from fleet_atlas_v2_model import (assemble, EvidenceClass, ProofKind, Proof)
from fleet_atlas_v2_sources import Snapshot, Source
from fleet_atlas_v2_proofs import verify_facts

ROOT = Path(__file__).resolve().parents[1]


def snapshot(files):
    return Snapshot('1' * 40, tuple(Source(p, text.encode()) for p, text in sorted(files.items())))


def agent(name, tools='Read'):
    return f'---\nname: {name}\ndescription: Test agent.\ntools: {tools}\n---\n# {name}\n'


def skill(name):
    return f'---\nname: {name}\ndescription: Test skill.\n---\n# {name}\n'


def build(files):
    source = snapshot(files)
    result = extract(source)
    graph = assemble(result.buckets, result.predicates)
    verify_facts(graph, source, result.predicates, result.evaluators)
    return source, result, graph


class ExtractTests(unittest.TestCase):
    def assertMatchesYaml(self, text, keys=('id', 'target', 'routing', 'threshold')):
        """The scenario metadata subset reads `keys` exactly as a real YAML parser does."""
        import yaml  # Independent test oracle; the installed atlas runtime stays stdlib-only.
        expected = yaml.safe_load(text)
        parsed, _ = scenario_fields(Source('evals/scenarios/case.yaml', text.encode()))
        for key in keys:
            self.assertEqual(expected[key], parsed[key])
        return expected, parsed

    def test_evidence_link_resolves_by_selector_not_path(self):
        _, _, graph = build({
            'docs/fleet-roadmap.md': '# Roadmap\n### EVAL-003 test\n**Status:** `active`\n**Evidence:** [decision](decisions/choice.md)\n',
            'docs/decisions/choice.md': '# Decision\n**Status:** accepted\n',
            'schemas/catalog-v1.json': '{"schemas":[{"id":"same-path","canonical_path":"docs/decisions/choice.md","status":"active","version":1}]}',
        })
        edge = next(f for f in graph.facts if f.predicate == 'evidenced_by')
        self.assertEqual('decision:choice', edge.object)
        self.assertIn('schema:same-path', {n.id for n in graph.nodes})
        self.assertIn('decision:choice', {n.id for n in graph.nodes})

    def test_owner_field_naming_a_component_emits_owner_to_component_edge(self):
        _, _, graph = build({'agents/agent-engineer.md': agent('agent-engineer'),
            'skills/fleet-atlas/SKILL.md': skill('fleet-atlas'),
            'docs/fleet-roadmap.md': '# Roadmap\n### GRAPH-004 test\n**Owner:** `agent-engineer` owns the `fleet-atlas` skill text.\n'})
        found = [f for f in graph.facts if f.predicate == 'owns' and f.object == 'skill:fleet-atlas']
        self.assertEqual(1, len(found))
        self.assertEqual('agent:agent-engineer', found[0].subject)
        self.assertEqual(ProofKind.JOINED, found[0].proof.kind)
        self.assertNotIn('owner:fleet-atlas', {n.id for n in graph.nodes})

    def test_explicit_skill_owner_body_is_distinct_from_incidental_mention(self):
        files = {'agents/agent-engineer.md': agent('agent-engineer'),
            'skills/fleet-atlas/SKILL.md': skill('fleet-atlas') + '**Owner:** `agent-engineer` owns the fleet-atlas capability.\n'}
        _, _, graph = build(files)
        self.assertTrue(any(f.predicate == 'owns' and f.object == 'skill:fleet-atlas' for f in graph.facts))
        files['skills/fleet-atlas/SKILL.md'] = skill('fleet-atlas') + 'Related agent: `agent-engineer`.\n'
        self.assertFalse(any(f.predicate == 'owns' and f.object == 'skill:fleet-atlas' for f in build(files)[2].facts))

    def test_explicit_agent_method_table_preserves_skill_and_condition(self):
        body = agent('reliability-engineer') + '''## Choose the method
| Assignment | Load when needed |
|---|---|
| Existing service readiness | `service-lifecycle` |

The service-lifecycle lane was discussed in a review.
'''
        _, _, graph = build({'agents/reliability-engineer.md': body,
                            'skills/service-lifecycle/SKILL.md': skill('service-lifecycle')})
        references = [f for f in graph.facts if f.subject == 'agent:reliability-engineer' and f.predicate == 'loads_when']
        self.assertEqual(1, len(references))
        self.assertEqual('skill:service-lifecycle', references[0].object)
        self.assertEqual('Existing service readiness', dict(references[0].qualifiers)['predicate'])
        self.assertEqual('agent-method', dict(references[0].qualifiers)['via'])
        self.assertEqual(EvidenceClass.EXTRACTED, references[0].evidence_class)
        no_table = body.split('## Choose the method')[0] + 'Mention `service-lifecycle` only.\n'
        _, _, changed = build({'agents/reliability-engineer.md': no_table,
                              'skills/service-lifecycle/SKILL.md': skill('service-lifecycle')})
        self.assertFalse(any(f.predicate == 'loads_when' and f.subject == 'agent:reliability-engineer' for f in changed.facts))

    def test_catalog_node_proof_is_extracted_over_every_contributing_field(self):
        text = '''{"schemas": [{
 "id": "test-v1",
 "canonical_path": "schemas/test.json",
 "status": "active",
 "version": 7,
 "validator": "scripts/check.py",
 "generated_projections": []
}]}'''
        _, _, graph = build({'schemas/catalog-v1.json': text, 'schemas/test.json': '{}\n', 'scripts/check.py': 'pass\n'})
        claims = [f for f in graph.facts if f.subject == 'schema:test-v1']
        self.assertTrue(claims)
        for claim in claims:
            self.assertTrue(any(p.path == 'schemas/catalog-v1.json' and p.start_line <= 2 and p.end_line >= 7 for p in claim.proof.inputs))
        self.assertEqual(ProofKind.EXTRACTED, next(f for f in claims if f.predicate == 'attr.version').proof.kind)

    def test_batch_edge_proof_is_joined_and_cites_both_sides(self):
        _, _, graph = build({
            'docs/fleet-roadmap.md': '# Roadmap\n### EVAL-003 test\n**Evidence:** batch 20260930T010101Z-abcd1234\n',
            'docs/reviews/result.md': '# Result\nMeasured batch: 20260930T010101Z-abcd1234\n'})
        fact = next(f for f in graph.facts if f.predicate == 'evidenced_by')
        self.assertEqual(ProofKind.JOINED, fact.proof.kind)
        self.assertEqual({'docs/fleet-roadmap.md', 'docs/reviews/result.md'}, {p.path for p in fact.proof.inputs})
        self.assertTrue(any(p.path.endswith('result.md') and p.start_line == 2 for p in fact.proof.inputs))

    def test_wrapped_and_nested_label_evidence_links_are_preserved(self):
        _, _, graph = build({
            'docs/fleet-roadmap.md': '# Roadmap\n### EVAL-003 test\n**Evidence:** [fixed Windows\npacket](reviews/result.md), and [`[verified]` report](reviews/second.md).\n',
            'docs/reviews/result.md': '# Result\n', 'docs/reviews/second.md': '# Other\n'})
        self.assertEqual({'review:result', 'review:second'}, {f.object for f in graph.facts if f.predicate == 'evidenced_by'})

    def test_review_packets_with_the_same_filename_keep_distinct_evidence(self):
        _, _, graph = build({
            'docs/fleet-roadmap.md': '# Roadmap\n### AUDIT-001 test\n**Evidence:** '
                '[first](reviews/first/README.md#first-packet), '
                '[second](reviews/second/README.md#second-packet), '
                '[flat](reviews/README.md#flat-packet).\n',
            'docs/reviews/first/README.md': '# First packet\nUnique first evidence.\n',
            'docs/reviews/second/README.md': '# Second packet\nUnique second evidence.\n',
            'docs/reviews/README.md': '# Flat packet\nExisting flat-file identity.\n',
        })
        reviews = {node.id: node.path for node in graph.nodes if node.type == 'review'}
        self.assertEqual({
            'review:first/README': 'docs/reviews/first/README.md',
            'review:second/README': 'docs/reviews/second/README.md',
            'review:README': 'docs/reviews/README.md',
        }, reviews)
        evidence = [fact for fact in graph.facts
                    if fact.subject == 'roadmap-item:AUDIT-001' and fact.predicate == 'evidenced_by']
        self.assertEqual(set(reviews), {fact.object for fact in evidence})
        self.assertEqual(3, len(evidence))
        for fact in evidence:
            self.assertEqual({'docs/fleet-roadmap.md', reviews[fact.object]},
                             {span.path for span in fact.proof.inputs})

    def test_valid_section_anchor_keeps_file_identity_and_exact_target_witness(self):
        files = {'docs/reviews/source.md': '# Source\n[section](target.md#measured-result)\n',
                 'docs/reviews/target.md': '# Target\n\n## Measured result\nThe record.\n'}
        _, _, graph = build(files)
        fact = next(f for f in graph.facts if f.predicate == 'cites')
        self.assertEqual('review:target', fact.object)
        self.assertEqual('measured-result', dict(fact.qualifiers)['anchor'])
        self.assertTrue(any(p.path.endswith('target.md') and p.start_line == p.end_line == 3 for p in fact.proof.inputs))
        files['docs/reviews/source.md'] = '# Source\n[section](target.md#missing)\n'
        _, _, changed = build(files)
        self.assertFalse(any(f.predicate == 'cites' for f in changed.facts))
        self.assertTrue(any(f.predicate == 'unknown' and dict(f.qualifiers)['code'] == 'extract.link-selector-unresolved' for f in changed.facts))

    def test_linked_review_inventory_keeps_source_bound_csv_identity(self):
        path = 'docs/reviews/packet/inventory.csv'
        _, _, graph = build({
            'docs/reviews/packet/README.md': '# Packet\n[Inventory](inventory.csv)\n',
            path: 'path,bytes\nskills/example/SKILL.md,123\n',
        })
        inventory = next(node for node in graph.nodes if node.path == path)
        self.assertEqual(('document:' + path, 'document'), (inventory.id, inventory.type))
        name = next(fact for fact in graph.facts
                    if fact.subject == inventory.id and fact.predicate == 'name')
        self.assertEqual(path, name.object)
        self.assertEqual(ProofKind.COMPUTED, name.proof.kind)
        self.assertEqual({path}, {span.path for span in name.proof.inputs})
        self.assertTrue(any(fact.subject == 'review:packet/README'
                            and fact.predicate == 'cites' and fact.object == inventory.id
                            for fact in graph.facts))

    def test_multiple_selectors_of_one_evidence_file_are_distinct_claims(self):
        _, _, graph = build({'docs/fleet-roadmap.md': '# Roadmap\n### SKILL-001 title\n**Evidence:** [first](reviews/result.md#first)\n[second](reviews/result.md#second)\n[whole](reviews/result.md)\n',
                             'docs/reviews/result.md': '# Result\n## First\nOne.\n## Second\nTwo.\n'})
        facts = [f for f in graph.facts if f.predicate == 'evidenced_by']
        self.assertEqual(3, len(facts))
        self.assertEqual(3, len({f.id for f in facts}))
        self.assertEqual({None, 'first', 'second'}, {dict(f.qualifiers).get('anchor') for f in facts})
        self.assertEqual({'review:result'}, {f.object for f in facts})

    def test_standalone_json_schema_retains_declared_contract_without_catalog(self):
        text = '''{
 "$schema": "https://json-schema.org/draft/2020-12/schema",
 "$id": "https://example.invalid/fleet-atlas-v2.schema.json",
 "title": "Fleet Atlas",
 "type": "object",
 "additionalProperties": false
}'''
        _, _, graph = build({'schemas/fleet-atlas-v2.schema.json': text})
        schema = next(n for n in graph.nodes if n.type == 'schema')
        self.assertEqual('schema:fleet-atlas-v2', schema.id)
        facts = {f.predicate: f for f in graph.facts if f.subject == schema.id}
        self.assertEqual('https://example.invalid/fleet-atlas-v2.schema.json', facts['attr.schema_uri'].object)
        self.assertEqual('object', facts['attr.type'].object)
        self.assertTrue(all(any(p.start_line == 1 and p.end_line == 7 for p in f.proof.inputs) for f in facts.values()))

    def test_standalone_projection_requires_schema_and_actual_writer_mapping(self):
        import json
        schema = json.dumps({'$id': 'https://example.invalid/fleet-atlas-v2.schema.json',
            'type': 'object', 'x-fleet-validator': 'scripts/fleet_atlas_v2.py',
            'x-fleet-generated-projections': ['docs/fleet-atlas/v2/atlas.json']})
        implementation = '''from pathlib import Path
import os
import tempfile
OUTPUT = Path("docs/fleet-atlas/v2")
def render_files(checked):
    files = {}
    files["atlas.json"] = b"generated"
    return files
def _safe_output(root):
    current = root
    for part in OUTPUT.parts:
        current = current / part
    return current
def build(root):
    files = render_files(root)
    output = _safe_output(root)
    for name in files:
        with tempfile.NamedTemporaryFile(dir=output) as handle:
            temporary = Path(handle.name)
            handle.write(files[name])
        os.replace(temporary, output / name)
'''
        files = {'schemas/fleet-atlas-v2.schema.json': schema,
                 'scripts/fleet_atlas_v2.py': '# Declared validation entrypoint\n',
                 'scripts/fleet_atlas_v2_artifacts.py': implementation}
        _, _, graph = build(files)
        subject = 'schema-projection:docs/fleet-atlas/v2/atlas.json'
        fact = next(f for f in graph.facts if f.subject == subject and f.predicate == 'constrained_by')
        self.assertEqual('schema:fleet-atlas-v2', fact.object)
        self.assertEqual(ProofKind.JOINED, fact.proof.kind)
        self.assertEqual({'schemas/fleet-atlas-v2.schema.json', 'scripts/fleet_atlas_v2.py', 'scripts/fleet_atlas_v2_artifacts.py'}, {p.path for p in fact.proof.inputs})
        self.assertTrue(any(p.path.endswith('_artifacts.py') and p.start_line <= 7 <= p.end_line for p in fact.proof.inputs))
        for changed in (implementation.replace('files["atlas.json"]', 'files["other.json"]'),
                        implementation.replace('output / name', 'root / name'),
                        implementation.replace('return files', 'return {}'),
                        implementation.replace('files = render_files(root)', 'render_files(root)\n    files = {}'),
                        implementation.replace('    for name in files:', '    files = {}\n    for name in files:'),
                        implementation.replace('    for name in files:', '    output = root\n    for name in files:'),
                        implementation.replace('handle.write(files[name])', 'handle.write(b"unrelated")'),
                        implementation.replace('for name in files:', 'for name in []:')):
            with self.subTest(changed=changed):
                _, _, failed = build({**files, 'scripts/fleet_atlas_v2_artifacts.py': changed})
                self.assertNotIn(subject, {n.id for n in failed.nodes})
                self.assertTrue(any(f.predicate == 'unknown' and dict(f.qualifiers)['code'] == 'extract.schema-projection-unproved' for f in failed.facts))
        del files['scripts/fleet_atlas_v2.py']
        _, _, failed = build(files)
        self.assertNotIn(subject, {n.id for n in failed.nodes})

    def test_real_artifact_writer_still_proves_its_schema_projection(self):
        # The synthetic writer above pins the recogniser; this pins the shipped writer.
        # Restructuring render_files/_safe_output/build outside the recognised shape
        # would otherwise drop the projection node from the real atlas without a failure.
        files = {
            'schemas/fleet-atlas-v2.schema.json': (ROOT / 'schemas/fleet-atlas-v2.schema.json').read_text(encoding='utf-8'),
            'scripts/fleet_atlas_v2.py': (ROOT / 'scripts/fleet_atlas_v2.py').read_text(encoding='utf-8'),
            'scripts/fleet_atlas_v2_artifacts.py': (ROOT / 'scripts/fleet_atlas_v2_artifacts.py').read_text(encoding='utf-8'),
        }
        _, _, graph = build(files)
        subject = 'schema-projection:docs/fleet-atlas/v2/atlas.json'
        self.assertIn(subject, {n.id for n in graph.nodes})
        fact = next(f for f in graph.facts if f.subject == subject and f.predicate == 'constrained_by')
        self.assertEqual('schema:fleet-atlas-v2', fact.object)
        self.assertEqual(ProofKind.JOINED, fact.proof.kind)
        self.assertFalse(any(f.predicate == 'unknown' and dict(f.qualifiers)['code'] == 'extract.schema-projection-unproved'
                             for f in graph.facts))

    def test_guard_edge_proof_is_joined_over_roster_and_hook_wiring(self):
        _, _, graph = build({'agents/sre-assistant.md': agent('sre-assistant'),
            'AGENTS.md': '# Roster\n| Agent | Lane | Tools | Delegates to |\n|---|---|---|---|\n| `sre-assistant` | observe | read | — |\n',
            'scripts/generate_platform_adapters.py': 'GUARDED_AGENTS = {"sre-assistant"}\n',
            'hooks/hooks.json': '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"command":"python readonly-guard.py"}]}]}}\n'})
        fact = next(f for f in graph.facts if f.predicate == 'constrained_by')
        self.assertEqual(ProofKind.JOINED, fact.proof.kind)
        self.assertEqual({'AGENTS.md', 'scripts/generate_platform_adapters.py', 'hooks/hooks.json'}, {p.path for p in fact.proof.inputs})

    def test_generated_from_proof_cites_mapping_span_not_signature(self):
        generator = '''from pathlib import Path
COPILOT_AGENTS = Path(".github/agents")
def expected_outputs(root):
    outputs = {}
    agents = sorted((root / "agents").glob("*.md"))
    for source in agents:
        outputs[COPILOT_AGENTS / f"{source.stem}.agent.md"] = b"rendered"
    return outputs
'''
        files = {'agents/sre-assistant.md': agent('sre-assistant'),
            '.github/agents/sre-assistant.agent.md': '# Projected agent\n',
            'scripts/generate_platform_adapters.py': generator}
        _, _, graph = build(files)
        fact = next(f for f in graph.facts if f.predicate == 'generated_from')
        self.assertEqual('agent:sre-assistant', fact.object)
        self.assertTrue(any(p.path.endswith('generate_platform_adapters.py') and p.start_line <= 7 <= p.end_line for p in fact.proof.inputs))
        self.assertFalse(all(p.start_line == p.end_line == 3 for p in fact.proof.inputs))
        files['scripts/generate_platform_adapters.py'] = generator.replace('outputs[COPILOT_AGENTS / f"{source.stem}.agent.md"] = b"rendered"', 'pass # outputs are no longer generated')
        self.assertFalse(any(f.predicate == 'generated_from' for f in build(files)[2].facts))

    def test_ast_verification_rejects_literals_and_fixture_reads(self):
        prefix = 'from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n'
        positive = prefix + 'def test_contract():\n    text = (ROOT / "agents/sre-assistant.md").read_text()\n    assert "tools:" in text\n'
        reads = rooted_reads(Source('scripts/test_contract.py', positive.encode()))
        self.assertEqual(['agents/sre-assistant.md'], [p for p, _ in reads])
        self.assertTrue(any(p.start_line == 2 for p in reads[0][1]))
        for body in (
            'note = "agents/sre-assistant.md"\n',
            '(ROOT / "agents/sre-assistant.md").write_text("fixture")\n',
            '(Path(tmp) / "agents/sre-assistant.md").read_text()\n',
            'open(ROOT / "agents/sre-assistant.md", "w+")\n',
            'ROOT = Path(tmp)\n    (ROOT / "agents/sre-assistant.md").read_text()\n',
        ):
            with self.subTest(body=body):
                text = prefix + 'def test_fixture(tmp):\n    ' + body
                self.assertEqual((), rooted_reads(Source('scripts/test_fixture.py', text.encode())))

    def test_ast_read_helper_binds_callsite_and_body(self):
        text = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def read_contract(relative):
    return (ROOT / relative).read_text()
def test_contract():
    assert read_contract("skills/a/SKILL.md")
'''
        reads = rooted_reads(Source('scripts/test_contract.py', text.encode()))
        self.assertEqual(['skills/a/SKILL.md'], [p for p, _ in reads])
        self.assertTrue(any(p.start_line <= 4 <= p.end_line for p in reads[0][1]))
        self.assertTrue(any(p.start_line <= 6 <= p.end_line for p in reads[0][1]))

    def test_function_local_repository_root_is_cited_and_reassignment_rejected(self):
        text = '''from pathlib import Path
def test_schema():
    root = Path(__file__).resolve().parents[1]
    assert (root / "schemas/example.schema.json").read_text()
'''
        reads = rooted_reads(Source('scripts/test_schema.py', text.encode()))
        self.assertEqual(['schemas/example.schema.json'], [path for path, _ in reads])
        self.assertTrue(any(p.start_line == 3 for p in reads[0][1]))
        changed = text.replace('    assert ', '    root = Path("fixture")\n    assert ')
        self.assertEqual((), rooted_reads(Source('scripts/test_schema.py', changed.encode())))

    def test_rooted_fixture_write_cannot_create_verification_evidence(self):
        text = '''from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_fixture():
    (ROOT / "agents/example.md").write_text("synthetic fixture")
    assert (ROOT / "agents/example.md").read_text()
'''
        self.assertEqual((), rooted_reads(Source('scripts/test_fixture.py', text.encode())))

    def test_fixture_helper_writes_cannot_create_verification_evidence(self):
        for functions, invocation in (
            ('def seed(path):\n    path.write_text("fixture")\n', 'seed(ROOT / "agents/example.md")'),
            ('def seed(text, path):\n    path.write_text(text)\n', 'seed("fixture", path=ROOT / "agents/example.md")'),
            ('def seed(path):\n    mutate(path)\ndef mutate(path):\n    path.write_bytes(b"fixture")\n', 'seed(ROOT / "agents/example.md")'),
        ):
            text = ('from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n' + functions
                    + 'def test_fixture():\n    ' + invocation
                    + '\n    assert (ROOT / "agents/example.md").read_text()\n')
            with self.subTest(invocation=invocation):
                self.assertEqual((), rooted_reads(Source('scripts/test_fixture.py', text.encode())))

    def test_shuffled_extractor_registration_is_byte_identical(self):
        from fleet_atlas_v2_extract import EXTRACTION_STAGES
        from fleet_atlas_v2_artifacts import render_files
        from fleet_atlas_v2_format import graph_dict
        from fleet_atlas_v2_model import canonical_bytes

        source = snapshot({
            'agents/sre-assistant.md': agent('sre-assistant'),
            'skills/alpha/SKILL.md': skill('alpha') + '\nBody-only dependency symptoms.\n',
            'AGENTS.md': '# Roster\n| Agent | Lane | Tools | Delegates to |\n|---|---|---|---|\n| `sre-assistant` | observe | read | — |\n',
            'docs/fleet-roadmap.md': '# Roadmap\n### GRAPH-004 current\n**Owner:** `sre-assistant` owns the `alpha` skill.\n**Evidence:** [choice](decisions/choice.md)\n',
            'docs/roadmap-closed.md': '# Closed\n| `GRAPH-004` | old | superseded entry |\n',
            'docs/decisions/choice.md': '# Decision\n**Status:** accepted\n',
            'schemas/catalog-v1.json': '{"schemas":[{"id":"choice","canonical_path":"docs/decisions/choice.md","status":"active","version":1}]}',
        })

        def materialize(registration):
            calls = []
            wrapped = []
            for stage in registration:
                def producer(current, inputs, stage=stage):
                    self.assertEqual(set(stage.requires), set(inputs))
                    self.assertTrue(set(inputs) <= set(calls))
                    with self.assertRaises(TypeError):
                        inputs['injected'] = None
                    result = stage.produce(current, inputs)
                    with self.assertRaises(dataclasses.FrozenInstanceError):
                        result.records = ()
                    calls.append(stage.name)
                    return result
                wrapped.append(dataclasses.replace(stage, produce=producer))
            result = extract(source, stages=tuple(wrapped))
            graph = assemble(result.buckets, result.predicates)
            checked = verify_facts(graph, source, result.predicates, result.evaluators)
            self.assertEqual(len(EXTRACTION_STAGES), len(calls))
            self.assertNotIn('owner:alpha', {node.id for node in graph.nodes})
            self.assertIn('capability:observe', {node.id for node in graph.nodes})
            self.assertEqual('live', next(f.object for f in graph.facts
                                         if f.subject == 'roadmap-item:GRAPH-004' and f.predicate == 'state'))
            self.assertTrue(any(f.predicate == 'owns' and f.object == 'skill:alpha' for f in graph.facts))
            return canonical_bytes(graph_dict(graph)), render_files(checked), calls

        expected = materialize(EXTRACTION_STAGES)
        self.assertIn('manifest.json', expected[1])
        self.assertIn('atlas.json', expected[1])
        registrations = [tuple(reversed(EXTRACTION_STAGES))]
        for seed in range(12):
            shuffled = list(EXTRACTION_STAGES)
            random.Random(seed).shuffle(shuffled)
            registrations.append(tuple(shuffled))
        for registration in registrations:
            with self.subTest(order=[stage.name for stage in registration]):
                self.assertEqual(expected, materialize(registration))

    def test_extraction_stage_dependencies_reject_missing_cycles_and_duplicates(self):
        from fleet_atlas_v2_extract import EXTRACTION_STAGES
        first = EXTRACTION_STAGES[0]
        for registration, message in (
            ((*EXTRACTION_STAGES, first), 'duplicate'),
            ((dataclasses.replace(first, requires=('absent',)),), 'missing'),
            ((dataclasses.replace(first, requires=(first.name,)),), 'cycle'),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                extract(snapshot({}), stages=registration)

    def test_replay_rejects_changed_value_class_proof_and_subject(self):
        source, result, graph = build({'skills/a/SKILL.md': skill('a'), 'skills/b/SKILL.md': skill('b')})
        original = next(f for f in graph.facts if f.subject == 'skill:a' and f.predicate == 'name')
        for mutation in (dataclasses.replace(original, object='forged'),
                         dataclasses.replace(original, subject='skill:b'),
                         dataclasses.replace(original, evidence_class=EvidenceClass.CONTRACT),
                         dataclasses.replace(original, proof=Proof(original.proof.kind, (source.source('skills/b/SKILL.md').span(1, 1),), original.proof.evaluator))):
            changed = dataclasses.replace(graph, facts=tuple(mutation if f.id == original.id else f for f in graph.facts))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify_facts(changed, source, result.predicates, result.evaluators)

    def test_staleness_applies_to_every_dated_live_status_as_unknown(self):
        for state in ('active', 'ready', 'blocked', 'decision-needed', 'deferred'):
            with self.subTest(state=state):
                _, _, graph = build({'docs/fleet-roadmap.md': f'# Roadmap\n### EVAL-003 test\n**Status:** `{state}` (2026-09-30)\n**Evidence:** [old](reviews/2026-01-01-old.md)\n',
                    'docs/reviews/2026-01-01-old.md': '# Old evidence\n'})
                self.assertTrue(any(f.predicate == 'unknown' and dict(f.qualifiers)['code'] == 'stale.evidence-predates-status' for f in graph.facts))

    def test_all_donor_vocabulary_is_declared(self):
        self.assertEqual(20, len(NODE_TYPES))
        self.assertEqual(15, len(EDGE_TYPES))
        self.assertIn('blocks', {p.name for p in extract(snapshot({})).predicates})

    def test_actual_field_proof_kinds_distinguish_computation_and_normalization(self):
        _, _, graph = build({'skills/a/SKILL.md': skill('a'),
            'docs/fleet-roadmap.md': '# Roadmap\n### GRAPH-004 title\n**Status:** `active` (2026-09-30)\n'})
        facts = {(f.subject, f.predicate): f for f in graph.facts}
        self.assertEqual(ProofKind.COMPUTED, facts['skill:a', 'attr.bytes'].proof.kind)
        self.assertEqual(ProofKind.COMPUTED, facts['skill:a', 'name'].proof.kind)
        self.assertEqual(ProofKind.COMPUTED, facts['skill:a', 'authority'].proof.kind)
        self.assertEqual(ProofKind.NORMALIZED, facts['roadmap-item:GRAPH-004', 'attr.status'].proof.kind)
        self.assertEqual(ProofKind.NORMALIZED, facts['skill:a', 'state'].proof.kind)

    def test_roadmap_state_cites_status_or_closure_and_rejects_missing_support(self):
        source, result, graph = build({
            'docs/fleet-roadmap.md': '# Roadmap\n### GRAPH-004 current\n\n**Status:** `active` (2026-09-30)\n**Outcome:** Find guidance.\n',
            'docs/roadmap-closed.md': '# Closed roadmap\n\n| Item | Closed | Disposition |\n| `GRAPH-003` | 2026-09-29 | Completed |\n',
        })
        for subject, path, state, evidence_class in (
            ('roadmap-item:GRAPH-004', 'docs/fleet-roadmap.md', 'live', EvidenceClass.CONTRACT),
            ('roadmap-item:GRAPH-003', 'docs/roadmap-closed.md', 'historical', EvidenceClass.EXTRACTED),
        ):
            with self.subTest(subject=subject):
                original = next(f for f in graph.facts if f.subject == subject and f.predicate == 'state')
                determining = source.source(path).span(4, 4)
                self.assertEqual(state, original.object)
                self.assertEqual(evidence_class, original.evidence_class)
                self.assertEqual(ProofKind.NORMALIZED, original.proof.kind)
                self.assertIn(determining, original.proof.inputs)
                omitted = tuple(p for p in original.proof.inputs if p != determining)
                irrelevant = (source.source(path).span(1, 1),)
                for inputs in (omitted, irrelevant):
                    with self.subTest(inputs=inputs):
                        if not inputs:
                            # A closure row is the sole witness: removing it is
                            # rejected at the immutable proof boundary itself.
                            with self.assertRaisesRegex(ValueError, 'nonempty'):
                                dataclasses.replace(original.proof, inputs=inputs)
                            continue
                        changed = dataclasses.replace(original,
                            proof=dataclasses.replace(original.proof, inputs=inputs))
                        candidate = dataclasses.replace(graph,
                            facts=tuple(changed if f.id == original.id else f for f in graph.facts))
                        with self.assertRaises(ValueError):
                            verify_facts(candidate, source, result.predicates, result.evaluators)

    def test_scenario_subset_matches_yaml_identity_and_ignores_prompt_fixture_tokens(self):
        text = '''id: real-case
target: {kind: agent, name: sre-assistant}
routing:
  expect: not_fire
  expected_alternative: {kind: skill, name: a}
threshold: 1.0
prompt: |
  target: {kind: agent, name: attacker}
fixture:
  files:
    false.yaml: |
      target: {kind: skill, name: attacker}
'''
        self.assertMatchesYaml(text)

    def test_block_scalar_chomping_and_indentation_headers_stay_prompt_text(self):
        headers = ('|', '|-', '|+', '>', '>-', '>+', '|2', '>1', '|+2', '|-1',
                   '|2+', '|1-', '>+2', '>2+', '>2-', '>-2')
        properties = ('', '&prompt ', '!!str ', '&prompt !!str ', '!!str &prompt ')
        for header in headers:
            for prefix in properties:
                for comment in ('', '  # target: attacker'):
                    value = prefix + header + comment
                    with self.subTest(header=value):
                        text = ('id: case\ntarget: {kind: agent, name: sre-assistant}\n'
                                'routing: {expect: fire}\n'
                                f'prompt: {value}\n'
                                '  target: {kind: agent, name: attacker}\n'
                                '  routing: {expect: not_fire}\nthreshold: 1.0\n')
                        expected, _ = self.assertMatchesYaml(text)
                        self.assertIsInstance(expected['prompt'], str)

    def test_scalar_properties_on_separate_lines_cannot_inject_metadata(self):
        for properties in ('&prompt', '!!str', '&prompt !!str', '!!str &prompt'):
            with self.subTest(properties=properties):
                text = ('id: case\ntarget: {kind: agent, name: sre-assistant}\n'
                        'routing: {expect: fire}\n'
                        f'prompt: {properties}  # properties precede the header\n'
                        '  |+ # scalar header is on its own line\n'
                        '    target: {kind: agent, name: attacker}\n'
                        '    routing: {expect: not_fire}\nthreshold: 1.0\n')
                self.assertMatchesYaml(text)

    def test_multiline_quoted_and_flow_values_cannot_inject_metadata(self):
        values = (
            '\"hello\ntarget: {kind: agent, name: attacker}\n\"',
            "'hello\ntarget: {kind: agent, name: attacker}\n'",
            '\"hello \\\"quoted\\\"\ntarget: {kind: agent, name: attacker}\n\"',
            "'hello ''quoted''\ntarget: {kind: agent, name: attacker}\n'",
            '&prompt \"hello\ntarget: {kind: agent, name: attacker}\n\"',
            '\n  \"hello\ntarget: {kind: agent, name: attacker}\n\"',
            '[hello,\ntarget: {kind: agent, name: attacker}\n]',
            '[\"text with ] and }\ntarget: attacker\", # comment\nhello]',
            "[don't,\ntarget: {kind: agent, name: attacker}\n]",
            '[!!str \"hello]\ntarget: {kind: agent, name: attacker}\n\"]',
            '[&prompt\n\"hello]\ntarget: {kind: agent, name: attacker}\n\"]',
            '{message: !!str \"hello}\ntarget: {kind: agent, name: attacker}\n\"}',
            '{message: hello,\ntarget: {kind: agent, name: attacker}\n}',
        )
        for value in values:
            with self.subTest(value=value):
                text = ('id: case\ntarget: {kind: agent, name: sre-assistant}\n'
                        f'prompt: {value}\nrouting: {{expect: fire}}\nthreshold: 1.0\n')
                self.assertMatchesYaml(text)

    def test_next_line_block_scalar_is_not_a_target_mapping(self):
        for properties in ('', '&target ', '!!str '):
            with self.subTest(properties=properties):
                text = ('id: case\ntarget:\n'
                        f'  {properties}|+ # value is a scalar\n'
                        '    kind: agent\n    name: attacker\n'
                        'routing: {expect: not_fire}\nthreshold: 1.0\n')
                expected, parsed = self.assertMatchesYaml(text, ('id', 'routing', 'threshold'))
                self.assertIsInstance(expected['target'], str)
                self.assertNotIn('target', parsed, 'block scalar content is outside the metadata subset')

    def test_flow_node_properties_preserve_multiline_quote_boundaries(self):
        from itertools import product
        properties = ('&prompt', '!!str', '!', '!<tag:yaml.org,2002:str>',
                      '&prompt !!str', '!!str &prompt')
        for prop, quote, separator, opener in product(properties, ('\"', "'"),
                                                      (' ', '\n'), ('[', '{message: ')):
            with self.subTest(property=prop, quote=quote, separator=separator, opener=opener):
                closer = ']' if opener == '[' else '}'
                value = (f'{opener}{prop}{separator}{quote}hello{closer}\n'
                         f'target: {{kind: agent, name: attacker}}\n{quote}{closer}')
                text = ('id: case\ntarget: {kind: agent, name: sre-assistant}\n'
                        f'prompt: {value}\nrouting: {{expect: fire}}\nthreshold: 1.0\n')
                self.assertMatchesYaml(text)

    def test_unterminated_or_mismatched_flow_scalars_fail_closed(self):
        for value in ('\"hello', "'hello", '[hello', '{message: hello',
                      '[hello}', '\"hello\" unexpected'):
            with self.subTest(value=value):
                text = f'prompt: {value}\ntarget: {{kind: agent, name: attacker}}\n'
                with self.assertRaises(ValueError):
                    scenario_fields(Source('evals/scenarios/case.yaml', text.encode()))

    def test_unsupported_explicit_flow_keys_fail_closed(self):
        import yaml  # Independent test oracle; the installed atlas runtime stays stdlib-only.
        for property_prefix in ('', '!!str '):
            with self.subTest(property_prefix=property_prefix):
                value = (f'{{? {property_prefix}\"hello: x}}\n'
                         'target: {kind: agent, name: attacker}\n\": scalar}')
                text = ('id: case\ntarget: {kind: agent, name: sre-assistant}\n'
                        f'prompt: {value}\n')
                self.assertEqual(yaml.safe_load(text)['target']['name'], 'sre-assistant')
                with self.assertRaises(ValueError):
                    scenario_fields(Source('evals/scenarios/case.yaml', text.encode()))

    def test_body_only_symptom_guidance_preserves_every_chunk_with_exact_spans(self):
        body = skill('a') + '## Ledger delays\n\nDependency timeouts can hold the shared pool.\n\n' + ('A longer evidence paragraph. ' * 500) + '\n'
        _, _, graph = build({'skills/a/SKILL.md': body})
        guidance = [f for f in graph.facts if f.predicate == 'guidance']
        self.assertTrue(any('Dependency timeouts' in f.object for f in guidance))
        self.assertTrue(all(len(f.object.encode()) <= 3000 for f in guidance))
        for fact in guidance:
            self.assertTrue(fact.proof.inputs)
        self.assertIn('A longer evidence paragraph.', '\n'.join(f.object for f in guidance))
        final_line = len(body.splitlines())
        long_paragraph = sorted((f for f in guidance if any(p.start_line == p.end_line == final_line for p in f.proof.inputs)),
                                key=lambda f: dict(f.qualifiers)['start_offset'])
        self.assertEqual(body.splitlines()[-1], ''.join(f.object for f in long_paragraph))


if __name__ == '__main__':
    unittest.main()
