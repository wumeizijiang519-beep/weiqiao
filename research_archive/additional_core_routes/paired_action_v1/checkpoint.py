"""Ordered in-process checkpoint composition; no claim of runtime admission."""


class CompositeCheckpoint:
    def __init__(self, native, graph, rng, static_verifiers=(), renderer=None):
        self.native = native
        self.graph = graph
        self.rng = rng
        self.static_verifiers = tuple(static_verifiers)
        self.renderer = renderer

    def restore(self):
        # Native integration inputs first, then Python references/caches and RNG.
        self.native.restore()
        self.graph.restore()
        self.rng.restore()
        for verifier in self.static_verifiers:
            verifier.verify()
        raster = self.renderer.restore() if self.renderer is not None else None
        return {'native_exact': True, 'graph_exact': True, 'rng_exact': True,
                'static_verifiers': len(self.static_verifiers),
                'raster_sha256': raster}
