"""Outcome identity must retain measurement state, including through ordinary Python containers."""

import copy
import pickle
from dataclasses import FrozenInstanceError

import pytest
from probe.outcomes import Outcome, State


def test_a_boolean_pair_cannot_make_failure_equal_to_an_unknown_measurement():
    failed = Outcome(State.FAIL, "same evidence")
    unknown = Outcome(State.INCONCLUSIVE, "same evidence")
    pair = (False, "same evidence")
    assert failed != unknown
    assert failed != pair and pair != failed
    assert unknown != pair and pair != unknown
    assert len({failed, unknown, pair}) == 3


def test_an_outcome_cannot_change_its_identity_after_assessment():
    outcome = Outcome(State.FAIL, "deployed", forbidden=True)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        outcome.state = State.PASS
    assert outcome.state is State.FAIL
    assert outcome.forbidden


def test_pair_readers_keep_working_without_discarding_the_outcome_identity():
    original = Outcome(State.INCONCLUSIVE, "instrument failed", machinery=True, forbidden=False)
    assert tuple(original) == (False, "instrument failed")
    assert original[0] is False
    assert original[1] == "instrument failed"
    for restored in (copy.deepcopy(original), pickle.loads(pickle.dumps(original))):
        assert restored == original
        assert restored.state is State.INCONCLUSIVE
        assert restored.machinery
