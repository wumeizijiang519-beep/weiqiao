import unittest
from collections import OrderedDict
import hashlib
import numpy as np
from state_graph import CoverageError, StateGraph


class Controller:
    pass


class GraphTests(unittest.TestCase):
    def test_ordered_dict_preserves_order_and_values(self):
        value = OrderedDict([('a', np.array([1, 2])), ('b', 3)])
        graph = StateGraph({'value': value}, {})
        value.move_to_end('a')
        value['b'] = 4
        graph.restore()
        self.assertEqual(list(value), ['a', 'b'])
        self.assertEqual(value['b'], 3)

    def test_none_dictionary_key_is_exactly_restored(self):
        value = {None: 4, 'named': 7}
        graph = StateGraph({'value': value}, {})
        value[None] = 9
        graph.restore()
        self.assertEqual(value, {None: 4, 'named': 7})

    def test_alias_cycle_cache_controller(self):
        c = Controller()
        c.goal = np.array([1., 2.])
        c.history = [c.goal]
        roots = {'controller': c, 'alias': c.goal}
        roots['self'] = roots
        graph = StateGraph(roots, {Controller: {'goal', 'history'}})
        c.goal[:] = 99
        c.goal = np.zeros(2)
        c.history.append('new')
        roots['new'] = 10
        graph.restore()
        self.assertIs(roots['self'], roots)
        self.assertIs(c.goal, roots['alias'])
        self.assertIs(c.goal, c.history[0])
        np.testing.assert_array_equal(c.goal, [1., 2.])
        self.assertEqual(len(c.history), 1)

    def test_unknown_object_rejected(self):
        with self.assertRaises(CoverageError):
            StateGraph({'controller': Controller()}, {})

    def test_unknown_field_rejected(self):
        c = Controller()
        c.new = 1
        with self.assertRaises(CoverageError):
            StateGraph(c, {Controller: set()})

    def test_postcapture_field_change_preflight(self):
        c = Controller()
        c.goal = np.ones(1)
        graph = StateGraph(c, {Controller: {'goal'}})
        c.new = 1
        c.goal[:] = 5
        with self.assertRaises(CoverageError):
            graph.restore()
        self.assertEqual(c.goal[0], 5)

    def test_external_must_match(self):
        handle = object()
        marker = [1]
        graph = StateGraph({'handle': handle}, {},
                           {id(handle): lambda _: hashlib.sha256(str(marker[0]).encode()).hexdigest()})
        marker[0] = 2
        with self.assertRaises(CoverageError):
            graph.restore()

    def test_mutable_external_signature_rejected(self):
        handle = object()
        with self.assertRaises(CoverageError):
            StateGraph(handle, {}, {id(handle): lambda _: []})

    def test_array_layout_change_rejected(self):
        a = np.arange(4.)
        graph = StateGraph(a, {})
        a.shape = (2, 2)
        with self.assertRaises(CoverageError):
            graph.restore()

    def test_object_array_rejected(self):
        with self.assertRaises(CoverageError):
            StateGraph(np.array([object()]), {})

    def test_numpy_scalar_and_nan_bits(self):
        roots = [np.float32(1), float('nan')]
        graph = StateGraph(roots, {})
        roots[:] = [2, 3]
        graph.restore()
        self.assertEqual(type(roots[0]), np.float32)
        self.assertTrue(np.isnan(roots[1]))

    def test_tuple_and_read_only_array(self):
        a = np.ones(2)
        a.flags.writeable = False
        roots = [(a,)]
        graph = StateGraph(roots, {})
        roots.clear()
        graph.restore()
        self.assertIs(roots[0][0], a)


if __name__ == '__main__':
    unittest.main()
