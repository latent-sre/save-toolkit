"""Contract tests for scripts/check_stale_names.py.

This checker had no test. It runs in Gate A only against the real tree, where it currently matches
nothing — so if STALE_RE, the word-boundary logic, or the path/`.md` carve-outs silently broke, the
checker would still print PASS and Gate A would stay green. That is this repo's own documented
failure mode ("a rule that asserts nothing"). These tests feed it known-bad and known-good input so
a future refactor that neuters it fails loudly instead.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_stale_names


class StaleNamesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="stale-names-")
        self.root = Path(self._tmp.name)
        (self.root / "skills").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def _a_stale_name(self) -> str:
        # Pick a retired name that is NOT an ordinary English word, so the assertion is about the
        # guard firing, not about a carve-out. `sre-tool` is a retired unit name in STALE.
        assert "sre-tool" in check_stale_names.STALE
        return "sre-tool"

    def test_the_real_repo_is_clean(self) -> None:
        # Anchors the suite: if the live tree ever trips the checker, every test below is suspect.
        self.assertEqual([], check_stale_names.check(check_stale_names.ROOT))

    def test_a_seeded_retired_name_in_prose_is_caught(self) -> None:
        self._write("skills/probe/SKILL.md", f"Route it to the {self._a_stale_name()} skill.\n")
        failures = check_stale_names.check(self.root)
        self.assertTrue(
            any("stale fleet-unit name" in f and self._a_stale_name() in f for f in failures),
            failures,
        )

    def test_retired_builder_agent_name_is_caught(self) -> None:
        old_name = "s" + "de"
        self.assertIn(old_name, check_stale_names.STALE)
        self._write("skills/probe/SKILL.md", f"Route implementation to `{old_name}`.\n")
        failures = check_stale_names.check(self.root)
        self.assertTrue(any(old_name in failure for failure in failures), failures)

    def test_purged_sister_fleet_name_is_caught_in_non_markdown_plugin_source(self) -> None:
        retired = "sde-agents"
        self._write("skills/probe/helper.py", f'LEGACY_PLUGIN = "{retired}"\n')

        failures = check_stale_names.check(self.root)

        self.assertTrue(
            any("helper.py" in failure and retired in failure for failure in failures),
            failures,
        )

        self._write("skills/probe/helper.py", 'LEGACY_PLUGIN = "sde-agents-helper"\n')
        self.assertEqual([], check_stale_names.check(self.root))

    def test_sde_agents_is_caught_by_the_standalone_checker(self) -> None:
        retired_fleet = "sde-agents"
        self._write(
            "skills/probe/SKILL.md",
            f"Do not copy the {retired_fleet} roster.\n",
        )
        failures = check_stale_names.check(self.root)
        self.assertTrue(
            any(retired_fleet in failure for failure in failures),
            failures,
        )

    def test_clean_prose_is_silent(self) -> None:
        self._write("skills/probe/SKILL.md", "Route it to the reviewer agent.\n")
        self.assertEqual([], check_stale_names.check(self.root))

    def test_sre_ladder_stays_retired(self) -> None:
        self.assertIn(
            "sre-ladder",
            check_stale_names.STALE,
            "the incident-mode router is `investigation-depth`; `sre-ladder` stays retired",
        )

    def test_a_path_or_md_reference_is_exempt(self) -> None:
        # The carve-out that keeps a reintroduced name usable as a real filename: a match adjacent to
        # `/` or immediately followed by `.md` is skipped *when a file of that name exists in the
        # scanned tree*. `api-design` is a retired unit name that now also ships as api-design.md,
        # so the link form must NOT trip the guard -- but only because the file is really there.
        # Writing it is what earns the exemption; see
        # test_a_retired_name_with_no_live_file_is_caught_in_path_and_md_form for the other half.
        stale_file_token = "api-design"
        self.assertIn(stale_file_token, check_stale_names.STALE)
        self._write(f"skills/probe/references/{stale_file_token}.md", "# API surface design\n")
        self._write(
            "skills/probe/SKILL.md",
            f"See [API surface design](references/{stale_file_token}.md) and "
            f"`references/{stale_file_token}.md`.\n",
        )
        self.assertEqual([], check_stale_names.check(self.root))

    def test_a_retired_name_with_no_live_file_is_caught_in_path_and_md_form(self) -> None:
        """The carve-out must exempt real filenames, not every retired unit.

        `_hits` skipped any match adjacent to `/` or followed by `.md`, so a live handoff naming
        `agents/prompt-engineer.md` -- the exact artifact the rename retired -- passed Gate A. The
        exemption is meant for retired unit names that survive as real files (`api-design.md`), so
        it is granted per name, on evidence that such a file exists in the scanned tree.
        """

        retired = "prompt-engineer"
        self.assertIn(retired, check_stale_names.STALE)
        self.assertFalse(
            (check_stale_names.ROOT / "agents" / f"{retired}.md").is_file(),
            "the retired agent file must not exist for this test to mean anything",
        )
        for form in (f"see agents/{retired}.md", f"see {retired}.md", f"handoff to {retired}/"):
            with self.subTest(form=form):
                self._write("skills/probe/SKILL.md", form + "\n")
                failures = check_stale_names.check(self.root)
                self.assertEqual(1, len(failures), f"{form!r} evaded the checker: {failures}")
                self.assertIn(retired, failures[0])

    def test_a_sibling_repository_url_stays_writable(self) -> None:
        # The `/` carve-out exists for this repository's retired plugin name in a path.
        self._write(
            "skills/probe/SKILL.md",
            "See https://github.com/latent-sre/sre-agents and latent-sre/sre-agents.\n",
        )
        self.assertEqual([], check_stale_names.check(self.root))

    def test_the_same_reintroduced_name_in_prose_is_still_caught(self) -> None:
        # The other half of the carve-out: the filename is exempt, but a bareword prose reference to
        # the retired UNIT is still a finding — the guard is narrowed, not disabled.
        self._write("skills/probe/SKILL.md", "load the api-design skill first\n")
        failures = check_stale_names.check(self.root)
        self.assertTrue(any("api-design" in f for f in failures), failures)

    def test_word_boundary_prevents_substring_false_positive(self) -> None:
        # A retired name embedded in a longer token must not match (the boundary logic is load-
        # bearing: `sre` is a strict prefix of `sre-tool`, `observer`, etc.).
        self._write("skills/probe/SKILL.md", "the observerpattern helper and researcherxyz\n")
        self.assertEqual([], check_stale_names.check(self.root))

    def test_only_skills_agents_commands_are_scanned(self) -> None:
        # A stale name in docs/ or scripts/ is out of scope by design.
        self._write("docs/note.md", f"mentions {self._a_stale_name()} freely\n")
        self.assertEqual([], check_stale_names.check(self.root))


class EvalScenarioScopeTests(unittest.TestCase):
    """Scenario prompts are sent to the model verbatim, so a retired name there teaches it.

    Two live scenarios did: "You are sde-engineer" (canonical: `software-engineer`) and a reference to
    `code-reviewer` (canonical: `reviewer`). Both passed their graders, because the graders do not
    key on the agent name — the suite was quietly training the fleet's old vocabulary.
    """

    def test_a_stale_name_in_a_scenario_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scenarios = root / "evals/scenarios"
            scenarios.mkdir(parents=True)
            (scenarios / "probe.yaml").write_text(
                "prompt: |\n  You are sde-engineer. Do the thing.\n", encoding="utf-8"
            )
            failures = check_stale_names._scan_tree(root)
        self.assertTrue(any("sde-engineer" in f for f in failures), failures)

    def test_baselines_stay_out_of_scope(self) -> None:
        """Frozen result JSON records what was true on the day it ran.

        The repo has committed to leaving those bytes unchanged, and widening the scan to `evals`
        rather than `evals/scenarios` lights up on 24 such hits that are supposed to be there.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baselines = root / "evals/baselines/2026-07-31-run"
            baselines.mkdir(parents=True)
            (baselines / "result.json").write_text(
                '{"agent": "sde-engineer", "verdict": "pass"}\n', encoding="utf-8"
            )
            self.assertEqual([], check_stale_names._scan_tree(root))


if __name__ == "__main__":
    unittest.main()
