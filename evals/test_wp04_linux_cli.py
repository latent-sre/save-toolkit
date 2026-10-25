"""Model-free controls for the WP04 Linux read-only CLI boundary."""

import json
import os
import shutil
import subprocess
import sys

import pytest
import wp04_linux_cli as boundary


def layout(tmp_path):
    root = tmp_path / 'trial'
    repo, plugin, config = root / 'repo', root / 'plugin', tmp_path / 'auth-copy'
    for path in (repo, plugin, config):
        path.mkdir(parents=True)
    (repo / 'observation.txt').write_text('visible observation')
    (plugin / 'guidance.md').write_text('trusted guidance')
    return repo, plugin, config


def test_rejects_tool_or_path_expansion_before_launch(tmp_path):
    repo, plugin, config = layout(tmp_path)
    args = ['--agent', 'sre-assistant', '-p', 'task', '--plugin-dir', str(plugin),
            '--tools', 'Read,Grep,Glob,Skill', '--add-dir', str(plugin)]
    boundary.validate_profile(args, repo, config)
    for changed in [[*args, '--tools', 'Bash'], [*args, '--add-dir', str(tmp_path)],
                    [x.replace('Read,Grep,Glob,Skill', 'Read,Bash') for x in args],
                    [*args, '--resume', 'old-session']]:
        with pytest.raises(ValueError):
            boundary.validate_profile(changed, repo, config)


@pytest.mark.skipif(sys.platform != 'linux' or not shutil.which('bwrap'), reason='Linux bubblewrap required')
def test_real_namespace_hides_evaluator_and_keeps_only_observed_inputs(tmp_path):
    repo, plugin, config = layout(tmp_path)
    hidden = tmp_path / 'ground-truth.json'
    hidden.write_text('must not be exposed')
    script = (
        'import json,os,tempfile; from pathlib import Path; '
        f'p=Path({str(repo)!r}); h=Path({str(hidden)!r}); '
        'result={"read":(p/"observation.txt").read_text(),"hidden":h.exists()}; '
        '\ntry: (p/"write.txt").write_text("bad")\n'
        'except OSError: result["readonly"]=True\n'
        'else: result["readonly"]=False\n'
        'result["temp_env"]=all(os.environ.get(k)=="/tmp" for k in ("TMP","TEMP","TMPDIR"))\n'
        'with tempfile.TemporaryFile() as f: f.write(b"ok")\n'
        'print(json.dumps(result))'
    )
    command = boundary.namespace_command(['/usr/bin/python3', '-c', script], repo, plugin, config)
    env = {**os.environ, **dict.fromkeys(('TMP', 'TEMP', 'TMPDIR'), str(tmp_path / 'unmounted-tmp'))}
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, env=env)
    if result.returncode and ('Operation not permitted' in result.stderr or 'No permissions' in result.stderr):
        pytest.skip('host disallows unprivileged namespaces')
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {'read': 'visible observation', 'hidden': False,
                                       'readonly': True, 'temp_env': True}
    assert hidden.read_text() == 'must not be exposed'
