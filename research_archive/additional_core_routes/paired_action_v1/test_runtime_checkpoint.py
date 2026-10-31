import unittest
from collections import OrderedDict
import numpy as np

from runtime_checkpoint import RuntimeCheckpoint


class Unsupported:
    __slots__ = ('value',)
    def __init__(self): self.value = 1


class RuntimeCheckpointDiscoveryTest(unittest.TestCase):
    def test_unknown_slot_object_fails_closed(self):
        checkpoint = RuntimeCheckpoint.__new__(RuntimeCheckpoint)
        checkpoint._seen = set()
        checkpoint.schemas = {}
        checkpoint.externals = {}
        checkpoint.static_states = []
        checkpoint.native = type('N', (), {'current': lambda self: np.zeros(1)})()
        checkpoint.model_state = type('M', (), {'current': lambda self: '0' * 64})()
        with self.assertRaisesRegex(RuntimeError, 'Unhandled native type'):
            checkpoint._discover(Unsupported(), 'root')

    def test_inconsistent_same_type_schema_fails(self):
        class Mutable: pass
        first, second = Mutable(), Mutable()
        first.a = 1
        second.b = 2
        root = {'first': first, 'second': second}
        checkpoint = RuntimeCheckpoint.__new__(RuntimeCheckpoint)
        checkpoint._seen = set()
        checkpoint.schemas = {}
        checkpoint.externals = {}
        checkpoint.static_states = []
        checkpoint.native = type('N', (), {'current': lambda self: np.zeros(1)})()
        checkpoint.model_state = type('M', (), {'current': lambda self: '0' * 64})()
        with self.assertRaisesRegex(RuntimeError, 'Inconsistent field schema'):
            checkpoint._discover(root, 'root')

    def test_dynamic_cache_values_are_content_addressed(self):
        checkpoint = RuntimeCheckpoint.__new__(RuntimeCheckpoint)
        checkpoint.graph = type('Graph', (), {'nodes': {}})()
        value = OrderedDict([
            ('obs', np.arange(6, dtype=np.float32).reshape(2, 3)),
            ('meta', {'done': False, None: [1, 2, 3]}),
        ])
        first = checkpoint._live_token(value)
        self.assertEqual(first, checkpoint._live_token(value))
        value['obs'][0, 0] = 9
        self.assertNotEqual(first, checkpoint._live_token(value))

    def test_dynamic_aliases_do_not_depend_on_memory_address(self):
        checkpoint = RuntimeCheckpoint.__new__(RuntimeCheckpoint)
        checkpoint.graph = type('Graph', (), {'nodes': {}})()
        left = []
        left.append(left)
        right = []
        right.append(right)
        self.assertEqual(checkpoint._live_token(left), checkpoint._live_token(right))


if __name__ == '__main__':
    unittest.main()
