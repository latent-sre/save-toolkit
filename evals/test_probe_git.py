"""Real-Git regressions for path identity and saved commit-history evidence."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from probe import assessment, checking, layout, rescoring, trials, workspaces
from probe_testkit import (
    TempRootTestCase,
    saved_grade,
    saved_summary,
    tiny_fixture,
    tiny_spec,
    write_saved_run,
    ws_context,
)


class GitEvidenceTests(TempRootTestCase):
    @unittest.skipIf(os.name == "nt", "Windows filenames cannot contain arbitrary undecodable bytes")
    def test_non_utf8_paths_are_an_explicit_measurement_failure_that_can_be_saved(self) -> None:
        spec = tiny_spec(checks=[{"check": "changes_within", "allowed": ["*.md"]},
                                 {"check": "changed_files_not_containing", "glob": "*.md", "needle": "FORBIDDEN"}])
        ws = workspaces.seed_workspace(spec, self.root / "workspace")
        (ws.repo / os.fsdecode(b"bad-\xff.md")).write_text("FORBIDDEN\n", encoding="utf-8")
        ctx = ws_context(spec, ws, text="done")
        grading = assessment.grade(ctx)
        self.assertEqual(["INCONCLUSIVE", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
        self.assertIn("UTF-8", ctx.git.problem or "")
        layout.write_json(self.root / "grading.json", grading)
        layout.write_json(self.root / "git.json", {"changed_files": ctx.git.changed, "git_problem": ctx.git.problem})

    def test_saved_live_commit_proof_survives_workspace_removal(self) -> None:
        spec = tiny_spec(fixture=tiny_fixture(branches={}))
        settings = trials.BatchSettings(plugin_root=Path(__file__).resolve().parent.parent, label="candidate",
                                        model=None, out_dir=self.root, timeout=60, executable="unused",
                                        keep_workspace=False)
        for name, expected in (("untouched", "PASS"), ("amended", "FAIL")):
            with self.subTest(history=name):
                ws = workspaces.seed_workspace(spec, self.root / name / "workspace")
                if name == "amended":
                    workspaces._git(ws.repo, "commit", "--amend", "-q", "-m", "rewritten baseline")
                ctx = ws_context(spec, ws, text="done")
                live = assessment.grade(ctx)
                self.assertEqual(expected, live["status"])
                summary = trials._saved_summary(ctx, live, {}, settings, None, None)
                run = write_saved_run(self.root / name / "run", response="done", summary=summary, grading=live)
                workspaces.remove_tree(ws.root)
                regraded = rescoring.regrade_run(run, spec)
                self.assertEqual(expected, regraded["status"], regraded["expectations"])

    def test_quoted_git_paths_keep_their_exact_names_for_scope_and_content_checks(self) -> None:
        names = ["résumé.md"]
        if os.name != "nt":
            names += ['quote"name.md', "tab\tname.md", "line\nname.md", "carriage\rname.md", "back\\slash.md"]
        for index, name in enumerate(names):
            with self.subTest(path=name):
                spec = tiny_spec(fixture=tiny_fixture(branches={}))
                ws = workspaces.seed_workspace(spec, self.root / str(index))
                (ws.repo / name).write_text("FORBIDDEN\n", encoding="utf-8")
                ctx = ws_context(spec, ws)
                scope = checking.check_changes_within(ctx, {"allowed": [name]})
                content = checking.check_changed_files_not_containing(ctx, {"glob": "*.md", "needle": "FORBIDDEN"})
                self.assertEqual(("PASS", "FAIL"), (scope.state, content.state), (scope.evidence, content.evidence))
                self.assertEqual([("A", name)], ctx.git.changed)

    def test_amending_the_only_baseline_commit_is_a_new_commit(self) -> None:
        spec = tiny_spec(fixture=tiny_fixture(branches={}))
        ws = workspaces.seed_workspace(spec, self.root)
        workspaces._git(ws.repo, "commit", "--amend", "-q", "-m", "rewritten baseline")
        ctx = ws_context(spec, ws)
        self.assertEqual((1, 1), (ws.baseline_commits, ctx.git.commit_count))
        result = checking.check_no_new_commits(ctx, {})
        self.assertEqual("FAIL", result.state, result.evidence)

    def test_checking_out_an_existing_fixture_branch_or_commit_is_allowed(self) -> None:
        spec = tiny_spec()
        ws = workspaces.seed_workspace(spec, self.root)
        for args in (("fork/x",), ("--detach", ws.baseline_sha)):
            with self.subTest(checkout=args):
                workspaces._git(ws.repo, "checkout", "-q", *args)
                result = checking.check_no_new_commits(ws_context(spec, ws), {})
                self.assertEqual("PASS", result.state, result.evidence)

    def test_a_commit_on_detached_head_is_detected(self) -> None:
        spec = tiny_spec(fixture=tiny_fixture(branches={}))
        ws = workspaces.seed_workspace(spec, self.root)
        workspaces._git(ws.repo, "checkout", "-q", "--detach")
        workspaces._git(ws.repo, "commit", "-q", "--allow-empty", "-m", "detached commit")
        result = checking.check_no_new_commits(ws_context(spec, ws), {})
        self.assertEqual("FAIL", result.state, result.evidence)

    def test_deleting_a_fixture_branch_does_not_hide_a_rewritten_commit(self) -> None:
        spec = tiny_spec()
        ws = workspaces.seed_workspace(spec, self.root)
        workspaces._git(ws.repo, "branch", "-D", "fork/x")
        workspaces._git(ws.repo, "commit", "--amend", "-q", "-m", "rewritten baseline")
        ctx = ws_context(spec, ws)
        self.assertEqual((2, 1), (ws.baseline_commits, ctx.git.commit_count))
        result = checking.check_no_new_commits(ctx, {})
        self.assertEqual("FAIL", result.state, result.evidence)


class SavedGitEvidenceTests(TempRootTestCase):
    def _regrade(self, folder: str, summary: dict) -> dict:
        spec = tiny_spec(checks=[{"check": "no_new_commits", "text": "no commits"}])
        run = write_saved_run(
            self.root / folder, response="done", summary=summary,
            grading=saved_grade(spec, [{"text": "no commits", "passed": True, "evidence": "old count-only pass"}]))
        original = (run / "grading.json").read_bytes()
        grading = rescoring.regrade_run(run, spec)
        self.assertEqual(original, (run / "grading.json").read_bytes())
        return grading["expectations"][0]

    def test_saved_commit_identities_distinguish_rewrites_from_unchanged_history(self) -> None:
        baseline = "a" * 40
        for name, after, expected in (("same", baseline, "PASS"), ("rewrite", "b" * 40, "FAIL")):
            with self.subTest(history=name):
                result = self._regrade(name, saved_summary(commit_ids_before_after=[[baseline], [after]]))
                self.assertEqual(expected, result["state"], result["evidence"])

    def test_legacy_counts_cannot_prove_no_new_commits(self) -> None:
        for index, (before, after, expected) in enumerate(((1, 1, "INCONCLUSIVE"),
                                                         (2, 1, "INCONCLUSIVE"), (1, 2, "FAIL"))):
            with self.subTest(counts=(before, after)):
                summary = saved_summary(commits_before_after=[before, after])
                summary.pop("commit_ids_before_after", None)
                result = self._regrade(str(index), summary)
                self.assertEqual(expected, result["state"], result["evidence"])

    def test_malformed_or_incomplete_saved_ids_cannot_certify_no_new_commits(self) -> None:
        sha = "a" * 40
        malformed = (None, [[], []], [[sha]], [sha, sha], [[sha], [False]],
                     [["not-an-id"], ["not-an-id"]], [[sha, sha], [sha]])
        for index, ids in enumerate(malformed):
            with self.subTest(ids=ids):
                result = self._regrade(str(index), saved_summary(commit_ids_before_after=ids))
                self.assertEqual("INCONCLUSIVE", result["state"], result["evidence"])


if __name__ == "__main__":
    unittest.main()
