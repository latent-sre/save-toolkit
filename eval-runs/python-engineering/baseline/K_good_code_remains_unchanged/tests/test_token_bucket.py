import pytest
from token_bucket import TokenBucket

def test_token_bucket_refill_and_bound():
    now = 0.0
    bucket = TokenBucket(capacity=2.0, refill_rate=1.0, clock=lambda: now)
    assert bucket.allow(2.0) is True
    assert bucket.allow(1.0) is False
    now = 1.5
    assert bucket.allow(1.0) is True
    assert bucket.allow(1.0) is False
