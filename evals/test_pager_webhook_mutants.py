"""Each pager-webhook mutant fails the oracle check for the rule it breaks: signature, ack and completion.

Kept apart from test_pager_webhook_oracle.py, which defines them, and split by check across three
files (MUTANT_FILE_CHECKS there), so that a run split by file gives these, the slowest of the
oracle's cases, workers of their own.
"""

from pathlib import Path

import pytest
from test_pager_webhook_oracle import assert_mutant_fails, mutants_checked_by


@pytest.mark.parametrize("name", mutants_checked_by(Path(__file__).name))
def test_mutant_fails_its_check(tmp_path, name):
    assert_mutant_fails(tmp_path, name)
