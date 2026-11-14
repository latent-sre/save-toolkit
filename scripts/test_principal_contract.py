"""Authority regressions for the principal design lane; no model calls."""

import unittest

from test_validate_fleet import DesignLaneAuthorityContract


class PrincipalContractTests(DesignLaneAuthorityContract, unittest.TestCase):
    NAME = "principal-engineer"


if __name__ == "__main__":
    unittest.main()
