"""Offline Docker lifecycle, bounded execution, and real temporary Git pruning checks."""

import io
import json
import subprocess

import pytest
from swebench_adapter import containers

from scripts.testkit import require_shell

DIGEST = "sha256:" + "a" * 64
BASE = "b" * 40


class FakeDocker:
    executable = "fake-docker"

    @property
    def argv(self):
        return [self.executable]

    def __init__(self):
        self.calls = []
        self.present = set()
        self.fail_create = False
        self.inspect_error = False
        self.size = 0

    def call(self, args, *, input=None, timeout=120, check=True):
        args = list(args)
        self.calls.append((args, input, timeout, check))
        stdout = b""
        code = 0
        if args[:2] == ["network", "create"]:
            self.present.add(args[-1])
            if self.fail_create:
                raise RuntimeError("creation failed")
        elif args[0] == "run":
            self.present.add(args[args.index("--name") + 1])
            if self.fail_create:
                raise RuntimeError("creation failed")
        elif args[0] == "rm" or args[:2] == ["network", "rm"]:
            self.present.discard(args[-1])
        elif args[0] == "inspect" and "--size" in args:
            if self.inspect_error:
                raise RuntimeError("inspect failed")
            stdout = json.dumps(self.size).encode()
        elif "inspect" in args and "--format" in args:
            stdout = b'"172.30.0.2"'
        elif "inspect" in args:
            if self.inspect_error:
                return subprocess.CompletedProcess(args, 1, b"", b"daemon unavailable")
            if args[-1] not in self.present:
                return subprocess.CompletedProcess(args, 1, b"", b"Error: No such object: " + args[-1].encode())
            stdout = b"[{}]"
        return subprocess.CompletedProcess(args, code, stdout, b"")


@pytest.fixture
def setup(tmp_path):
    cli = tmp_path / "claude"
    cli.write_bytes(b"fake pinned CLI")
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    docker = FakeDocker()
    resources = containers.DockerResources(docker, "wp08-attempt")
    return docker, resources, cli, plugin


def agent(setup, **kwargs):
    docker, resources, cli, plugin = setup
    if "wp08-attempt-network" not in docker.present:
        resources.internal_network()
    return resources.start_agent(
        "wp08-attempt-network",
        DIGEST,
        cli,
        plugin,
        {"ANTHROPIC_AUTH_TOKEN": "attempt-placeholder", "ANTHROPIC_API_KEY": ""},
        "172.30.0.2",
        storage_quota=kwargs.get("storage_quota", True),
    )


def test_docker_wrapper_uses_argv_and_sanitizes_failure(monkeypatch):
    captured = []

    def run(argv, **kwargs):
        captured.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 1, b"sk-or-private", b"sk-or-private")

    monkeypatch.setattr(containers.subprocess, "run", run)
    docker = containers.Docker("docker-pinned")
    with pytest.raises(RuntimeError) as error:
        docker.call(["exec", "owned", "printf", "$(touch forbidden)"])
    assert "sk-or-private" not in str(error.value)
    assert captured[0][0] == ["docker-pinned", "exec", "owned", "printf", "$(touch forbidden)"]
    assert captured[0][1].get("shell", False) is False
    assert captured[0][1]["timeout"] == 120
    assert docker.call(["version"], check=False).returncode == 1


def test_docker_timeout_and_os_errors_do_not_include_output_or_argv(monkeypatch):
    for failure in (subprocess.TimeoutExpired(["sk-or-secret"], 1, output=b"sk-or-secret"), OSError("sk-or-secret")):
        calls = []

        def run(*args, failure=failure, calls=calls, **kwargs):
            calls.append(args)
            raise failure

        monkeypatch.setattr(containers.subprocess, "run", run)
        with pytest.raises(RuntimeError) as error:
            containers.Docker().call(["sk-or-secret"])
        assert "sk-or-secret" not in str(error.value)
        assert len(calls) == 1


