import copy
import unittest

import numpy as np

from run_replay_aba_gate_v1 import compare_trace


class ReplayTraceTest(unittest.TestCase):
    def trace(self):
        return {
            'steps': 2,
            'rewards': np.array([0.0, 1.0]),
            'done': np.array([False, True]),
            'success': np.array([False, True]),
            'proprio': np.arange(4, dtype=np.float64).reshape(2, 2),
            'native': np.arange(6, dtype=np.float64).reshape(2, 3),
            'env_state': np.arange(8, dtype=np.float64).reshape(2, 4),
            'rng': ['a', 'b'],
            'policy_raster': ['c', 'd'],
            'direct_raster': ['e', 'f'],
        }

    def test_exact_trace_passes(self):
        trace = self.trace()
        compare_trace(trace, copy.deepcopy(trace), 'repeat')

    def test_one_bit_difference_fails(self):
        first, second = self.trace(), self.trace()
        second['native'][1, 2] = np.nextafter(second['native'][1, 2], np.inf)
        with self.assertRaisesRegex(RuntimeError, 'native differs'):
            compare_trace(first, second, 'repeat')


if __name__ == '__main__':
    unittest.main()
