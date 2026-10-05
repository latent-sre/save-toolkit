#!/usr/bin/env python3
"""Contract tests for the cross-platform fleet-validation workflow."""
from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidateWorkflowTests(unittest.TestCase):
    def test_sandbox_dependencies_match_repository_pins(self) -> None:
        def pins(path):
            return {line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#")}

        repository = pins(ROOT / "requirements-dev.txt")
        for relative in ("sandbox/autogen-a2a-sandbox/requirements.txt",
                         "sandbox/graph-sandbox/runner/requirements.txt",
                         "sandbox/graph-sandbox/services/requirements.txt"):
            with self.subTest(path=relative):
                self.assertEqual(set(), pins(ROOT / relative) - repository,
                                 "sandbox dependencies drifted from the repository pin set")

    def test_ci_tracks_latest_python_314(self) -> None:
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        for name in ("validate", "component-tests"):
            setup = next(step for step in jobs[name]["steps"]
                         if step.get("uses", "").startswith("actions/setup-python@"))
            self.assertEqual("3.14", setup["with"]["python-version"])
            self.assertIs(setup["with"]["check-latest"], True)

    def test_repository_actions_use_major_tags(self) -> None:
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        for job in jobs.values():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], r"^[\w.-]+/[\w.-]+@v[0-9]+$")

    def test_deploy_oracle_action_policy(self) -> None:
        path = ROOT / "evals/oracles/pcf-deploy-job/probe_ci_workflow.py"
        spec = importlib.util.spec_from_file_location("ci_oracle", path)
        oracle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        cases = [
            ("actions/checkout@v7", True, True),
            ("actions/upload-artifact@v7", True, True),
            ("actions/download-artifact@v8", True, True),
            ("other/checkout@v7", True, False),
            ("actions/checkout/subaction@v7", True, False),
            ("actions/checkout@main", False, False),
            ("actions/checkout@latest", False, False),
            ("actions/checkout@v7.0.1", False, False),
            ("actions/checkout@" + "a" * 40, False, False),
            ("./local-action", True, True),
            ("docker://example@sha256:" + "a" * 64, True, True),
            ("docker://example:latest", False, True),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            workflow = Path(temporary) / "ci.yml"
            with mock.patch.object(oracle, "workflow_files", return_value=[str(workflow)]):
                for reference, valid, approved in cases:
                    with self.subTest(reference=reference):
                        workflow.write_text(f"steps:\n  - uses: {reference}\n", encoding="utf-8")
                        self.assertEqual(oracle.case_pins() is None, valid)
                        self.assertEqual(oracle.case_reviewed_pins() is None, approved)

    def test_plugin_validator_tracks_latest_and_records_its_version(self) -> None:
        job = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["claude-plugin-contract"]
        commands = [line.strip() for step in job["steps"] for line in step.get("run", "").splitlines()]
        install = commands.index("npm install -g @anthropic-ai/claude-code@latest")
        version = commands.index("claude --version")
        marketplace = commands.index("claude plugin validate .claude-plugin/marketplace.json --strict")
        validate = commands.index("claude plugin validate .claude-plugin/plugin.json")
        self.assertLess(install, version)
        self.assertLess(version, marketplace)
        self.assertLess(version, validate)
        self.assertNotIn("claude plugin validate . --strict", commands)
        for step in job["steps"]:
            if "claude plugin validate" in step.get("run", ""):
                self.assertNotIn("continue-on-error", step)

    def test_linux_validate_job_runs_gate_a(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        validate_job, separator, _remainder = workflow.partition("\n  component-tests:")
        self.assertTrue(separator, "validate workflow has no component-tests job")
        self.assertIn("runs-on: ubuntu-latest", validate_job, "the Linux validate job lost its runner")
        self.assertIn(
            "run: python scripts/gate_a.py",
            validate_job,
            "the Linux validate job no longer invokes Gate A",
        )

    def test_ci_runs_only_linux_and_preserves_the_required_check_name(self) -> None:
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        self.assertEqual({"ubuntu-latest"}, {job["runs-on"] for job in jobs.values()})
        self.assertNotIn("strategy", jobs["component-tests"])
        self.assertEqual("component-tests (ubuntu-latest)", jobs["component-tests"]["name"])

    def test_gate_a_jobs_do_not_fetch_history_for_focused_component_tests(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        validate_job, separator, _remainder = workflow.partition(
            "\n  claude-plugin-contract:"
        )
        self.assertTrue(separator, "validate workflow lost the plugin-contract job boundary")
        self.assertNotIn(
            "fetch-depth: 0",
            validate_job,
            "the structural gate reads the checked-out tree; focused snapshot tests own history",
        )

    @classmethod
    def _gate_path_scripts(cls) -> list[Path]:
        """Scripts Gate A runs, plus the modules they import from this repository."""
        gate = (ROOT / "scripts" / "gate_a.py").read_text(encoding="utf-8")
        named = {ROOT / name for name in re.findall(r'"(scripts/[a-z_]+\.py)"', gate)}
        pending = [ROOT / "scripts/gate_a.py", *named]
        visited: set[Path] = set()
        while pending:
            path = pending.pop()
            if path in visited or not path.is_file():
                continue
            visited.add(path)
            pending.extend(ROOT / "scripts" / f"{name}.py" for name in cls._imports(path))
        return sorted(visited)

    @staticmethod
    def _imports(path: Path) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
                if node.module == "scripts":
                    names.extend(alias.name for alias in node.names if alias.name != "*")
            found.update(name.removeprefix("scripts.").split(".")[0] for name in names)
        return found

    @classmethod
    def _third_party_imports(cls, path: Path) -> set[str]:
        local = {module.stem for module in (ROOT / "scripts").glob("*.py")}
        return cls._imports(path) - sys.stdlib_module_names - local - {"scripts"}

    def test_dependency_install_in_another_job_does_not_satisfy_gate_a(self) -> None:
        workflow = (
            "jobs:\n"
            "  validate:\n"
            "    steps:\n"
            "      - run: python scripts/gate_a.py\n"
            "  component-tests:\n"
            "    steps:\n"
            "      - run: python -m pip install -r requirements-dev.txt\n"
        )
        for statement in (
            "import yaml", "import fleet_frontmatter", "from scripts import fleet_frontmatter",
            "from scripts import fleet_frontmatter as frontmatter",
            "import scripts.fleet_frontmatter as frontmatter",
            "from scripts.fleet_frontmatter import yaml",
        ):
            with self.subTest(statement=statement), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                (root / "scripts").mkdir()
                (root / "scripts/gate_a.py").write_text(
                    'STEPS = ["scripts/validate_fleet.py"]\n', encoding="utf-8",
                )
                (root / "scripts/validate_fleet.py").write_text(
                    statement + "\n", encoding="utf-8",
                )
                (root / "scripts/fleet_frontmatter.py").write_text("import yaml\n", encoding="utf-8")
                workflow_path = root / "validate.yml"
                workflow_path.write_text(workflow, encoding="utf-8")
                with mock.patch.multiple(sys.modules[__name__], ROOT=root, WORKFLOW=workflow_path):
                    with self.assertRaisesRegex(AssertionError, "gate-path scripts import"):
                        self.test_live_tree_satisfies_the_dependency_contract()
                    workflow_path.write_text(
                        workflow.replace(
                            "      - run: python scripts/gate_a.py",
                            "      - run: python -m pip install -r requirements-dev.txt\n"
                            "      - run: python scripts/gate_a.py",
                        ),
                        encoding="utf-8",
                    )
                    self.test_live_tree_satisfies_the_dependency_contract()

    def test_live_tree_satisfies_the_dependency_contract(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        steps = yaml.safe_load(workflow)["jobs"]["validate"]["steps"]
        gate_index = next(
            index for index, step in enumerate(steps)
            if "python scripts/gate_a.py" in step.get("run", "").splitlines()
        )
        ci_installs = any(
            "python -m pip install -r requirements-dev.txt" in step.get("run", "").splitlines()
            and "if" not in step
            for step in steps[:gate_index]
        )
        offenders = {
            path.relative_to(ROOT).as_posix(): sorted(self._third_party_imports(path))
            for path in self._gate_path_scripts()
            if self._third_party_imports(path)
        }
        self.assertFalse(
            offenders and not ci_installs,
            f"gate-path scripts import {offenders} but the validate job installs no "
            "dependencies before Gate A; add `python -m pip install -r requirements-dev.txt` "
            "to that job (and update gate_a.py's docstring) in the same change",
        )

    def test_readonly_guard_is_standard_library_only(self) -> None:
        """The guard is exempt from the dependency allowance, permanently.

        The session hook runs it as `python -I -S`: no user environment, no `site`. An installed
        plugin never pip-installs anything, so a third-party import raises before the guard can
        return 42/43, the launcher falls through to its blanket deny, and every guarded Bash
        command dies. CI installing the package would not help -- CI is not where the guard runs.
        """
        guard = ROOT / "scripts" / "readonly-guard.py"
        self.assertEqual(set(), self._third_party_imports(guard))
        hook = (ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8")
        self.assertIn("-I -S", hook, "the guard's isolated invocation is what makes this binding")

    def test_component_tests_install_dependencies_and_run_pytest(self) -> None:
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        commands = [step.get("run") for step in jobs["component-tests"]["steps"]]
        self.assertIn("python -m pytest -q", commands)
        self.assertIn("python -m pip install -r requirements-test.txt", commands)

    def test_component_tests_run_in_parallel_without_writing_bytecode(self) -> None:
        """The eval runner digests every file under skills/, compiled caches included.

        A .pyc that one worker writes while another runs a native trial reads as plugin drift, so
        parallel workers are only safe while the test step writes no bytecode.
        """
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        step = next(step for step in jobs["component-tests"]["steps"]
                    if step.get("run") == "python -m pytest -q")
        environment = step.get("env", {})
        self.assertRegex(environment.get("PYTEST_ADDOPTS", ""), r"(^| )-n [0-9]+( |$)",
                         "the component tests no longer run on parallel workers")
        self.assertIn("--dist loadfile", environment["PYTEST_ADDOPTS"])
        self.assertEqual("1", environment.get("PYTHONDONTWRITEBYTECODE"),
                         "parallel workers may write .pyc files under skills/ mid-trial")

    def test_the_gate_still_has_a_schedule_and_manual_dispatch(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        triggers = workflow.partition("\npermissions:")[0]
        self.assertRegex(triggers, re.compile(r"^  schedule:\n    - cron: ", re.MULTILINE))
        self.assertIn("workflow_dispatch:", triggers)


class ArtifactPromotionOracleTests(unittest.TestCase):
    """Run the real probe on the build scenario's manifest and workflow files; no shell executes."""

    ORACLE = ROOT / "evals/oracles/pcf-deploy-job/probe_ci_workflow.py"
    SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-adds-pcf-deploy-job.yaml"

    def probe(self, steps, *, defaults=None, workflow_defaults=None, env=None, manifest=None, additional_jobs=None):
        fixture = yaml.safe_load(self.SCENARIO.read_text(encoding="utf-8"))["fixture"]["files"]
        workflow = yaml.safe_load(fixture[".github/workflows/ci.yml"])
        job = {"steps": steps}
        if defaults:
            job["defaults"] = {"run": defaults}
        if workflow_defaults:
            workflow["defaults"] = {"run": workflow_defaults}
        if env:
            job["env"] = env
        workflow["jobs"]["deploy"] = job
        workflow["jobs"].update(additional_jobs or {})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / ".github/workflows/ci.yml"
            destination.parent.mkdir(parents=True)
            destination.write_text(yaml.safe_dump(workflow), encoding="utf-8")
            (root / "manifest.yml").write_text(
                fixture["manifest.yml"] if manifest is None else manifest, encoding="utf-8",
            )
            return subprocess.run(
                [sys.executable, str(self.ORACLE), "artifact-promoted"], cwd=root,
                capture_output=True, text=True, timeout=20,
            )

    @staticmethod
    def checkout(**inputs):
        return {"uses": "actions/checkout@v7", "with": inputs}

    @staticmethod
    def download(path="dist", **step_fields):
        inputs = {"name": "checkout-build"}
        if path is not None:
            inputs["path"] = path
        return {"uses": "actions/download-artifact@v8", "with": inputs, **step_fields}

    def test_downloaded_payload_paths_and_reviewed_manifest_are_accepted(self):
        cases = [
            ("manifest path", "dist", {"run": "cf push checkout --strategy rolling"}, {}),
            ("explicit path", "reviewed-artifact",
             {"run": "cf push checkout -p reviewed-artifact/checkout.zip -f ./manifest.yml"}, {}),
            ("long options", "dist",
             {"run": "cf push checkout --path=dist/checkout.zip --manifest=manifest.yml"}, {}),
            ("manifest directory", "dist",
             {"run": "cf push checkout -f ."}, {}),
            ("default download destination", None,
             {"run": "cf push checkout -p checkout.zip"}, {}),
            ("step directory", "dist",
             {"working-directory": "dist", "run": "cf push checkout -f ../manifest.yml -p checkout.zip"}, {}),
            ("job directory and manifest-relative payload", "dist",
             {"run": "cf push checkout -f ../manifest.yml"}, {"defaults": {"working-directory": "dist"}}),
            ("workflow directory", "dist", {"run": "cf push checkout -f ../manifest.yml"},
             {"workflow_defaults": {"working-directory": "dist"}}),
            ("step directory overrides defaults", "dist",
             {"working-directory": ".", "run": "cf push checkout -p dist/checkout.zip"},
             {"defaults": {"working-directory": "other"}, "workflow_defaults": {"working-directory": "wrong"}}),
            ("literal cd", "dist",
             {"run": "set -euo pipefail\ncd dist && cf push checkout -f ../manifest.yml -p checkout.zip"}, {}),
            ("separator followed by newline", "dist",
             {"run": "echo deploying;\ncf api https://api.example.invalid &&\ncf push checkout"}, {}),
            ("comment keeps command boundary", "dist",
             {"run": 'echo "# deployment" # comment\ncf push checkout # reviewed bytes'}, {}),
            ("workspace expression", "${{ github.workspace }}/dist",
             {"run": 'cf push checkout -f "$GITHUB_WORKSPACE/manifest.yml" -p "${GITHUB_WORKSPACE}/dist/checkout.zip"'}, {}),
            ("literal environment path", "${{ env.ARTIFACT_DIR }}",
             {"run": 'cf push checkout -p "$ARTIFACT_DIR/checkout.zip"'}, {"env": {"ARTIFACT_DIR": "dist"}}),
            ("quoted path and continuation", "reviewed artifact",
             {"run": "cf push checkout \\\n  -p 'reviewed artifact/checkout.zip' --strategy rolling # reviewed bytes\n"}, {}),
        ]
        for name, path, push, options in cases:
            with self.subTest(name=name):
                result = self.probe([self.checkout(), self.download(path), push], **options)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_checkout_path_and_step_shell_directory_are_resolved_separately(self):
        result = self.probe([
            self.checkout(path="source"), self.download("source/dist"),
            {"run": "cd source/dist"},
            {"run": "cf push checkout -f source/manifest.yml -p source/dist/checkout.zip"},
        ])
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        result = self.probe([
            self.checkout(), self.download(None),
            {"run": "cf push checkout -f ../manifest.yml -p ../checkout.zip"},
        ], defaults={"working-directory": "dist"})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_unrelated_ignored_and_unresolved_payloads_are_rejected(self):
        cases = [
            ("reported unrelated payload", "reviewed-artifact", "cf push checkout -p /tmp/unrelated-bytes"),
            ("ignored download", "reviewed-artifact", "cf push checkout"),
            ("wrong archive", "dist", "cf push checkout -p dist/unreviewed.zip"),
            ("unresolved variable", "dist", 'cf push checkout -p "$PUSH_PATH"'),
            ("literal variable", "dist", "cf push checkout -p '$ARTIFACT_DIR/checkout.zip'"),
            ("unreviewed manifest", "dist", "cf push checkout -f other.yml -p dist/checkout.zip"),
            ("no manifest", "dist", "cf push checkout --no-manifest -p dist/checkout.zip"),
            ("docker replacement", "dist", "cf push checkout -p dist/checkout.zip --docker-image unrelated"),
            ("second push", "dist", "cf push checkout\ncf push checkout -p /tmp/unrelated-bytes"),
            ("first push", "dist", "cf push checkout -p /tmp/unrelated-bytes\ncf push checkout"),
            ("unknown download expression", "${{ inputs.destination }}", "cf push checkout"),
            ("repeated payload option", "dist", "cf push checkout -p dist/checkout.zip --path /tmp/unrelated"),
        ]
        for name, path, command in cases:
            with self.subTest(name=name):
                result = self.probe([
                    self.checkout(), self.download(path), {"run": command},
                ], env={"ARTIFACT_DIR": "dist"})
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("artifact-promoted", result.stdout)

    def test_replacement_rebuild_and_opaque_shell_before_push_are_rejected(self):
        for command in (
            "cp /tmp/unrelated-bytes dist/checkout.zip",
            "printf unrelated > dist/checkout.zip",
            "scripts/build.sh",
            "scripts/repackage.sh",
            "python3 -c 'from pathlib import Path; Path(\"dist/checkout.zip\").write_bytes(b\"other\")'",
            "ln -sf /tmp/unrelated-bytes dist/checkout.zip",
            "echo $(cp /tmp/unrelated-bytes dist/checkout.zip)",
            "if true; then cp /tmp/unrelated-bytes dist/checkout.zip; fi",
            "echo deploying;\ncp /tmp/unrelated-bytes dist/checkout.zip",
            "echo deploying &&\ncp /tmp/unrelated-bytes dist/checkout.zip",
            "echo unrelated >& dist/checkout.zip",
            'echo "${ARTIFACT_DIR:=/tmp/unrelated}"',
            "echo deploying # comment\ncp /tmp/unrelated-bytes dist/checkout.zip",
            "echo deploying # comment \\\ncp /tmp/unrelated-bytes dist/checkout.zip",
        ):
            with self.subTest(command=command):
                result = self.probe([
                    self.checkout(), self.download(), {"run": command + "\ncf push checkout"},
                ])
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("unsupported", result.stdout)

    def test_download_and_reviewed_checkout_must_precede_every_push(self):
        push = {"run": "cf push checkout"}
        cases = [
            ("absent download", [self.checkout(), push]),
            ("late download", [self.checkout(), push, self.download()]),
            ("skipped download", [self.checkout(), self.download(**{"if": False}), push]),
            ("tolerated download failure", [self.checkout(), self.download(**{"continue-on-error": True}), push]),
            ("checkout replaces bytes", [self.checkout(), self.download(), self.checkout(), push]),
            ("absent checkout", [self.download(), push]),
            ("unreviewed checkout", [self.checkout(ref="other"), self.download(), push]),
            ("retained stale manifest", [self.checkout(clean=False), self.download(), push]),
            ("unsupported shell", [self.checkout(), self.download(), {**push, "shell": "pwsh"}]),
        ]
        for name, steps in cases:
            with self.subTest(name=name):
                result = self.probe(steps)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("artifact-promoted:", result.stdout)

    def test_opaque_trailing_pushes_and_option_substitutions_are_rejected(self):
        for trailing in (
            "bash -c 'cf push checkout -p /tmp/unrelated-bytes'",
            "./deploy-again.sh",
        ):
            for same_step in (False, True):
                with self.subTest(trailing=trailing, same_step=same_step):
                    runs = ([{"run": "cf push checkout\n" + trailing}] if same_step else
                            [{"run": "cf push checkout"}, {"run": trailing}])
                    result = self.probe([self.checkout(), self.download(), *runs])
                    self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                    self.assertIn("unsupported", result.stdout)
        for option in ("--strategy", "-b", "-c"):
            with self.subTest(option=option):
                result = self.probe([
                    self.checkout(), self.download(),
                    {"run": f'cf push checkout {option} "$(cp /tmp/unrelated-bytes dist/checkout.zip)"'},
                ])
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("unsupported", result.stdout)
        result = self.probe([
            self.checkout(), self.download(),
            {"run": "cf push checkout\ncf app checkout"}, {"run": "echo deployment complete"},
        ])
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_modified_manifest_and_an_additional_bad_deploy_job_are_rejected(self):
        result = self.probe([
            self.checkout(), self.download(), {"run": "cf push checkout -p dist/checkout.zip"},
        ], manifest="applications:\n  - name: checkout\n    path: /tmp/unrelated\n")
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("reviewed fixture manifest", result.stdout)
        result = self.probe([
            self.checkout(), self.download(), {"run": "cf push checkout"},
        ], additional_jobs={"other": {"steps": [
            self.checkout(), self.download("ignored"), {"run": "cf push checkout"},
        ]}})
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn("job other: cf push payload", result.stdout)

    def test_every_option_value_must_be_one_resolved_shell_word(self):
        for option in ("--strategy", "-b", "-m", "-i", "-k", "-t", "-c"):
            with self.subTest(option=option):
                result = self.probe([
                    self.checkout(), self.download(), {"run": f"cf push checkout {option} $BUILDPACK"},
                ], env={"BUILDPACK": "null -p /tmp/unrelated-bytes"})
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("unsupported", result.stdout)
        for value in (None, "", "*", "?", "[abc]"):
            with self.subTest(value=value):
                result = self.probe([
                    self.checkout(), self.download(), {"run": "cf push checkout -b $BUILDPACK"},
                ], env={} if value is None else {"BUILDPACK": value})
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("unsupported", result.stdout)
        for value in ("null -p /tmp/unrelated-bytes", "*", "?", "[abc]"):
            with self.subTest(quoted_value=value):
                result = self.probe([
                    self.checkout(), self.download(), {"run": 'cf push checkout -b "$BUILDPACK"'},
                ], env={"BUILDPACK": value})
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        for option in ("--no-start", "--no-route", "--random-route", "--no-wait"):
            with self.subTest(inline_option=option):
                result = self.probe([
                    self.checkout(), self.download(), {"run": f"cf push checkout {option}=$FLAGS"},
                ], env={"FLAGS": "true -p /tmp/unrelated-bytes"})
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                self.assertIn("unsupported", result.stdout)
        for value in ("true", "false"):
            with self.subTest(boolean_value=value):
                result = self.probe([
                    self.checkout(), self.download(), {"run": f"cf push checkout --no-start={value}"},
                ])
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