def test_internal_network_requires_isolated_bridge_mode_and_owns_partial_create(setup):
    docker, resources, _, _ = setup
    docker.fail_create = True
    with pytest.raises(RuntimeError):
        resources.internal_network()
    argv = next(args for args, *_ in docker.calls if args[:2] == ["network", "create"])
    assert "--internal" in argv
    assert "com.docker.network.bridge.gateway_mode_ipv4=isolated" in argv
    assert resources.cleanup() == [
        {"kind": "network", "name": "wp08-attempt-network", "present": False, "removed": True}
    ]


def test_agent_launch_has_only_readonly_tool_mounts_and_fixed_network(setup):
    docker, resources, cli, plugin = setup
    name = agent(setup, storage_quota=True)
    argv = next(args for args, *_ in docker.calls if args[0] == "run")
    assert name == "wp08-attempt-agent"
    for option, expected in [
        ("--cpus", "2"),
        ("--memory", "2g"),
        ("--pids-limit", "256"),
        ("--cap-drop", "ALL"),
        ("--security-opt", "no-new-privileges"),
        ("--dns", "127.0.0.1"),
        ("--add-host", "model-proxy:172.30.0.2"),
        ("--storage-opt", "size=10G"),
        ("--network", "wp08-attempt-network"),
    ]:
        assert argv[argv.index(option) + 1] == expected
    mounts = [argv[i + 1] for i, arg in enumerate(argv) if arg == "--mount"]
    assert mounts == [
        f"type=bind,source={cli.resolve()},target=/opt/claude,readonly",
        f"type=bind,source={plugin.resolve()},target=/opt/fleet,readonly",
    ]
    assert "docker.sock" not in " ".join(argv)
    assert "--privileged" not in argv
    assert resources.cleanup()[0]["present"] is False


@pytest.mark.parametrize("image", ["image:latest", "image:version", "sha256:bad", "-bad@" + DIGEST])
def test_mutable_or_invalid_image_is_rejected_before_allocating(setup, image):
    docker, resources, cli, plugin = setup
    with pytest.raises(ValueError):
        resources.start_agent("network", image, cli, plugin, {}, "172.30.0.2", storage_quota=True)
    assert docker.calls == []


@pytest.mark.parametrize("value", ["sk-or-secret", "sk-ant-secret", "ghp_secret", "AKIASECRET", "ya29.secret"])
def test_real_credential_markers_are_refused_before_launch(setup, value):
    docker, resources, cli, plugin = setup
    with pytest.raises(ValueError):
        resources.start_agent(
            "network", DIGEST, cli, plugin, {"ANTHROPIC_AUTH_TOKEN": value}, "172.30.0.2", storage_quota=True
        )
    assert docker.calls == []


def test_relay_has_fixed_target_no_forwarding_and_only_returns_internal_ip(setup):
    docker, resources, _, _ = setup
    network = resources.internal_network()
    address = resources.start_relay(network, "host.docker.internal", 40000)
    assert address == "172.30.0.2"
    run = next(args for args, *_ in docker.calls if args[0] == "run")
    assert run[run.index("--network") + 1] == "bridge"
    assert run[run.index("--sysctl") + 1] == "net.ipv4.ip_forward=0"
    assert run[run.index("--cap-drop") + 1] == "ALL"
    assert run[run.index("--cpus") + 1] == "2"
    assert run[-2:] == ["host.docker.internal", "40000"]
    assert containers.SERVICE_RELAY_SCRIPT in run
    assert containers.SERVICE_RELAY_IMAGE in run
    assert ["network", "connect", network, "wp08-attempt-relay"] in [args for args, *_ in docker.calls]
    receipt = resources.cleanup()
    assert [entry["kind"] for entry in receipt] == ["container", "network"]
    assert all(entry["removed"] and entry["present"] is False for entry in receipt)


def test_cleanup_inspection_errors_are_unknown_and_do_not_stop_other_resources(setup):
    docker, resources, _, _ = setup
    resources.internal_network()
    agent(setup)
    docker.inspect_error = True
    receipt = resources.cleanup()
    assert [entry["kind"] for entry in receipt] == ["container", "network"]
    assert all(entry["present"] is None and entry["removed"] for entry in receipt)


