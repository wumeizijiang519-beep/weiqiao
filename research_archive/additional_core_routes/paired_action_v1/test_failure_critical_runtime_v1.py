import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np

import run_failure_critical_boundary_v1 as runtime


class RuntimeContractTest(unittest.TestCase):
    def test_branch_order_is_a_permutation(self):
        self.assertEqual(sorted(runtime.branch_order("group")), list(range(8)))
        self.assertEqual(runtime.branch_order("group"), runtime.branch_order("group"))

    def test_load_prefix_uses_actual_lengths_and_receipts(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            receipts = []
            expected = []
            for index, actual in enumerate((3, 2)):
                transition = root / f"transition_{index:04d}"
                transition.mkdir()
                actions = np.arange(35, dtype=np.float32).reshape(5, 7) + index * 100
                path = transition / "transition.npz"
                np.savez(path, actual_length=np.asarray(actual), executed_actions=actions)
                receipts.append({"index": index, "actual_length": actual,
                                 "sha256": runtime.disk_sha(path)})
                expected.extend(actions[:actual])
            expected = np.stack(expected)
            entry = {"boundary_replan": 2, "transition_receipts": receipts,
                     "prefix_steps": len(expected),
                     "prefix_actions_sha256": hashlib.sha256(expected.tobytes()).hexdigest()}
            np.testing.assert_array_equal(runtime.load_prefix(entry, root), expected)

    def test_load_prefix_fails_closed_on_receipt_change(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            transition = root / "transition_0000"
            transition.mkdir()
            path = transition / "transition.npz"
            np.savez(path, actual_length=np.asarray(1),
                     executed_actions=np.zeros((1, 7), dtype=np.float32))
            entry = {"boundary_replan": 1,
                     "transition_receipts": [{"index": 0, "actual_length": 1,
                                               "sha256": "0" * 64}],
                     "prefix_steps": 1, "prefix_actions_sha256": "0" * 64}
            with self.assertRaises(RuntimeError):
                runtime.load_prefix(entry, root)


if __name__ == "__main__":
    unittest.main()
