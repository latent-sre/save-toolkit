"""Runtime timeout and executable CF-target oracle regression controls."""

import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
import yaml
from probe_testkit import load_oracle
from test_eval011_oracles import execute

ROOT = Path(__file__).resolve().parent
GO = ROOT / "oracles/go-incidents-api/probe_checks.py"
CI = ROOT / "oracles/pcf-deploy-job/probe_ci_workflow.py"


@pytest.mark.parametrize(
    "prefix",
    [
        "# cf api https://api.invalid\n# cf target -o prod -s prod",
        "echo cf api https://api.invalid\necho cf target -o prod -s prod",
        "cf api\ncf target -o prod -s prod",
        'cf api "$UNSET"\ncf target -o prod -s prod',
        'cf api https://api.invalid\ncf target -o "$UNSET" -s prod',
        'cf api https://api.invalid\ncf target -o prod -s "$UNSET"',
        'cf api "unterminated\ncf target -o prod -s prod',
        "cf api https://api.invalid\ncf target -o -s prod",
        "cf push checkout\ncf api https://api.invalid\ncf target -o prod -s prod",
    ],
)
def test_cf_target_rejects_noncommands_or_missing_selection(prefix):
    oracle = load_oracle(CI)
    assert oracle._cf_target({"steps": [{"run": prefix + "\ncf push checkout"}]}, {})


@pytest.mark.parametrize(
    "prefix",
    [
        "cf api https://api.invalid\ncf target -o prod -s prod",
        "cf api https://api.invalid && cf target -s prod -o prod",
        "cf api https://api.invalid # endpoint\ncf target -o prod \\\n -s prod",
    ],
)
def test_cf_target_accepts_real_ordered_commands(prefix):
    oracle = load_oracle(CI)
    assert oracle._cf_target({"steps": [{"run": prefix + "\ncf push checkout"}]}, {}) is None


@pytest.mark.parametrize("mode", ["bounded", "unbounded", "streaming", "exited", "broken_http"])
def test_header_timeout_measures_launched_socket_not_source(tmp_path, monkeypatch, mode):
    oracle = load_oracle(GO)
    # These source markers used to pass even though the launched peer has no limit.
    (tmp_path / "main.go").write_text("// ReadHeaderTimeout\nvar unused = http.Server{ReadHeaderTimeout: 0}\n")
    monkeypatch.setattr(oracle, "WORKSPACE", tmp_path)
    monkeypatch.setattr(oracle, "HEADER_TIMEOUT_LIMIT", 0.15, raising=False)
    stop = threading.Event()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(1)

        def serve():
            peer, _ = listener.accept()
            with peer:
                assert b"Host:" in peer.recv(4096)
                if mode == "streaming":
                    while not stop.wait(0.015):
                        try:
                            peer.sendall(b"x")
                        except OSError:
                            break
                else:
                    stop.wait(2 if mode == "unbounded" else 0.025)

        thread = threading.Thread(target=serve)
        thread.start()
        service = SimpleNamespace(
            port=listener.getsockname()[1],
            proc=SimpleNamespace(poll=lambda: 0 if mode == "exited" else None),
            request=lambda *args: (401 if mode == "broken_http" else 200, {}, b"ok"),
        )

        class Running:
            def __enter__(self):
                return service

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(oracle, "Service", Running)
        try:
            with pytest.raises(SystemExit) as result:
                oracle.check_server_timeouts()
            assert result.value.code == (0 if mode == "bounded" else 10)
        finally:
            stop.set()
            thread.join(timeout=2)


@pytest.mark.parametrize("oracle,case", [(GO, "server_timeouts"), (CI, "cf-target")])
@pytest.mark.parametrize(
    "fault,code",
    [
        ("raise SystemExit(0)", 0),
        ("raise SystemExit(10)", 10),
        ("import os; os._exit(0)", 1),
        ("raise SystemExit(1)", 1),
        ("raise RuntimeError('oracle crash')", 1),
    ],
)
def test_changed_oracles_supervised_completion_outcomes(tmp_path, oracle, case, fault, code):
    source = oracle.read_text(encoding="utf-8")
    if oracle == GO:
        source = source.replace("    CHECKS[sys.argv[1]]()", "    " + fault)
    else:
        source = source.replace("        reason = CASES[sys.argv[1]]()", "        " + fault)
    result = execute(tmp_path, source, args=(case,))
    assert result.returncode == code, result.stdout + result.stderr


@pytest.mark.parametrize("commented", [False, True])
def test_actual_cf_target_supervised_assessment(tmp_path, commented):
    prefix = "# " if commented else ""
    workflow = (
        "jobs:\n  deploy:\n    steps:\n      - run: |\n"
        f"          {prefix}cf api https://api.invalid\n"
        f"          {prefix}cf target -o prod -s prod\n"
        "          cf push checkout\n"
    )
    result = execute(tmp_path, CI.read_text(encoding="utf-8"), {".github/workflows/ci.yml": workflow}, ("cf-target",))
    assert result.returncode == (10 if commented else 0), result.stdout + result.stderr


def test_actual_go_missing_tool_is_supervised_unavailable(tmp_path):
    source = GO.read_text(encoding="utf-8").replace('found = shutil.which("go")', "found = None")
    result = execute(tmp_path, source, args=("server_timeouts",))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "go is not installed" in result.stdout


def test_cf_target_resolves_supported_literal_env_values():
    oracle = load_oracle(CI)
    job = {
        "env": {"API": "https://api.invalid", "ORG": "prod", "SPACE": "production space"},
        "steps": [{"run": 'cf api "$API"\ncf target -o "$ORG" -s "$SPACE"\ncf push checkout'}],
    }
    assert oracle._cf_target(job, {}) is None


