import ast
from pathlib import Path
import unittest
import numpy as np

# Isolate the pure contract function from simulator/client imports on CPU.
source = ast.parse(Path(__file__).with_name('trajectory_collector.py').read_text())
node = next(node for node in source.body if isinstance(node, ast.FunctionDef)
            and node.name == 'transition_fields')
namespace = {'np': np}
exec(compile(ast.Module(body=[node], type_ignores=[]), '<transition_fields>', 'exec'), namespace)
transition_fields = namespace['transition_fields']


class TransitionTests(unittest.TestCase):
    def test_partial_last_chunk_success(self):
        result = transition_fields([0, 10], 13, 10, True, 1200)
        np.testing.assert_array_equal(result['executed_steps'], [10, 3])
        self.assertEqual(result['rewards'][1, 2], 1)
        self.assertEqual(result['rewards'].sum(), 1)
        np.testing.assert_array_equal(result['finite_horizon_terminal'], [False, True])

    def test_task_deadline_not_interruption(self):
        result = transition_fields([0, 10], 20, 10, False, 20)
        self.assertTrue(result['task_deadline_reached'])
        self.assertEqual(result['rewards'].sum(), 0)
        with self.assertRaises(ValueError):
            transition_fields([0, 10], 20, 10, False, 1200)

    def test_bad_lengths(self):
        for starts, end in (([0, 10], 10), ([0], 11), ([1], 2)):
            with self.assertRaises(ValueError):
                transition_fields(starts, end, 10, True, 1200)


if __name__ == '__main__':
    unittest.main()
