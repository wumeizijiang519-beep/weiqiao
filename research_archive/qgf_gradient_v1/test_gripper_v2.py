import unittest

import numpy as np

from data_contract import normalized_executed_action as original_v1
from data_contract_v2 import normalized_executed_action, official_native_from_raw, validate_bank


class NativeV2Tests(unittest.TestCase):
    def bank(self):
        raw = np.random.default_rng(1).normal(size=(4, 32, 7)).astype(np.float32)
        raw[0, 12, -1] = 0
        scale = np.ones(7, dtype=np.float32)
        scale[-1] = 2
        offset = np.zeros(7, dtype=np.float32)
        offset[-1] = -1
        native = official_native_from_raw(raw, scale, offset)
        return native, raw, scale, offset

    def test_official_neutral_is_preserved_without_changing_v1(self):
        native, raw, scale, offset = self.bank()
        with self.assertRaises(ValueError):
            original_v1(native, scale, offset)
        normalized, report = validate_bank(native, raw, scale, offset)
        self.assertEqual(native[0, 12, -1], 0)
        self.assertEqual(normalized[0, 12, -1], 0)
        self.assertIn([0, 12], report['neutral_zero_locations'])

    def test_arbitrary_intermediate_or_wrong_raw_native_mapping_rejected(self):
        native, raw, scale, offset = self.bank()
        native[0, 0, -1] = .2
        with self.assertRaises(ValueError):
            normalized_executed_action(native, scale, offset)
        native, raw, scale, offset = self.bank()
        native[0, 0, 0] += .1
        with self.assertRaisesRegex(ValueError, 'mapping disagreement'):
            validate_bank(native, raw, scale, offset)


if __name__ == '__main__':
    unittest.main()