def git(directory, *argv):
    result = subprocess.run(["git", "-C", str(directory), *argv], check=True, capture_output=True)
    return result.stdout.decode().strip()


def test_git_prune_script_removes_future_hidden_refs_remotes_and_reflogs(tmp_path):
    repo = tmp_path / "testbed"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "user.name", "Offline test")
    (repo / "tracked").write_text("base")
    git(repo, "add", "tracked")
    git(repo, "commit", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "tracked").write_text("future gold")
    git(repo, "commit", "-am", "future")
    future = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/hidden/future", future)
    git(repo, "update-ref", "refs/original/future", future)
    git(repo, "tag", "future", future)
    git(repo, "replace", base, future)
    git(repo, "remote", "add", "origin", "https://example.invalid/repo")
    git(repo, "update-ref", "refs/remotes/origin/main", future)
    (repo / ".git" / "ORIG_HEAD").write_text(future + "\n")
    (repo / "untracked").write_text("remove")
    script = containers.git_prune_script(base)
    assert "\r" not in script
    # Only replace the fixed image workdir for the real temporary Git fixture.
    script = script.replace("cd /testbed", 'cd "' + repo.as_posix() + '"')
    subprocess.run([require_shell("sh"), "-s"], input=script.encode(), check=True, capture_output=True)
    assert git(repo, "rev-parse", "HEAD") == base
    assert git(repo, "for-each-ref") == ""
    assert git(repo, "remote") == ""
    assert git(repo, "rev-list", "--all", "--not", base) == ""
    assert (repo / "tracked").read_text() == "base"
    assert not (repo / "untracked").exists()
    future_check = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", future], capture_output=True)
    assert future_check.returncode != 0
    assert subprocess.run(["git", "-C", str(repo), "symbolic-ref", "-q", "HEAD"], capture_output=True).returncode != 0


def test_repository_setup_uses_stdin_script_and_rejects_mutable_base(setup):
    docker, resources, _, _ = setup
    name = agent(setup)
    resources.setup_repository(name, BASE)
    argv, data, _, _ = docker.calls[-1]
    assert argv == ["exec", "-i", name, "/bin/sh", "-s"]
    assert data == containers.git_prune_script(BASE).encode()
    with pytest.raises(ValueError):
        resources.setup_repository(name, "main; touch /bad")


class FakeProcess:
    def __init__(self, stdout=b"hello", stderr=b"note", running=False):
        self.stdout = io.BytesIO(stdout)
        self.stderr = io.BytesIO(stderr)
        self.running = running
        self.returncode = None if running else 0
        self.killed = False
        self.interrupt = False

    def poll(self):
        if self.interrupt:
            raise KeyboardInterrupt
        return None if self.running else self.returncode

    def kill(self):
        self.killed = True
        self.running = False
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


def fake_process(monkeypatch, process):
    calls = []

    def popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return process

    monkeypatch.setattr(containers.subprocess, "Popen", popen)
    return calls


def test_execution_collects_bounded_bytes_without_shell(setup, monkeypatch):
    _, resources, _, _ = setup
    name = agent(setup)
    calls = fake_process(monkeypatch, FakeProcess())
    result = resources.execute(name, ["/opt/claude", "--version"], storage_quota=True)
    assert result.stdout == b"hello" and result.stderr == b"note"
    assert result.returncode == 0 and result.stop is None and result.seconds >= 0
    assert calls[0][0] == ["fake-docker", "exec", name, "/opt/claude", "--version"]
    assert calls[0][1].get("shell", False) is False


