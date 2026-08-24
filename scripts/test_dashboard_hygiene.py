#!/usr/bin/env python3
"""Offline tests for skills/obs-dashboards/scripts/dashboard_hygiene.py. Stdlib only, no network.

Fixture-first on purpose. A suite that only asserted "a known-bad dashboard produces violations"
would still pass if a rule were mutated into always-fire, and one that only asserted "a good
dashboard is clean" would pass if every rule were deleted. So each rule is exercised twice: once
against a model that satisfies it (must NOT fire) and once against the same model with a single
field changed (must fire, and fire that rule specifically).
"""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills" / "obs-dashboards" / "scripts" / "dashboard_hygiene.py"

_spec = importlib.util.spec_from_file_location("dashboard_hygiene", MODULE)
hygiene = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hygiene)


def clean_model() -> dict:
    """A dashboard that satisfies every rule this checker knows."""
    return {
        "title": "Checkout / Health",
        "uid": "checkout-health",
        "tags": ["platform", "checkout"],
        "templating": {"list": [
            {"name": "datasource", "type": "datasource", "query": "prometheus"},
            {"name": "job", "type": "query", "multi": True, "includeAll": True, "allValue": ".+"},
        ]},
        "panels": [{
            "id": 1,
            "type": "timeseries",
            "title": "Is checkout error ratio breaching target?",
            "description": "5xx over all requests, SLO 99.9%.",
            "datasource": {"type": "prometheus", "uid": "${datasource}"},
            "fieldConfig": {"defaults": {"unit": "percentunit", "noValue": "no traffic"}},
            "targets": [{
                "refId": "A",
                "expr": 'sum(rate(http_requests_total{job=~"$job"}[$__rate_interval]))',
            }],
        }],
    }


def rules_fired(model: dict) -> set[str]:
    return {rule for rule, _where, _detail in hygiene.check(model)}


class CleanModelTest(unittest.TestCase):
    def test_the_clean_fixture_fires_nothing(self) -> None:
        # If this ever fails, every mutation test below is measuring the wrong baseline.
        self.assertEqual(set(), rules_fired(clean_model()))


class RuleMutationTest(unittest.TestCase):
    """One mutation per rule. Each must fire ITS OWN rule, proving the rule discriminates."""

    def _mutate(self, mutate) -> set[str]:
        model = clean_model()
        mutate(model)
        return rules_fired(model)

    def test_missing_title(self) -> None:
        self.assertIn("panel-title", self._mutate(lambda m: m["panels"][0].update(title="  ")))

    def test_missing_description(self) -> None:
        self.assertIn("panel-description", self._mutate(lambda m: m["panels"][0].pop("description")))

    def test_missing_unit_on_a_unit_bearing_panel(self) -> None:
        fired = self._mutate(lambda m: m["panels"][0]["fieldConfig"]["defaults"].pop("unit"))
        self.assertIn("panel-units", fired)

    def test_a_text_panel_is_not_asked_for_a_query_or_a_no_value(self) -> None:
        # Shipped defect: the documentation Text panel this skill tells authors to add was reported
        # for having no target and no "No value", so the mandatory pre-write check failed on a
        # correct dashboard.
        model = clean_model()
        model["panels"] = [{
            "id": 9, "type": "text", "title": "About this dashboard",
            "description": "purpose, links, and how to read it",
            "options": {"content": "# Purpose"}, "fieldConfig": {"defaults": {}},
        }]
        fired = rules_fired(model)
        self.assertNotIn("panel-no-targets", fired)
        self.assertNotIn("panel-no-value", fired)
        self.assertNotIn("panel-units", fired)

    def test_a_querying_panel_is_still_asked_for_a_target(self) -> None:
        # The exemption must be scoped to non-querying types, not a hole for every panel.
        self.assertIn("panel-no-targets", self._mutate(lambda m: m["panels"][0].update(targets=[])))

    def test_unit_is_not_demanded_of_a_text_panel(self) -> None:
        # The rule must not fire where a unit is meaningless, or people learn to ignore it.
        def mutate(m):
            m["panels"][0]["type"] = "text"
            m["panels"][0]["fieldConfig"]["defaults"].pop("unit")
        self.assertNotIn("panel-units", self._mutate(mutate))

    def test_missing_no_value(self) -> None:
        fired = self._mutate(lambda m: m["panels"][0]["fieldConfig"]["defaults"].pop("noValue"))
        self.assertIn("panel-no-value", fired)

    def test_hardcoded_datasource_uid(self) -> None:
        fired = self._mutate(
            lambda m: m["panels"][0].update(datasource={"type": "prometheus", "uid": "P1234567890ABCD"})
        )
        self.assertIn("panel-datasource", fired)

    def test_a_target_level_datasource_override_is_flagged(self) -> None:
        # Shipped defect: only panel.datasource was inspected. Grafana uses the target's override
        # when present, so a panel reading ${datasource} with one hard-coded target broke on move
        # while reporting clean.
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(
                datasource={"type": "prometheus", "uid": "P1234567890ABCD"}
            )
        )
        self.assertIn("panel-datasource", fired)

    def test_a_target_datasource_variable_is_not_flagged(self) -> None:
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(
                datasource={"type": "prometheus", "uid": "${datasource}"}
            )
        )
        self.assertNotIn("panel-datasource", fired)

    def test_builtin_datasource_is_not_flagged(self) -> None:
        fired = self._mutate(
            lambda m: m["panels"][0].update(datasource={"type": "datasource", "uid": "-- Grafana --"})
        )
        self.assertNotIn("panel-datasource", fired)

    def test_rate_without_rate_interval(self) -> None:
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(expr="sum(rate(http_requests_total[5m]))")
        )
        self.assertIn("target-rate-interval", fired)

    def test_interval_variable_is_not_accepted_as_rate_interval(self) -> None:
        # $__interval is the exact mistake the rule exists to catch; it must not satisfy it.
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(expr="sum(rate(x_total[$__interval]))")
        )
        self.assertIn("target-rate-interval", fired)

    def test_one_correct_rate_call_does_not_excuse_a_second_wrong_one(self) -> None:
        # Shipped defect: the rule asked whether $__rate_interval appeared ANYWHERE in the
        # expression, so a compound query passed on the strength of its first call.
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(
                expr="rate(a_total[$__rate_interval]) + rate(b_total[5m])"
            )
        )
        self.assertIn("target-rate-interval", fired)

    def test_every_rate_call_correct_is_clean(self) -> None:
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(
                expr="rate(a_total[$__rate_interval]) + rate(b_total[$__rate_interval])"
            )
        )
        self.assertNotIn("target-rate-interval", fired)

    def test_raw_counter_without_aggregation(self) -> None:
        fired = self._mutate(lambda m: m["panels"][0]["targets"][0].update(expr="http_requests_total"))
        self.assertIn("target-counter-agg", fired)

    def test_counter_inside_rate_is_not_flagged(self) -> None:
        self.assertNotIn("target-counter-agg", rules_fired(clean_model()))

    def test_a_raw_counter_after_a_closed_rate_call_is_flagged(self) -> None:
        # Shipped defect: scope was inferred by counting parentheses before the metric, so the
        # already-closed rate call earlier in the expression made this counter look rated.
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(
                expr="sum(rate(a_total[$__rate_interval])) / sum(b_total)"
            )
        )
        self.assertIn("target-counter-agg", fired)

    def test_a_raw_counter_beside_a_rate_call_is_flagged(self) -> None:
        fired = self._mutate(
            lambda m: m["panels"][0]["targets"][0].update(
                expr="rate(a_total[$__rate_interval]) + sum(b_total)"
            )
        )
        self.assertIn("target-counter-agg", fired)

    def test_include_all_without_custom_all_value(self) -> None:
        fired = self._mutate(lambda m: m["templating"]["list"][1].update(allValue=""))
        self.assertIn("template-all-value", fired)

    def test_variable_without_include_all_is_not_flagged(self) -> None:
        def mutate(m):
            m["templating"]["list"][1]["includeAll"] = False
            m["templating"]["list"][1]["allValue"] = ""
        self.assertNotIn("template-all-value", self._mutate(mutate))

    def test_missing_tags(self) -> None:
        self.assertIn("dashboard-tags", self._mutate(lambda m: m.update(tags=[])))


