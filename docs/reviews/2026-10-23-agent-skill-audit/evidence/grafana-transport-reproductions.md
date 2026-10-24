# Grafana helper reproduction evidence

[verified] Source target: `8b4f9b785e520944319e04fd8e5018d4545b6800`. The transport reviewer reproduced both cases through the public CLI entry point using Python 3.14.8, fake HTTP, synthetic credentials and temporary packages. No network or live credentials were used.

Copy the following script to a temporary file and run it from the audited repository root with the existing project interpreter and `-I -B`. The optional Grafana dependencies must already be installed. This is retained audit evidence, not an installed helper or a repair.

```python
"""No-network reproductions for Grafana audit findings 003 and 004.

Run:
PYTHONDONTWRITEBYTECODE=1 /home/hawkfire/save-toolkit/.venv/bin/python -I -B /tmp/grafana-audit-transport-repros.py
"""
import importlib.util
import io
import json
import pathlib
import sys
import tempfile

source = pathlib.Path('skills/grafana/scripts/grafana_workflow.py').resolve()
spec = importlib.util.spec_from_file_location('audit_workflow', source)
w = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = w
spec.loader.exec_module(w)

# AUDIT-GRAFANA-003: recovery is appended after masking.
requests = []
def fake_large_dashboard(request, **bounds):
    requests.append(request.full_url)
    value = {'id': 1} if request.full_url.endswith('/api/org') else {
        'dashboard': {'uid': 'board', 'version': 1, 'panels': [{
            'id': 1, 'type': 'timeseries', 'title': 'x' * 600000,
            'datasource': {'uid': 'prom', 'type': 'prometheus'},
            'targets': [{'refId': 'A', 'expr': 'up'}]}]}, 'meta': {}}
    return 200, json.dumps(value).encode()

with tempfile.TemporaryDirectory(prefix='grafana-audit-') as tmp:
    dest = pathlib.Path(tmp) / 'synthetic-user'
    out = io.StringIO()
    code = w.main(['plan', '--uid', 'board', '--from', '1000', '--to', '2000',
                   '--output-dir', str(dest), '--agent-json'],
                  environ={'GRAFANA_URL': 'https://example.invalid', 'GRAFANA_ORG_ID': '1',
                           'GRAFANA_USERNAME': 'synthetic-user', 'GRAFANA_PASSWORD': 'synthetic-password'},
                  transport=fake_large_dashboard, output=out)
    result = json.loads(out.getvalue())
    print(json.dumps({'finding': 'AUDIT-GRAFANA-003', 'exit': code, 'status': result.get('status'),
                      'calls': len(requests), 'package_directory': result.get('package', {}).get('directory'),
                      'recovery_arguments': result.get('recovery', {}).get('arguments'),
                      'raw_synthetic_username_in_output': 'synthetic-user' in out.getvalue()}))

# AUDIT-GRAFANA-004: creation accepts a symlinked parent; readback rejects it.
requests = []
def fake_small_dashboard(request, **bounds):
    requests.append(request.full_url)
    value = {'id': 1} if request.full_url.endswith('/api/org') else {
        'dashboard': {'uid': 'board', 'version': 1, 'panels': []}, 'meta': {}}
    return 200, json.dumps(value).encode()

with tempfile.TemporaryDirectory(prefix='grafana-audit-') as tmp:
    root = pathlib.Path(tmp)
    (root / 'actual').mkdir()
    (root / 'linked').symlink_to(root / 'actual', target_is_directory=True)
    dest = root / 'linked' / 'capture'
    out = io.StringIO()
    argv = ['plan', '--uid', 'board', '--from', '1000', '--to', '2000',
            '--output-dir', str(dest), '--agent-json']
    env = {'GRAFANA_URL': 'https://example.invalid', 'GRAFANA_ORG_ID': '1',
           'GRAFANA_SA_TOKEN': 'synthetic-token'}
    code = w.main(argv, environ=env, transport=fake_small_dashboard, output=out)
    first = json.loads(out.getvalue())
    out = io.StringIO()
    second = w.main(argv, environ=env, transport=fake_small_dashboard, output=out)
    print(json.dumps({'finding': 'AUDIT-GRAFANA-004', 'exit': code, 'response': first,
                      'calls': len(requests), 'package_written': (dest / 'manifest.json').is_file(),
                      'incomplete_marker': (dest / '.incomplete').exists(), 'retry_exit': second,
                      'retry_response': json.loads(out.getvalue()),
                      'resolved_package_integrity': w._module('grafana_capture').verify_package(dest.resolve())['integrity']}))
```

[verified] Case 003 returned exit 0 and `output_truncated`, a redacted package directory, and a recovery argument containing `synthetic-user`. Case 004 returned exit 2 and `invalid_or_unavailable_evidence` after completing the package; retry returned `output_directory_exists`; verification through the resolved path returned `matches_manifest`.