@pytest.mark.parametrize("stream,limit", [("stdout", 64 * 1024 * 1024), ("stderr", 1024 * 1024)])
def test_output_overflow_stops_and_removes_container(setup, monkeypatch, stream, limit):
    docker, resources, _, _ = setup
    name = agent(setup)
    process = FakeProcess(**{stream: b"x" * (limit + 1)})
    fake_process(monkeypatch, process)
    result = resources.execute(name, ["command"], storage_quota=True)
    assert result.stop == "output_limit"
    assert len(getattr(result, stream)) == limit
    assert ["rm", "--force", name] in [args for args, *_ in docker.calls]


def test_wall_clock_stops_process_and_container(setup, monkeypatch):
    docker, resources, _, _ = setup
    name = agent(setup)
    process = FakeProcess(running=True)
    fake_process(monkeypatch, process)
    result = resources.execute(name, ["command"], wall_seconds=0.01, storage_quota=True)
    assert result.stop == "wall_clock" and process.killed
    assert ["rm", "--force", name] in [args for args, *_ in docker.calls]


@pytest.mark.parametrize(
    "size,expected", [(10_737_418_241, "storage_limit"), (None, "monitor_failure"), (-1, "monitor_failure")]
)
def test_exact_writable_layer_watchdog_fails_closed(setup, monkeypatch, size, expected):
    docker, resources, _, _ = setup
    name = agent(setup)
    docker.size = size
    process = FakeProcess(running=True)
    fake_process(monkeypatch, process)
    result = resources.execute(name, ["command"], wall_seconds=0.2, storage_quota=False)
    assert result.stop == expected and process.killed
    assert any(args[:2] == ["inspect", "--size"] for args, *_ in docker.calls)


def test_monitor_command_failure_is_not_treated_as_zero_storage(setup, monkeypatch):
    docker, resources, _, _ = setup
    name = agent(setup)
    docker.inspect_error = True
    process = FakeProcess(running=True)
    fake_process(monkeypatch, process)
    assert resources.execute(name, ["command"], storage_quota=False).stop == "monitor_failure"


def test_interruption_stops_process_and_container(setup, monkeypatch):
    _, resources, _, _ = setup
    name = agent(setup)
    process = FakeProcess(running=True)
    fake_process(monkeypatch, process)
    process.interrupt = True
    result = resources.execute(name, ["command"], storage_quota=True)
    assert result.stop == "interrupted" and process.killed
    assert resources.cleanup()[0]["present"] is False


def test_cleanup_only_removes_owned_resources(setup):
    docker, resources, _, _ = setup
    docker.present.add("unrelated")
    resources.internal_network()
    agent(setup)
    resources.cleanup()
    assert "unrelated" in docker.present
    with pytest.raises(ValueError):
        resources.setup_repository("unrelated", BASE)
    with pytest.raises(ValueError):
        resources.execute("unrelated", ["command"])


def test_preexisting_resource_is_never_claimed_or_removed(setup):
    docker, resources, _, _ = setup
    docker.present.add("wp08-attempt-network")
    with pytest.raises(RuntimeError, match="exist"):
        resources.internal_network()
    assert resources.cleanup() == []
    assert "wp08-attempt-network" in docker.present


def test_fast_execution_still_checks_storage_before_return(setup, monkeypatch):
    docker, resources, _, _ = setup
    name = agent(setup)
    docker.size = containers.STORAGE_LIMIT + 1
    process = FakeProcess()
    fake_process(monkeypatch, process)
    result = resources.execute(name, ["command"], storage_quota=False)
    assert result.stop == "storage_limit"


def test_failed_agent_creation_is_still_owned_for_cleanup(setup):
    docker, resources, _, _ = setup
    resources.internal_network()
    docker.fail_create = True
    with pytest.raises(RuntimeError):
        agent(setup)
    launches = [args for args, *_ in docker.calls if args[0] == "run"]
    assert len(launches) == 1
    assert launches[0][launches[0].index("--storage-opt") + 1] == "size=10G"
    assert [entry["kind"] for entry in resources.cleanup()] == ["container", "network"]
    assert docker.present == set()


