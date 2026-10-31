import unittest

import numpy as np

from candidate_bank import build_bank, native_from_normalized, normalized_executed_action


class CandidateBankTest(unittest.TestCase):
    def fixture(self):
        rng = np.random.default_rng(11)
        native = rng.normal(scale=0.05, size=(4, 32, 7)).astype(np.float32)
        native[..., -1] = np.asarray([-1, 0, 1, -1])[:, None]
        scale = np.ones(7, dtype=np.float32)
        offset = np.zeros(7, dtype=np.float32)
        raw = native.copy()
        raw[..., -1] = (1 - native[..., -1]) / 2
        basis = np.zeros((3, 32, 6), dtype=np.float32)
        basis[0, :, 0] = 1 / np.sqrt(32)
        basis[1, :, 1] = 1 / np.sqrt(32)
        basis[2, :, 2] = 1 / np.sqrt(32)
        return native, raw, scale, offset, basis

    def test_bank_is_unique_and_preserves_gripper(self):
        values = self.fixture()
        result = build_bank(*values, median_norm=0.2, p95_norm=0.4)
        self.assertEqual(result["native"].shape, (8, 32, 7))
        self.assertEqual(len(set(result["hashes"])), 8)
        expected = np.broadcast_to(values[0][0, :, -1], (4, 32))
        np.testing.assert_array_equal(result["native"][4:, :, -1], expected)
        np.testing.assert_allclose(result["structured_delta_norms"], 0.2, atol=1e-6)

    def test_invalid_support_radius_fails(self):
        values = self.fixture()
        with self.assertRaises(RuntimeError):
            build_bank(*values, median_norm=0.5, p95_norm=0.4)

    def test_official_affine_roundtrip_including_neutral_gripper(self):
        native, _, scale, offset, _ = self.fixture()
        normalized = normalized_executed_action(native, scale, offset)
        np.testing.assert_array_equal(native_from_normalized(normalized, scale, offset), native)


if __name__ == "__main__":
    unittest.main()
