"""Each pager-webhook mutant that keeps work only in memory fails the oracle's durability check.

One of three files splitting the mutants by check; see test_pager_webhook_mutants.py.
"""

from pathlib import Path

import pytest
from test_pager_webhook_oracle import assert_mutant_fails, mutants_checked_by


@pytest.mark.parametrize("name", mutants_checked_by(Path(__file__).name))
def test_mutant_fails_its_check(tmp_path, name):
    assert_mutant_fails(tmp_path, name)
