"""CLI outcomes and source-bound navigation through the real artifact verifier."""

from contextlib import redirect_stdout
import io
import json
import unittest
from types import SimpleNamespace
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys

import fleet_atlas_v2 as cli
import test_fleet_atlas_v2_artifacts as fixtures
from fleet_atlas_v2_model import Bucket, EvidenceClass, Fact, Node, Predicate, Proof, ProofKind
from fleet_atlas_v2_proofs import Derivation
from fleet_atlas_v2_sources import current_snapshot


class CliTests(unittest.TestCase):
    setUp = fixtures.ArtifactTests.setUp
    git = fixtures.ArtifactTests.git
    output = fixtures.ArtifactTests.output

    def call(self, *args, loader=fixtures.fixture_extract):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = cli.main(["--root", str(self.root), *args], loader)
        content = stdout.getvalue().encode("utf-8")
        return code, json.loads(content), content

    def test_missing_atlas_and_usage_are_distinct_enveloped_failures(self):
        code, record, _ = self.call("check")
        self.assertEqual(1, code)
        self.assertEqual("unverified", record["outcome"])
        for args in (("query", "unsupported", "x"), ("query", "state", "one", "two"), ("query", "state")):
            code, record, _ = self.call(*args)
            self.assertEqual(2, code)
            self.assertEqual("usage", record["outcome"])

    def test_cli_results_carry_evidence_labels(self):
        self.assertEqual(0, self.call("build")[0])
        code, data, content = self.call("query", "state", "README.md")
        self.assertEqual(0, code)
        self.assertEqual("results", data["outcome"])
        self.assertEqual("verified", data["results"][0]["label"])
        self.assertEqual("README.md", data["results"][0]["citations"][0]["path"])
        self.assertEqual(len(content), data["encodedBytes"])

    def test_verified_empty_is_success_with_explicit_scope(self):
        self.call("build")
        code, data, _ = self.call("query", "owner-of", "no-such-capability")
        self.assertEqual(0, code)
        self.assertEqual("empty", data["outcome"])
        self.assertEqual(0, data["count"])
        self.assertIn("not proof", data["scope"])

    def test_query_rejects_drift_using_same_verifier_as_check(self):
        self.call("build")
        self.output("INDEX.md").write_bytes(b"forged")
        for args in (("check",), ("query", "state", "README.md")):
            code, data, _ = self.call(*args)
            self.assertEqual(1, code)
            self.assertEqual("drift", data["outcome"])
            self.assertEqual([], data["results"])

    def test_full_output_requires_explicit_flag_and_exposes_proofs(self):
        self.call("build")
        code, data, _ = self.call("query", "state", "README.md", "--full")
        self.assertEqual(0, code)
        self.assertIsNone(data["budgetBytes"])
        self.assertIn("proof", data["results"][0]["fullFact"])

    def test_query_rejects_duck_typed_container_without_artifact_verification(self):
        self.call("build")
        document = cli.verify(self.root, fixtures.fixture_extract)
        loose = SimpleNamespace(facts=document.facts, revision=document.revision)
        with self.assertRaisesRegex(TypeError, "VerifiedDocument"):
            cli.query(loose, "state", ["README.md"])

    def test_recorded_unknown_is_not_reported_as_verified_empty(self):
        def loader(snapshot):
            base = fixtures.fixture_extract(snapshot)
            proof = Proof(ProofKind.ABSENCE, (snapshot.source("README.md").span(1, 1),),
                          "missing-owner/v1", snapshot.tree_digest)
            fact = Fact("unknown:owner", "document:README.md", "unknown", "Owner is not recorded",
                        EvidenceClass.UNKNOWN, proof)

            def evaluate(candidate, sources, premises):
                source = sources.source("README.md")
                value = "Owner is recorded" if "Owner:" in source.text else "Owner is not recorded"
                return Derivation(value, EvidenceClass.UNKNOWN,
                                  Proof(ProofKind.ABSENCE, (source.span(1, 1),),
                                        "missing-owner/v1", sources.tree_digest))

            return SimpleNamespace(
                buckets=(*base.buckets, Bucket("unknown", (), (fact,))),
                predicates=(*base.predicates, Predicate("unknown", frozenset({"document"}), None, ("README.md",))),
                evaluators={**base.evaluators, "missing-owner/v1": evaluate})

        self.assertEqual(0, self.call("build", loader=loader)[0])
        code, data, _ = self.call("query", "owner-of", "README.md", loader=loader)
        self.assertEqual(1, code)
        self.assertEqual("unverified", data["outcome"])
        self.assertEqual("unverified", data["results"][0]["label"])

    def test_guidance_snippet_survives_oversized_matching_metadata(self):
        (self.root / "README.md").write_bytes(
            b"live\nCheck dependency timeouts at the caller boundary.\n"
            + b"dependency timeouts metadata " + b"x" * 25_000 + b"\n")
        self.git("add", "README.md")
        self.git("commit", "-qm", "guidance and crowded metadata")

        def loader(snapshot):
            base = fixtures.fixture_extract(snapshot)
            source = snapshot.source("README.md")
            claims = (("a-description", "attr.description", 3), ("z-guidance", "guidance", 2))
            facts = tuple(Fact(identity, "document:README.md", predicate, source.lines[line - 1],
                               EvidenceClass.EXTRACTED, Proof(ProofKind.EXTRACTED,
                               (source.span(line, line),), "guidance-fixture/v1"))
                          for identity, predicate, line in claims)

            def evaluate(candidate, sources, premises):
                current = sources.source("README.md")
                line = 2 if candidate.predicate == "guidance" else 3
                return Derivation(current.lines[line - 1], EvidenceClass.EXTRACTED,
                                  Proof(ProofKind.EXTRACTED, (current.span(line, line),), "guidance-fixture/v1"))

            return SimpleNamespace(
                buckets=(*base.buckets, Bucket("guidance", (), facts)),
                predicates=(*base.predicates, *(Predicate(predicate, frozenset({"document"}), None,
                             ("README.md",)) for _, predicate, _ in claims)),
                evaluators={**base.evaluators, "guidance-fixture/v1": evaluate})

        self.assertEqual(0, self.call("build", loader=loader)[0])
        code, data, content = self.call("query", "guidance", "dependency", "timeouts", loader=loader)
        self.assertEqual(0, code)
        self.assertTrue(data["truncated"])
        self.assertLessEqual(len(content), 20_000)
        self.assertEqual("guidance", data["results"][0]["predicate"])
        self.assertIn("caller boundary", data["results"][0]["object"])

    def test_supersedes_query_matches_both_old_and_new_decisions(self):
        def loader(snapshot):
            base = fixtures.fixture_extract(snapshot)
            nodes = (Node("decision:new", "decision", "README.md", "new"),
                     Node("decision:old", "decision", "README.md", "old"))
            proof = Proof(ProofKind.EXTRACTED, (snapshot.source("README.md").span(1, 1),), "supersedes-fixture/v1")
            fact = Fact("edge:new:old", "decision:new", "supersedes", "decision:old", EvidenceClass.EXTRACTED, proof)
            return SimpleNamespace(
                buckets=(*base.buckets, Bucket("decisions", nodes, (fact,))),
                predicates=(*base.predicates, Predicate("supersedes", frozenset({"decision"}),
                             frozenset({"decision"}), ("README.md",))),
                evaluators={**base.evaluators, "supersedes-fixture/v1": lambda f, s, p:
                            Derivation("decision:old", EvidenceClass.EXTRACTED, proof)})

        self.assertEqual(0, self.call("build", loader=loader)[0])
        for name in ("new", "old"):
            with self.subTest(name=name):
                code, data, _ = self.call("query", "supersedes", name, loader=loader)
                self.assertEqual(0, code)
                self.assertEqual("results", data["outcome"])
                self.assertEqual("decision:new", data["results"][0]["subject"])
                self.assertEqual("decision:old", data["results"][0]["object"])


