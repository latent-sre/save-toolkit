# Python oracle reproduction evidence

[sourced] Sol independently ran both scratch-only cases against source identical to `8b4f9b785e520944319e04fd8e5018d4545b6800`. The combined script below preserves the two cases; it has not been rerun as a combined file. Run from the audited repository root with the existing project interpreter, `-B`, and `PYTHONDONTWRITEBYTECODE=1`. It uses existing calibration helpers and temporary artifacts; no install, network or candidate edit is required.

```python
"""Offline scratch-only reproductions; run with project Python -B."""
import gc
import importlib.util
import sys
from pathlib import Path

ROOT = Path.cwd().resolve()
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'evals'))

def helper(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

package = helper('audit_package', 'evals/test_python_package_refactor.py')
files = package.reference()
policy = package.POLICY.replace(
    '    for line in lines:',
    '    def forwarded():\n        yield from lines\n    for line in forwarded():',
)
files['order_report/calculation.py'] = policy
result = package.run_artifact(files)
print('AUDIT-PYTHON-001 FULL_PACKAGE_ORACLE_EXIT', result.returncode)
print(result.stdout, end='')
print(result.stderr, end='')
namespace = {}
exec(policy, namespace)
closed = []
def borrowed():
    try:
        yield 'malformed\n'
        yield 'posted,1,2\n'
    finally:
        closed.append(True)
source = borrowed()
try:
    namespace['total_from_lines'](source)
except ValueError:
    pass
gc.collect()
print('BORROWED_GENERATOR_CLOSED', closed)
print('REMAINING_LINES', list(source))

library = helper('audit_library', 'evals/test_python_library_selection_oracle.py')
changes = library.correct('schema') | {
    'batch.py': 'import validation\ndef load(schema, payloads):\n'
                '    return list(reversed([validation.validate_payload(schema, payload) '
                'for payload in payloads]))\n'
}
result = library.artifact('schema', changes)
print('AUDIT-PYTHON-002 REVERSED_BATCH_FULL_ORACLE_EXIT', result.returncode)
print(result.stdout, end='')
print(result.stderr, end='')
```

```text
Observed in the two original bounded executions against canonical-equivalent source:

FULL_PACKAGE_ORACLE_EXIT 0
package refactoring contracts passed
BORROWED_GENERATOR_CLOSED [True]
REMAINING_LINES []

REVERSED_BATCH_FULL_ORACLE_EXIT 0
library-selection contract passed: schema

Both enclosing Python commands exited 0. No stderr diagnostics were emitted.
The saved combined script has not been rerun; it preserves both original reproductions.
```
