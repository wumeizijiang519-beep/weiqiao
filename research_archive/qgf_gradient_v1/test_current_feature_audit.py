import unittest

import numpy as np
import torch

from audit_current_features import audit_order, buffer_hashes
from data_contract import OBS_KEYS, capture_rng, rng_hash


def observation(value):
    return {key: np.full((2, 2, 3) if key.endswith('_image') else (3,), value,
                         dtype=np.uint8 if key.endswith('_image') else np.float32) for key in OBS_KEYS}


class CurrentFeatureAuditTests(unittest.TestCase):
    def cases(self):
        return (observation(1), 'A', 700), (observation(2), 'B', 300)

    def test_current_only_stateless_encoder_passes(self):
        def encode(obs, description, remaining):
            return np.asarray([obs['agentview_image'].mean(), remaining / 700], dtype=np.float32)
        values, report = audit_order(encode, *self.cases())
        self.assertEqual(report['feature_repeat_max_abs_error'], 0)
        np.testing.assert_array_equal(values[0], values[2])

    def test_hidden_temporal_state_rejected(self):
        counter = [0]
        def encode(*args):
            counter[0] += 1
            return np.asarray(counter, dtype=np.float32)
        with self.assertRaisesRegex(RuntimeError, 'temporal state'):
            audit_order(encode, *self.cases())

    def test_rng_mutation_rejected_and_caller_restored(self):
        before = rng_hash(capture_rng())
        def encode(*args):
            return np.asarray([np.random.random()], dtype=np.float32)
        with self.assertRaisesRegex(RuntimeError, 'caller'):
            audit_order(encode, *self.cases())
        self.assertEqual(before, rng_hash(capture_rng()))

    def test_input_mutation_rejected(self):
        def encode(obs, *args):
            obs['agentview_image'][0, 0, 0] += 1
            return np.zeros(2, dtype=np.float32)
        with self.assertRaisesRegex(RuntimeError, 'current observation'):
            audit_order(encode, *self.cases())

    def test_nonfinite_features_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'finite float32'):
            audit_order(lambda *args: np.asarray([np.nan], dtype=np.float32), *self.cases())

    def test_buffer_hashes_preserve_scalar_and_integer_bits(self):
        model = torch.nn.Module()
        model.register_buffer('scalar', torch.tensor(3, dtype=torch.int64))
        model.register_buffer('low_precision', torch.ones(3, dtype=torch.bfloat16))
        model.register_buffer('large_integer', torch.tensor([2 ** 60], dtype=torch.int64))
        before = buffer_hashes(model)
        model.large_integer.add_(1)
        after = buffer_hashes(model)
        self.assertEqual(before['scalar'], after['scalar'])
        self.assertNotEqual(before['large_integer'], after['large_integer'])


if __name__ == '__main__':
    unittest.main()