class RealCliFailureTests(unittest.TestCase):
    def test_malformed_tracked_test_returns_envelope_for_all_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            runtime = Path(__file__).resolve().parent
            for path in [*runtime.glob("fleet_atlas_v2*.py"), runtime / "fleet_frontmatter.py"]:
                shutil.copyfile(path, scripts / path.name)
            (root / "README.md").write_bytes(b"# Runtime error fixture\n")

            def git(*args):
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)

            def command(*args):
                return subprocess.run([sys.executable, "-I", "-S", str(scripts / "fleet_atlas_v2.py"),
                                       "--root", str(root), *args], capture_output=True, check=False)

            git("init", "-q")
            git("config", "user.name", "Atlas malformed fixture")
            git("config", "user.email", "atlas@example.invalid")
            git("config", "core.autocrlf", "false")
            git("add", ".")
            git("commit", "-qm", "clean fixture")
            initial = command("build")
            self.assertEqual(0, initial.returncode, initial.stderr.decode())
            (scripts / "test_bad.py").write_bytes(b"def broken(\n")
            git("add", "scripts/test_bad.py")
            git("commit", "-qm", "malformed tracked test")
            # An untrusted stored atlas can claim fresh metadata. check/query must
            # still envelope the parser failure rather than leak a traceback.
            snapshot = current_snapshot(root)
            atlas = root / "docs/fleet-atlas/v2/atlas.json"
            document = json.loads(atlas.read_bytes())
            document["metadata"].update(revision=snapshot.revision, treeDigest=snapshot.tree_digest)
            atlas.write_text(json.dumps(document), encoding="utf-8")
            for args in (("build",), ("check",), ("query", "state", "README.md")):
                with self.subTest(command=args[0]):
                    result = command(*args)
                    self.assertEqual(1, result.returncode)
                    self.assertNotIn(b"Traceback", result.stderr)
                    envelope = json.loads(result.stdout)
                    self.assertEqual("unverified", envelope["outcome"])
                    self.assertEqual([], envelope["results"])


if __name__ == "__main__":
    unittest.main()
