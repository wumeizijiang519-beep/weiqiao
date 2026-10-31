import unittest
from checkpoint import CompositeCheckpoint


class Component:
    def __init__(self, name, calls):
        self.name, self.calls = name, calls
    def restore(self):
        self.calls.append(self.name)


class Verifier:
    def __init__(self, calls): self.calls = calls
    def verify(self): self.calls.append('static')


class Renderer:
    def __init__(self, calls): self.calls = calls
    def restore(self): self.calls.append('renderer'); return 'a' * 64


class CheckpointTest(unittest.TestCase):
    def test_order(self):
        calls = []
        checkpoint = CompositeCheckpoint(Component('native', calls), Component('graph', calls),
                                         Component('rng', calls), [Verifier(calls)], Renderer(calls))
        result = checkpoint.restore()
        self.assertEqual(calls, ['native', 'graph', 'rng', 'static', 'renderer'])
        self.assertEqual(result['raster_sha256'], 'a' * 64)


if __name__ == '__main__':
    unittest.main()