class StructureTest(unittest.TestCase):
    def test_panels_inside_a_collapsed_row_are_checked(self) -> None:
        # A row's children are the easiest panels to forget; the walker must descend.
        model = clean_model()
        hidden = copy.deepcopy(model["panels"][0])
        hidden["id"] = 2
        hidden.pop("description")
        model["panels"] = [{"type": "row", "title": "Drill-down", "panels": [hidden]}]
        self.assertIn("panel-description", rules_fired(model))

    def test_row_panels_are_not_themselves_checked(self) -> None:
        # A row has no unit, description, or targets and must not be reported for lacking them.
        # Written flat on purpose: the previous form was `fired - {a} & {b, c}`, which is correct
        # (binary `-` binds tighter than `&`) and was proven to fail under mutation, but a reviewer
        # read it as vacuous. An assertion whose correctness needs a precedence argument is a bad
        # assertion even when it works.
        model = clean_model()
        model["panels"] = [{"type": "row", "title": "R", "panels": []}]
        fired = rules_fired(model)
        self.assertNotIn("panel-units", fired)
        self.assertNotIn("panel-no-targets", fired)
        self.assertNotIn("panel-description", fired)

    def test_k8s_wrapper_is_unwrapped(self) -> None:
        wrapped = {"apiVersion": "dashboard.grafana.app/v1", "kind": "Dashboard",
                   "metadata": {"name": "x"}, "spec": clean_model()}
        self.assertEqual(clean_model()["title"], hygiene.unwrap(wrapped)["title"])

    def test_legacy_get_body_is_unwrapped(self) -> None:
        legacy = {"meta": {"provisioned": False}, "dashboard": clean_model()}
        self.assertEqual(clean_model()["title"], hygiene.unwrap(legacy)["title"])

    def test_bare_model_passes_through(self) -> None:
        self.assertEqual(clean_model()["title"], hygiene.unwrap(clean_model())["title"])


class ExitCodeTest(unittest.TestCase):
    """The exit codes are the contract a CI step keys on: 0 clean, 1 violations, 2 uncheckable."""

    def _run(self, model: dict) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.json"
            path.write_text(json.dumps(model), encoding="utf-8")
            return hygiene.main([str(path), "--quiet"])

    def test_clean_exits_zero(self) -> None:
        self.assertEqual(0, self._run(clean_model()))

    def test_violations_exit_one(self) -> None:
        model = clean_model()
        model["panels"][0].pop("description")   # any real rule will do; this one is stable
        self.assertEqual(1, self._run(model))

    def test_v2_dashboard_is_refused_not_silently_passed(self) -> None:
        # The dangerous failure: reporting "0 violations" for a model whose panels were never read.
        self.assertEqual(2, self._run({"title": "v2", "elements": {}, "layout": {}}))

    def test_a_model_without_panels_is_refused(self) -> None:
        self.assertEqual(2, self._run({"title": "nope"}))

    def test_unreadable_file_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "absent.json"
            self.assertEqual(2, hygiene.main([str(missing), "--quiet"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
