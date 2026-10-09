"""Source-corpus and source-location regressions independent of atlas extraction."""

import unittest

from atlas_test_support import ReadmeRepository
from fleet_atlas_v2_model import Span
from fleet_atlas_v2_sources import (
    Snapshot,
    Source,
    current_snapshot,
    is_source,
    read_revision,
    verify_revision,
)


class SourceTests(unittest.TestCase):
    def test_locator_raises_when_needle_absent(self):
        source = Source("docs/fleet-roadmap.md", b"first\nsecond\nsecond\n")
        self.assertEqual([2, 3], [span.start_line for span in source.locate("second")])
        with self.assertRaisesRegex(ValueError, "needle absent"):
            source.locate("not present")

    def test_canonical_digest_covers_github_and_platforms(self):
        for path in (".github/agents/a.md", "platforms/copilot/skills/a/SKILL.md",
                     "com.github.copilot/a.md"):
            self.assertTrue(is_source(path))
            one = Snapshot("revision", (Source(path, b"one"),))
            two = Snapshot("revision", (Source(path, b"two"),))
            self.assertNotEqual(one.tree_digest, two.tree_digest)
        self.assertFalse(is_source("docs/fleet-atlas/v2/atlas.json"))
        self.assertFalse(is_source("docs/fleet-atlas/generated/atlas.json"))
        self.assertFalse(is_source(".eval-runs/private.txt"))

    def test_root_dependency_contract_sources_remain_in_corpus(self):
        self.assertTrue(is_source("requirements-dev.txt"))
        self.assertTrue(is_source("requirements-test.txt"))
        self.assertTrue(is_source("pyproject.toml"))

    def test_snapshot_rejects_duplicate_and_unsorted_paths(self):
        source = Source("a.md", b"a")
        with self.assertRaises(ValueError):
            Snapshot("revision", (source, source))
        with self.assertRaises(ValueError):
            Snapshot("revision", (Source("z.md", b"z"), source))

    def test_cached_decoded_views_never_enter_source_identity(self):
        warm, cold = Source("README.md", b"one\ntwo\n"), Source("README.md", b"one\ntwo\n")
        self.assertEqual(("one", "two"), warm.lines)
        self.assertEqual(Span.from_bytes("README.md", b"one\ntwo\n", 2, 2), warm.span(2, 2))
        self.assertEqual((warm, hash(warm)), (cold, hash(cold)))
        self.assertEqual(Snapshot("revision", (warm,)), Snapshot("revision", (cold,)))
        self.assertEqual(Snapshot("revision", (warm,)).tree_digest, Snapshot("revision", (cold,)).tree_digest)
        with self.assertRaisesRegex(ValueError, "outside closed corpus"):
            Snapshot("revision", (warm,)).source("missing.md")

    def test_changed_blob_outside_excerpt_is_rejected(self):
        span = Span.from_bytes("README.md", b"title\nfact\n", 2, 2)
        snapshot = Snapshot("revision", (Source("README.md", b"changed title\nfact\n"),))
        with self.assertRaisesRegex(ValueError, "differs"):
            snapshot.verify_span(span)


class GitSourceTests(ReadmeRepository, unittest.TestCase):
    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))

    def commit(self, message):
        self.git("add", ".")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_tracked_only_and_no_generated_feedback(self):
        snapshot = current_snapshot(self.root)
        self.write("history-not-in-corpus/untracked.txt", "outside corpus may stay untracked\n")
        self.assertEqual(snapshot, current_snapshot(self.root))
        self.write("docs/fleet-atlas/v2/atlas.json", "{}\n")
        self.assertEqual(snapshot, current_snapshot(self.root),
                         "generated atlas output stays outside the corpus even untracked")
        self.git("add", "docs/fleet-atlas/v2/atlas.json")
        self.git("commit", "-qm", "generated only")
        current = current_snapshot(self.root)
        self.assertEqual(snapshot.tree_digest, current.tree_digest)
        verify_revision(self.root, snapshot.revision, current)

    def test_untracked_canonical_input_fails_closed(self):
        self.write("skills/untracked/SKILL.md", "untracked must not verify\n")
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            current_snapshot(self.root)
        self.git("add", "skills/untracked/SKILL.md")
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            current_snapshot(self.root)
        self.commit("add skill")
        current_snapshot(self.root)

    def test_dirty_staged_deleted_and_renamed_inputs_fail_closed(self):
        self.write("README.md", "changed\n")
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            current_snapshot(self.root)
        self.git("add", "README.md")
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            current_snapshot(self.root)
        self.git("reset", "--hard", "-q", "HEAD")
        (self.root / "README.md").unlink()
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            current_snapshot(self.root)
        self.git("reset", "--hard", "-q", "HEAD")
        self.git("mv", "README.md", "outside-corpus.txt")
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            current_snapshot(self.root)

    def test_reachable_non_ancestor_revision_with_differing_inputs_is_rejected(self):
        initial = current_snapshot(self.root).revision
        self.git("checkout", "-qb", "other")
        self.write("README.md", "other content\n")
        other = self.commit("other")
        self.git("checkout", "--detach", "-q", initial)
        self.write("README.md", "main content\n")
        self.commit("main")
        with self.assertRaisesRegex(ValueError, "different canonical"):
            verify_revision(self.root, other, current_snapshot(self.root))

    def test_git_object_bytes_do_not_depend_on_checkout_newlines(self):
        original = current_snapshot(self.root)
        self.git("config", "core.autocrlf", "true")
        self.write("README.md", "live\r\n")
        self.assertEqual(original, current_snapshot(self.root))
        self.assertEqual(b"live\n", read_revision(self.root, "HEAD").source("README.md").content)

    def test_same_corpus_accepts_divergent_rebased_and_merged_history(self):
        initial = current_snapshot(self.root)
        self.git("checkout", "-qb", "topic")
        self.write("history-not-in-corpus/topic.txt", "topic\n")
        topic = self.commit("topic outside atlas corpus")
        self.git("checkout", "-qb", "integration", initial.revision)
        self.write("history-not-in-corpus/integration.txt", "integration\n")
        integration = self.commit("integration outside atlas corpus")
        current = current_snapshot(self.root)
        self.assertEqual(initial.tree_digest, current.tree_digest)
        verify_revision(self.root, topic, current)
        self.git("checkout", "-q", "topic")
        self.git("rebase", "integration")
        rebased = current_snapshot(self.root)
        self.assertNotEqual(topic, rebased.revision)
        self.assertEqual(initial.tree_digest, rebased.tree_digest)
        verify_revision(self.root, topic, rebased)
        self.git("checkout", "-qb", "merge-side", initial.revision)
        self.write("history-not-in-corpus/side.txt", "side\n")
        self.commit("merge side outside atlas corpus")
        self.git("checkout", "-q", "topic")
        self.git("merge", "--no-ff", "--no-edit", "merge-side")
        merged = current_snapshot(self.root)
        self.assertEqual(3, len(self.git("rev-list", "--parents", "-n", "1", "HEAD").split()))
        self.assertEqual(initial.tree_digest, merged.tree_digest)
        for recorded in (initial.revision, topic, integration, rebased.revision):
            with self.subTest(recorded=recorded):
                verify_revision(self.root, recorded, merged)


if __name__ == "__main__":
    unittest.main()
