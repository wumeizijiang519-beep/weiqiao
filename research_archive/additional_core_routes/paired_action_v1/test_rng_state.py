import random
import unittest
import numpy as np
from rng_state import RngState, signature


class RngTests(unittest.TestCase):
    def test_global_and_local_repeat(self):
        local = {'selection': np.random.default_rng(42),
                 'noise': np.random.RandomState(43), 'python': random.Random(44)}
        snap = RngState(local)
        def sample():
            return (random.random(), np.random.random(), local['selection'].random(),
                    local['noise'].random(), local['python'].random())
        a = sample()
        sample()
        snap.restore()
        self.assertEqual(a, sample())

    def test_snapshot_immutable(self):
        generator = np.random.default_rng(42)
        snap = RngState({'generator': generator})
        digest = signature(snap.state)
        generator.random(10)
        self.assertEqual(digest, signature(snap.state))

    def test_registry_change_rejected(self):
        local = {'selection': np.random.default_rng(42)}
        snap = RngState(local)
        local['selection'] = np.random.default_rng(42)
        with self.assertRaises(RuntimeError):
            snap.restore()

    def test_unknown_rng_rejected(self):
        with self.assertRaises(TypeError):
            RngState({'unknown': object()})


if __name__ == '__main__':
    unittest.main()
