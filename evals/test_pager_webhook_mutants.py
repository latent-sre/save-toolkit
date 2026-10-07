"""Each pager-webhook mutant fails the oracle check for the rule it breaks.

Kept apart from test_pager_webhook_oracle.py, which defines them, so that a run split by file gives
these, the slowest of the oracle's cases, a worker of their own.
"""

import pytest
from test_pager_webhook_oracle import MUTANTS, materialize, run


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_mutant_fails_its_check(tmp_path, name):
    # Each mutant must fail for the rule it breaks, not because the app crashed.
    check, overrides, reason = MUTANTS[name]
    result = run(materialize(tmp_path, overrides), check)
    assert result.returncode == 1, result.stdout + result.stderr
    assert reason in result.stdout, result.stdout + result.stderr