@pytest.mark.parametrize("setup", ['echo "$UNSET"', 'echo "$(mktemp -d)"'])
def test_cf_target_does_not_resolve_unrelated_setup(setup):
    oracle = load_oracle(CI)
    job = {"steps": [{"run": setup + "\ncf api https://api.invalid\ncf target -o prod -s prod\ncf push checkout"}]}
    assert oracle._cf_target(job, {}) is None


class DeployOracleActionPolicyTests(unittest.TestCase):
    def test_deploy_oracle_action_policy(self) -> None:
        oracle = load_oracle(CI)
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


class ArtifactPromotionOracleTests(unittest.TestCase):
    """Run the real probe on the build scenario's manifest and workflow files; no shell executes."""

    ORACLE = CI
    SCENARIO = ROOT / "build-scenarios/build-software-engineer-adds-pcf-deploy-job.yaml"

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

    def assert_accepted(self, steps, **options):
        result = self.probe(steps, **options)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def assert_rejected(self, steps, reason, **options):
        """The probe fails the artifact-promoted case and its report names `reason`."""
        result = self.probe(steps, **options)
        self.assertEqual(10, result.returncode, result.stdout + result.stderr)
        self.assertIn(reason, result.stdout)

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
                self.assert_accepted([self.checkout(), self.download(path), push], **options)

    def test_checkout_path_and_step_shell_directory_are_resolved_separately(self):
        self.assert_accepted([
            self.checkout(path="source"), self.download("source/dist"),
            {"run": "cd source/dist"},
            {"run": "cf push checkout -f source/manifest.yml -p source/dist/checkout.zip"},
        ])
        self.assert_accepted([
            self.checkout(), self.download(None),
            {"run": "cf push checkout -f ../manifest.yml -p ../checkout.zip"},
        ], defaults={"working-directory": "dist"})

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
                self.assert_rejected([
                    self.checkout(), self.download(path), {"run": command},
                ], "artifact-promoted", env={"ARTIFACT_DIR": "dist"})

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
                self.assert_rejected([
                    self.checkout(), self.download(), {"run": command + "\ncf push checkout"},
                ], "unsupported")

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
                self.assert_rejected(steps, "artifact-promoted:")

    def test_opaque_trailing_pushes_and_option_substitutions_are_rejected(self):
        for trailing in (
            "bash -c 'cf push checkout -p /tmp/unrelated-bytes'",
            "./deploy-again.sh",
        ):
            for same_step in (False, True):
                with self.subTest(trailing=trailing, same_step=same_step):
                    runs = ([{"run": "cf push checkout\n" + trailing}] if same_step else
                            [{"run": "cf push checkout"}, {"run": trailing}])
                    self.assert_rejected([self.checkout(), self.download(), *runs], "unsupported")
        for option in ("--strategy", "-b", "-c"):
            with self.subTest(option=option):
                self.assert_rejected([
                    self.checkout(), self.download(),
                    {"run": f'cf push checkout {option} "$(cp /tmp/unrelated-bytes dist/checkout.zip)"'},
                ], "unsupported")
        self.assert_accepted([
            self.checkout(), self.download(),
            {"run": "cf push checkout\ncf app checkout"}, {"run": "echo deployment complete"},
        ])

    def test_modified_manifest_and_an_additional_bad_deploy_job_are_rejected(self):
        self.assert_rejected([
            self.checkout(), self.download(), {"run": "cf push checkout -p dist/checkout.zip"},
        ], "reviewed fixture manifest", manifest="applications:\n  - name: checkout\n    path: /tmp/unrelated\n")
        self.assert_rejected([
            self.checkout(), self.download(), {"run": "cf push checkout"},
        ], "job other: cf push payload", additional_jobs={"other": {"steps": [
            self.checkout(), self.download("ignored"), {"run": "cf push checkout"},
        ]}})

    def test_every_option_value_must_be_one_resolved_shell_word(self):
        for option in ("--strategy", "-b", "-m", "-i", "-k", "-t", "-c"):
            with self.subTest(option=option):
                self.assert_rejected([
                    self.checkout(), self.download(), {"run": f"cf push checkout {option} $BUILDPACK"},
                ], "unsupported", env={"BUILDPACK": "null -p /tmp/unrelated-bytes"})
        for value in (None, "", "*", "?", "[abc]"):
            with self.subTest(value=value):
                self.assert_rejected([
                    self.checkout(), self.download(), {"run": "cf push checkout -b $BUILDPACK"},
                ], "unsupported", env={} if value is None else {"BUILDPACK": value})
        for value in ("null -p /tmp/unrelated-bytes", "*", "?", "[abc]"):
            with self.subTest(quoted_value=value):
                self.assert_accepted([
                    self.checkout(), self.download(), {"run": 'cf push checkout -b "$BUILDPACK"'},
                ], env={"BUILDPACK": value})
        for option in ("--no-start", "--no-route", "--random-route", "--no-wait"):
            with self.subTest(inline_option=option):
                self.assert_rejected([
                    self.checkout(), self.download(), {"run": f"cf push checkout {option}=$FLAGS"},
                ], "unsupported", env={"FLAGS": "true -p /tmp/unrelated-bytes"})
        for value in ("true", "false"):
            with self.subTest(boolean_value=value):
                self.assert_accepted([
                    self.checkout(), self.download(), {"run": f"cf push checkout --no-start={value}"},
                ])