@pytest.mark.parametrize("endpoint", ["unix:///var/run/docker.sock", "npipe:////./pipe/docker_engine"])
def test_daemon_pin_is_stable_and_argv_cannot_mutate_it(endpoint):
    docker = containers.Docker("docker-pinned")
    assert docker.argv == ["docker-pinned"]
    docker.pin(endpoint)
    docker.pin(endpoint)
    assert docker.argv == ["docker-pinned", "--host", endpoint]
    detached = docker.argv
    detached[-1] = "tcp://remote.invalid:2375"
    assert docker.argv[-1] == endpoint
    with pytest.raises(AttributeError):
        docker.argv = ["other-docker"]
    with pytest.raises(ValueError):
        docker.pin("unix:///run/other.sock")
    assert docker.argv[-1] == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "tcp://remote.invalid:2375",
        "ssh://user@remote.invalid",
        "http://remote.invalid",
        "unix://remote.invalid/docker.sock",
        "unix://user:secret@localhost/socket",
        "unix:///run/docker.sock?credential=secret",
        "unix:///run/docker.sock#secret",
        "unix:///run/sk-or-secret.sock",
        "unix:///run/docker.sock\n",
        "unix:///run/docker\x00.sock",
        "npipe:////remote/pipe/docker_engine",
        "npipe:////./pipe/docker_engine\r",
        "",
        None,
    ],
)
def test_daemon_pin_refuses_remote_or_credential_bearing_endpoints(endpoint):
    docker = containers.Docker()
    with pytest.raises(ValueError):
        docker.pin(endpoint)
    assert docker.argv == ["docker"]


def test_all_owned_commands_and_exec_stay_on_bound_daemon_after_context_changes(setup, monkeypatch):
    _, _, cli, plugin = setup
    boundary = FakeDocker()
    invoked = []
    endpoint = "unix:///var/run/docker.sock"

    def run(argv, **kwargs):
        invoked.append(list(argv))
        return boundary.call(argv[3:], input=kwargs.get("input"), timeout=kwargs["timeout"], check=False)

    monkeypatch.setattr(containers.subprocess, "run", run)
    docker = containers.Docker("docker-pinned")
    docker.pin(endpoint)
    monkeypatch.setenv("DOCKER_HOST", "tcp://other.invalid:2375")
    monkeypatch.setenv("DOCKER_CONTEXT", "different-context")
    monkeypatch.setenv("DOCKER_TLS_VERIFY", "1")
    resources = containers.DockerResources(docker, "bound-attempt")
    network = resources.internal_network()
    proxy_ip = resources.start_relay(network, "host.docker.internal", 40000)
    name = resources.start_agent(
        network, DIGEST, cli, plugin, {"ANTHROPIC_AUTH_TOKEN": "attempt-placeholder"}, proxy_ip, storage_quota=True
    )
    resources.setup_repository(name, BASE)
    process_calls = fake_process(monkeypatch, FakeProcess())
    result = resources.execute(name, ["/opt/claude", "--version"], storage_quota=False)
    receipt = resources.cleanup()
    assert result.stop is None
    assert all(entry["present"] is False for entry in receipt)
    assert invoked and all(argv[:3] == ["docker-pinned", "--host", endpoint] for argv in invoked)
    assert process_calls[0][0] == ["docker-pinned", "--host", endpoint, "exec", name, "/opt/claude", "--version"]


def test_watchdog_accepts_the_exact_binary_docker_quota(setup, monkeypatch):
    docker, resources, _, _ = setup
    name = agent(setup)
    docker.size = 10_737_418_240
    process = FakeProcess()
    fake_process(monkeypatch, process)
    result = resources.execute(name, ["command"], storage_quota=False)
    assert result.stop is None
    assert not process.killed


@pytest.mark.parametrize("quota", [False, None, 1, "true"])
def test_agent_rejects_missing_hard_quota_before_docker(setup, quota):
    docker, resources, cli, plugin = setup
    with pytest.raises(ValueError, match="hard storage quota"):
        resources.start_agent("network", DIGEST, cli, plugin, {}, "172.30.0.2", storage_quota=quota)
    assert docker.calls == []
