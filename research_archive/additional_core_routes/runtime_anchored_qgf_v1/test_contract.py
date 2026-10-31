import ast
import unittest
from pathlib import Path


class RuntimeAnchoredContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).with_name("run_single_group.py").read_text()
        ast.parse(cls.source)

    def test_legacy_image_mismatch_is_metadata_not_failure(self):
        self.assertNotIn('raise RuntimeError("Reconstructed boundary policy input differs from archive")',
                         self.source)
        self.assertIn("source_matches_legacy_archive_policy_input", self.source)

    def test_physics_and_commit_gates_remain(self):
        self.assertIn("Branch simulator state differs at boundary", self.source)
        self.assertIn("Branch proprioception differs at boundary", self.source)
        self.assertIn("Executed candidate prefix differs from bank", self.source)

    def test_new_registration_is_required(self):
        self.assertIn("RUNTIME_ANCHORED_QGF_V1_REGISTERED", self.source)
        self.assertIn("RUNTIME_ANCHORED_QGF_V1_GROUP_AUTHORIZED", self.source)


if __name__ == "__main__":
    unittest.main()
