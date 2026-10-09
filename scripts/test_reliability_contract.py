"""Authority regressions for the reliability design lane; no model calls."""

import unittest

from test_validate_fleet import DesignLaneAuthorityContract


class ReliabilityContractTests(DesignLaneAuthorityContract, unittest.TestCase):
    NAME = "reliability-engineer"


if __name__ == "__main__":
    unittest.main()
