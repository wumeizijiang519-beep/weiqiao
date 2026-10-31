import unittest

from audit_boundary_availability import EXPECTED_FAILURE


class BoundaryAvailabilityTests(unittest.TestCase):
    def test_failure_contract_is_exact_and_outcome_free(self):
        self.assertEqual(EXPECTED_FAILURE,
                         "Reconstructed boundary policy input differs from archive")
        self.assertNotIn("success", EXPECTED_FAILURE.lower())


if __name__ == "__main__":
    unittest.main()
