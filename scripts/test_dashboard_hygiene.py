#!/usr/bin/env python3
"""Offline tests for skills/grafana/scripts/dashboard_hygiene.py. Stdlib only, no network.

Fixture-first on purpose. A suite that only asserted "a known-bad dashboard produces violations"
would still pass if a rule were mutated into always-fire, and one that only asserted "a good
dashboard is clean" would pass if every rule were deleted. So each rule is exercised twice: once
against a model that satisfies it (must NOT fire) and once against the same model with a single
field changed (must fire, and fire that rule specifically).
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from testkit import load_path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "skills" / "grafana" / "scripts" / "dashboard_hygiene.py"

hygiene = load_path(MODULE, "dashboard_hygiene")


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
            "fieldConfig": {"defaults": {"unit": "percentunit", "noValue": "no data"}},
            "targets": [{
                "refId": "A",
                "expr": 'sum(rate(http_requests_total{job=~"$job"}[$__rate_interval]))',
            }],
        }],
    }


def clean_model_with(path: tuple, value: object) -> dict:
    """The clean fixture with the value at `path`, a sequence of keys and list indexes, replaced."""
    model = clean_model()
    parent = model
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    return model


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

    def test_each_datasource_reference_is_judged_for_portability(self) -> None:
        for path, datasource, fires in (
            (("panels", 0, "datasource"), {"type": "prometheus", "uid": "P1234567890ABCD"}, True),
            # Shipped defect: only panel.datasource was inspected. Grafana uses the target's override
            # when present, so a panel reading ${datasource} with one hard-coded target broke on move
            # while reporting clean.
            (("panels", 0, "targets", 0, "datasource"), {"type": "prometheus", "uid": "P1234567890ABCD"}, True),
            (("panels", 0, "targets", 0, "datasource"), {"type": "prometheus", "uid": "${datasource}"}, False),
            (("panels", 0, "datasource"), {"type": "datasource", "uid": "-- Grafana --"}, False),
        ):
            with self.subTest(path=path, datasource=datasource):
                fired = rules_fired(clean_model_with(path, datasource))
                self.assertEqual(fires, "panel-datasource" in fired, fired)

    def test_mixed_backends_use_independent_typed_variables(self) -> None:
        model = clean_model()
        model["templating"]["list"] = [
            {"name": "metrics_source", "type": "datasource", "query": "wavefront"},
            {"name": "logs_source", "type": "datasource", "query": "splunk"},
        ]
        logs = copy.deepcopy(model["panels"][0])
        model["panels"].append(logs)
        for panel, plugin, variable, query in (
            (model["panels"][0], "wavefront", "metrics_source", "ts(app.requests)"),
            (logs, "splunk", "logs_source", "index=app | stats count"),
        ):
            source = {"type": plugin, "uid": "${" + variable + "}"}
            panel["datasource"] = source
            panel["targets"] = [{"refId": "A", "datasource": source, "query": query}]
        logs.update(id=2, title="Request log evidence")
        self.assertEqual([], hygiene.check(model))

        # A target override still breaks portability even when other sources are variable-backed.
        logs["targets"][0]["datasource"] = {"type": "splunk", "uid": "literal-uid"}
        self.assertIn("panel-datasource", rules_fired(model))

    def test_promql_rules_judge_each_rate_call_and_counter(self) -> None:
        # The clean fixture's own counter, inside a rate call, is test_the_clean_fixture_fires_nothing's.
        for expr, rule, fires in (
            ("sum(rate(http_requests_total[5m]))", "target-rate-interval", True),
            # $__interval is the exact mistake the rule exists to catch; it must not satisfy it.
            ("sum(rate(x_total[$__interval]))", "target-rate-interval", True),
            # Shipped defect: the rule asked whether $__rate_interval appeared ANYWHERE in the
            # expression, so a compound query passed on the strength of its first call.
            ("rate(a_total[$__rate_interval]) + rate(b_total[5m])", "target-rate-interval", True),
            ("rate(a_total[$__rate_interval]) + rate(b_total[$__rate_interval])", "target-rate-interval", False),
            # increase over the selected range keeps its total semantics; rate over it does not.
            ("sum(increase(http_requests_total[$__range]))", "target-rate-interval", False),
            ("rate(http_requests_total[$__range])", "target-rate-interval", True),
            # Brackets inside a label regex are not range selectors.
            ('increase(network_bytes_total{device!~"nic[0-9]+"}[$__range])', "target-rate-interval", False),
            ('rate(network_bytes_total{device!~"nic[0-9]+"}[5m])', "target-rate-interval", True),
            # Quoted query text can neither hide nor invent a rate call.
            ('rate(http_requests_total{label="foo) [$__rate_interval]"}[5m])', "target-rate-interval", True),
            ('up{label="rate(fake_total[5m])"}', "target-rate-interval", False),
            ('up{label="rate(fake_total[5m])"}', "target-counter-agg", False),
            ("http_requests_total", "target-counter-agg", True),
            # Shipped defect: scope was inferred by counting parentheses before the metric, so the
            # already-closed rate call earlier in the expression made this counter look rated.
            ("sum(rate(a_total[$__rate_interval])) / sum(b_total)", "target-counter-agg", True),
            ("rate(a_total[$__rate_interval]) + sum(b_total)", "target-counter-agg", True),
        ):
            with self.subTest(expr=expr, rule=rule):
                fired = rules_fired(clean_model_with(("panels", 0, "targets", 0, "expr"), expr))
                self.assertEqual(fires, rule in fired, fired)

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
    def test_logql_rate_is_not_checked_as_promql(self) -> None:
        model = clean_model()
        panel = model['panels'][0]
        panel['datasource'] = {'type': 'loki', 'uid': '${logs_source}'}
        panel['targets'][0]['expr'] = 'sum(rate({service_name="checkout"}[$__interval]))'
        self.assertNotIn('target-rate-interval', rules_fired(model))

    def test_target_datasource_type_overrides_panel_type(self) -> None:
        model = clean_model()
        target = model['panels'][0]['targets'][0]
        target['datasource'] = {'type': 'loki', 'uid': '${logs_source}'}
        target['expr'] = 'rate({service_name="checkout"}[$__interval])'
        self.assertNotIn('target-rate-interval', rules_fired(model))
        model['panels'][0]['datasource'] = {'type': 'loki', 'uid': '${logs_source}'}
        target['datasource'] = {'type': 'prometheus', 'uid': '${metrics_source}'}
        target['expr'] = 'rate(http_requests_total[$__interval])'
        self.assertIn('target-rate-interval', rules_fired(model))

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

    def test_check_refuses_panels_it_cannot_traverse(self) -> None:
        # check() descends through the walk validation uses, so a caller that skips validation gets
        # the same located refusal for a panel container, panel or type it cannot traverse, not a
        # crash or findings computed over that panel. Fields inside a panel remain validation's job.
        for panels, message in (
            ([None], r"\$\.panels\[0\] must be an object"),
            ([{"type": 5, "title": "x"}], r"\$\.panels\[0\]\.type must be a string"),
            ({"title": "x"}, r"\$\.panels must be an array"),
            ([{"type": "row", "panels": [[]]}], r"\$\.panels\[0\]\.panels\[0\] must be an object"),
        ):
            with self.subTest(panels=panels), self.assertRaisesRegex(hygiene.InputShapeError, message):
                hygiene.check({"panels": panels, "tags": ["t"]})

    def test_wrappers_are_unwrapped_and_a_bare_model_passes_through(self) -> None:
        for model in ({"apiVersion": "dashboard.grafana.app/v1", "kind": "Dashboard",
                       "metadata": {"name": "x"}, "spec": clean_model()},
                      {"meta": {"provisioned": False}, "dashboard": clean_model()},
                      clean_model()):
            with self.subTest(keys=sorted(model)):
                self.assertEqual(clean_model()["title"], hygiene.unwrap(model)["title"])


class ExitCodeTest(unittest.TestCase):
    """The exit codes are the contract a CI step keys on: 0 clean, 1 violations, 2 uncheckable."""

    def _process(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-I", "-S", str(MODULE), str(path), "--quiet"],
                              capture_output=True, text=True, encoding="utf-8", check=False)

    def _check(self, text: str) -> subprocess.CompletedProcess[str]:
        """Run the checker on `text` saved as a dashboard file."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.json"
            path.write_text(text, encoding="utf-8")
            return self._process(path)

    def _run(self, model) -> int:
        result = self._check(json.dumps(model))
        self.assertNotIn("Traceback", result.stderr)
        return result.returncode

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
            result = self._process(missing)
        self.assertEqual(2, result.returncode)
        self.assertNotIn("Traceback", result.stderr)

    def test_input_too_deep_to_decode_exits_two_not_one(self) -> None:
        # The JSON decoder overflows the stack; a crash would exit 1, which reads as "violations".
        result = self._check('{"panels":' + "[" * 100_000 + "]" * 100_000 + "}")
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("cannot check", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_rows_nested_too_deep_to_walk_exit_two_not_one(self) -> None:
        # A decoder that accepts deep JSON leaves the row walk to overflow instead; same contract.
        # 1,500 rows decode on Python 3.13 and 3.14 and overflow the walk at the default limit.
        rows = 1_500
        result = self._check('{"tags":["t"],"panels":[' + '{"type":"row","panels":[' * rows
                             + '{"type":"timeseries","title":"t"}' + "]}" * rows + "]}")
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("cannot check", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        if "while decoding" in result.stderr:
            self.skipTest("this interpreter's JSON decoder overflows before the row walk (Python 3.11)")
        self.assertIn("maximum recursion depth exceeded", result.stderr)

    def test_a_title_the_output_encoding_cannot_represent_still_reports(self) -> None:
        # Captured output may default to a legacy code page; `-I` would ignore PYTHONIOENCODING.
        model = clean_model()
        model["title"] = "Checkout → Health"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d.json"
            path.write_text(json.dumps(model), encoding="utf-8")
            result = subprocess.run([sys.executable, "-S", str(MODULE), str(path)], capture_output=True,
                                    env={**os.environ, "PYTHONIOENCODING": "ascii"}, check=False)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("Checkout → Health".encode(), result.stdout)

    def test_malformed_shapes_exit_two_with_a_concise_location(self) -> None:
        cases = [(None, "$"), (["panels"], "$"), ([], "$")]
        for key, discriminator in (("spec", {"apiVersion": "dashboard.grafana.app/v1"}),
                                   ("dashboard", {"meta": {}})):
            for value in (None, [], "not an object"):
                cases.append(({**discriminator, key: value}, "$." + key))
            cases.append(({**discriminator, key: {"panels": [None]}}, f"$.{key}.panels[0]"))
        for path, value in (
            (("panels",), {}),
            (("panels",), "not an array"),
            (("panels", 0), None),
            (("panels", 0), []),
            (("panels", 0, "type"), []),
            (("panels", 0, "title"), 12),
            (("panels", 0, "description"), {}),
            (("panels", 0, "fieldConfig"), []),
            (("panels", 0, "fieldConfig", "defaults"), []),
            (("panels", 0, "targets"), {}),
            (("panels", 0, "targets", 0), None),
            (("panels", 0, "targets", 0), "not an object"),
            (("templating",), []),
            (("templating", "list"), {}),
            (("templating", "list", 0), None),
            (("templating", "list", 1, "allValue"), 12),
        ):
            location = "$" + "".join(f"[{key}]" if isinstance(key, int) else "." + key for key in path)
            cases.append((clean_model_with(path, value), location))
        for children, location in (({}, "$.panels[0].panels"),
                                   ([None], "$.panels[0].panels[0]")):
            cases.append(({"panels": [{"type": "row", "panels": children}], "tags": ["ok"]}, location))
        for model, location in cases:
            with self.subTest(model=model, location=location):
                result = self._check(json.dumps(model))
                self.assertEqual(2, result.returncode, result.stderr)
                self.assertIn("cannot check", result.stderr)
                self.assertIn(location, result.stderr)
                self.assertEqual(1, len(result.stderr.splitlines()), result.stderr)
                self.assertEqual("", result.stdout)

    def test_optional_null_fields_keep_existing_hygiene_outcomes(self) -> None:
        for path, expected in (
            (("panels",), 0),
            (("panels", 0, "type"), 0),
            (("panels", 0, "title"), 1),
            (("panels", 0, "description"), 1),
            (("panels", 0, "fieldConfig"), 1),
            (("panels", 0, "fieldConfig", "defaults"), 1),
            (("panels", 0, "targets"), 1),
            (("templating",), 0),
            (("templating", "list"), 0),
            (("templating", "list", 1, "allValue"), 1),
        ):
            with self.subTest(path=path):
                self.assertEqual(expected, self._run(clean_model_with(path, None)))

    def test_valid_wrappers_rows_and_opaque_plugin_queries_still_pass(self) -> None:
        nested = clean_model()
        nested["panels"] = [{"type": "row", "panels": nested["panels"]}]
        plugin = clean_model()
        plugin["panels"][0]["datasource"] = {"type": "custom-plugin", "uid": "${datasource}"}
        plugin["panels"][0]["targets"][0] = {"refId": "A", "query": {"pluginSpecific": [1, 2]}}
        legacy = clean_model()
        legacy["panels"][0]["datasource"] = "legacy datasource name"
        for model in ({"apiVersion": "dashboard.grafana.app/v1", "spec": clean_model()},
                      {"meta": {}, "dashboard": clean_model()}, nested, plugin, legacy):
            with self.subTest(model=model):
                self.assertEqual(0, self._run(model))


if __name__ == "__main__":
    unittest.main(verbosity=2)
