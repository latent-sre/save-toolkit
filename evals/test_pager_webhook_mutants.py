"""Each pager-webhook mutant fails the oracle check for the rule it breaks.

Kept apart from test_pager_webhook_oracle.py, which defines them, so the heavy CI shard's
worksteal scheduling spreads these, the slowest of the oracle's cases, across workers.
"""

import pytest
from test_pager_webhook_oracle import MUTANTS, assert_mutant_fails


@pytest.mark.parametrize("name", sorted(MUTANTS))
def test_mutant_fails_its_check(tmp_path, name):
    assert_mutant_fails(tmp_path, name)
