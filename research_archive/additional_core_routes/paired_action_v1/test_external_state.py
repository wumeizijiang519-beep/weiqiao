import unittest
import xml.etree.ElementTree as ET

from external_state import CallbackState, ExternalStateError, RendererRebuildState, StaticXmlState


class ExternalTests(unittest.TestCase):
    def test_static_xml_detects_mutation(self):
        node = ET.fromstring('<a><b x="1"/></a>')
        state = StaticXmlState(node)
        self.assertEqual(len(state.verify()), 64)
        node[0].set('x', '2')
        with self.assertRaises(ExternalStateError):
            state.verify()

    def test_callback_detects_closure_replacement(self):
        item = []
        def callback(value=1):
            return len(item) + value
        state = CallbackState(callback)
        self.assertEqual(len(state.verify()), 64)
        # Closure contents mutate through the state graph, while identity remains stable.
        item.append(1)
        self.assertEqual(len(state.verify()), 64)

    def test_renderer_rebuild_requires_equal_raster(self):
        holder = {'pixels': b'abc'}
        state = RendererRebuildState(lambda: None, lambda: holder['pixels'])
        self.assertEqual(len(state.restore()), 64)
        holder['pixels'] = b'def'
        with self.assertRaises(ExternalStateError):
            state.restore()


if __name__ == '__main__':
    unittest.main()
