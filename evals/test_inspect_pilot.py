"""Offline contract checks; real agent/model acceptance is a separate run."""

import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import yaml
from inspect_ai import eval as inspect_eval
from inspect_ai.model import ChatCompletionChoice, ChatMessageAssistant, ModelOutput, get_model
from inspect_ai.solver import solver
from inspect_ai.tool import ToolCall
from inspect_ai.util import sandbox

import inspect_pilot as pilot


@pytest.fixture
def box(monkeypatch):
    box = SimpleNamespace(
        exec=AsyncMock(return_value=SimpleNamespace(success=True, returncode=0, stdout="alpha 4", stderr="")),
        write_file=AsyncMock(),
    )
    monkeypatch.setattr(pilot, "sandbox", lambda: box)
    return box


def run_score(checks):
    return asyncio.run(pilot.artifact_checks(checks)(None, None))


def test_task_reuses_fixture_and_exposes_omissions():
    spec, checks, omitted = pilot.pilot_spec()
    task = pilot.wordfreq()
    assert task.dataset[0].input == spec["prompt"]
    assert len(checks) == 7
    assert len(omitted) == 9
    assert task.metadata["omitted_checks"] == omitted
    assert task.metadata["native_fleet_parity"] is False
    assert task.token_limit == 20000
    assert task.time_limit == 300
    assert task.cost_limit == 1.0


def test_grader_system_paths_are_read_only():
    service = yaml.safe_load(pilot.COMPOSE.read_text(encoding="utf-8"))["services"]["default"]
    assert service["cap_drop"] == ["ALL"] and not service.get("cap_add")
    assert service["read_only"] is True
    assert service["environment"]["PATH"] == "/usr/local/bin:/usr/bin:/bin"


@pytest.mark.parametrize("success,output,expected", [
    (True, "alpha 4", 1), (True, "alpha 3", 0), (False, "alpha 4", 0),
])
def test_output_check_requires_exit_success_and_matching_output(box, success, output, expected):
    box.exec.return_value = SimpleNamespace(success=success, returncode=0 if success else 1, stdout=output, stderr="")
    result = run_score([{"check": "command_output_regex", "command": "python tool.py", "pattern": "alpha 4", "text": "ranking", "writes": {"oracle.txt": "known input"}}])
    assert result.value == expected
    box.write_file.assert_awaited_once_with("oracle.txt", "known input")


def test_timeout_remains_an_error(box):
    box.exec.side_effect = TimeoutError("sandbox unavailable")
    with pytest.raises(TimeoutError):
        run_score([{"check": "file_exists", "path": "tool.py", "text": "exists"}])


def test_unsupported_check_is_not_silently_passed(box):
    with pytest.raises(ValueError, match="unsupported"):
        run_score([{"check": "skill_loaded", "text": "native behavior"}])


@solver
def no_agent():
    async def solve(state, generate):
        return state
    return solve


def test_inspect_writes_real_offline_log(box, tmp_path):
    task = pilot.wordfreq()
    task.sandbox = None
    task.cost_limit = None  # No model requests; mockllm has no price catalog entry.
    task.dataset[0].setup = None
    task.solver = no_agent()
    task.scorer = [pilot.artifact_checks([{"check": "file_exists", "path": "tool.py", "text": "exists"}])]
    logs = inspect_eval(task, model="mockllm/model", log_dir=str(tmp_path), display="none")
    assert logs[0].status == "success"
    assert logs[0].samples[0].scores["artifact_checks"].value == 1
    assert list(tmp_path.glob("*.eval"))


@pytest.mark.skipif(os.environ.get("RUN_INSPECT_DOCKER_SMOKE") != "1",
                    reason="opt-in Docker/Claude download smoke; no paid model calls")
@pytest.mark.parametrize("create_solution,expected", [(False, 0), (True, 1)])
def test_real_swe_bridge_with_mock_model(create_solution, expected):
    files = {
        "scripts/wordfreq.py": """import argparse
from collections import Counter
from pathlib import Path
def count(text):
    return Counter(text.lower().split()).most_common(10)
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    for word, total in count(Path(args.path).read_text(encoding='utf-8')):
        print(word, total)
if __name__ == '__main__':
    main()
""",
        "tests/test_wordfreq.py": """import unittest
from scripts.wordfreq import count
class WordfreqTests(unittest.TestCase):
    def test_count(self):
        self.assertEqual(count('one one two'), [('one', 2), ('two', 1)])
    def test_empty(self):
        self.assertEqual(count(''), [])
""",
    }
    command = "python - <<'PY'\nimport json\nfrom pathlib import Path\n"
    command += f"files = json.loads({json.dumps(files)!r})\n"
    command += "for name, content in files.items():\n Path(name).write_text(content, encoding='utf-8')\nPY\n"

    def scripted_output(messages, tools, tool_choice, config):
        already_called = any(isinstance(message, ChatMessageAssistant) and message.tool_calls
                             for message in messages)
        if create_solution and not already_called and any(tool.name == "Bash" for tool in tools):
            return ModelOutput(model="mockllm", choices=[ChatCompletionChoice(
                message=ChatMessageAssistant(content="", tool_calls=[ToolCall(
                    id="call_fixture", function="Bash", arguments={"command": command})]),
                stop_reason="tool_calls")])
        return ModelOutput.from_content("mockllm", "Scripted bridge test complete.")

    model = get_model("mockllm/claude-sonnet-4-5", custom_outputs=scripted_output, memoize=False)
    task = pilot.wordfreq()
    task.cost_limit = None  # The scripted provider cannot make paid model calls.
    logs = inspect_eval(task, model=model, log_dir=str(pilot.ROOT / ".eval-runs/inspect-smoke"),
                        display="none", max_connections=1)
    assert logs[0].status == "success", logs[0].error
    assert logs[0].samples[0].scores["artifact_checks"].value == expected


@solver
def tamper_with_grader():
    async def solve(state, generate):
        attack = """import json
from pathlib import Path
replaced = []
for name in ['/usr/local/bin/python', '/usr/bin/test', '/bin/bash']:
    path = Path(name)
    try:
        path.unlink()
        path.write_text('#!/bin/sh\\necho "alpha 4 beta 3 gamma 2 delta 1 wordfreq ... ok"\\nexit 0\\n')
        path.chmod(0o755)
        replaced.append(name)
    except OSError:
        pass
print(json.dumps({'replaced': replaced, 'cap_eff': next(line.split()[1] for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:'))}))
"""
        result = await sandbox().exec(["/usr/local/bin/python", "-c", attack])
        assert result.success, result.stderr
        state.metadata["runtime_probe"] = json.loads(result.stdout)
        return state
    return solve


@pytest.mark.skipif(os.environ.get("RUN_INSPECT_DOCKER_SMOKE") != "1",
                    reason="opt-in Docker test of grader executable immutability")
def test_real_swe_grader_rejects_runtime_tampering():
    task = pilot.wordfreq()
    task.solver = tamper_with_grader()
    task.cost_limit = None
    logs = inspect_eval(task, model="mockllm/model", display="none",
                        log_dir=str(pilot.ROOT / ".eval-runs/inspect-smoke"))
    assert logs[0].status == "success", logs[0].error
    sample = logs[0].samples[0]
    assert sample.metadata["runtime_probe"]["replaced"] == []
    assert int(sample.metadata["runtime_probe"]["cap_eff"], 16) == 0
    assert sample.scores["artifact_checks"].value == 0
