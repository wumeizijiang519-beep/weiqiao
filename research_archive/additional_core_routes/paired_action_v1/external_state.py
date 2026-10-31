"""Explicit adapters for state that must not be blindly deep-copied."""
import hashlib
import json
import marshal
import xml.etree.ElementTree as ET

import numpy as np


class ExternalStateError(RuntimeError):
    pass


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _stable_scalar(value):
    if value is None or type(value) in (str, bytes, bool, int, float):
        return {'type': type(value).__name__, 'repr': repr(value)}
    if isinstance(value, tuple):
        return {'tuple': [_stable_scalar(item) for item in value]}
    raise ExternalStateError('Unsupported callback default: ' + str(type(value)))


class StaticXmlState:
    """XML is immutable during a branch; verify bytes and object identity."""
    def __init__(self, element):
        if not isinstance(element, ET.Element):
            raise TypeError('Expected ElementTree Element')
        self.element = element
        self.identity = id(element)
        self.digest = self.current()

    def current(self):
        if id(self.element) != self.identity:
            raise ExternalStateError('XML identity changed')
        return _sha(ET.tostring(self.element, encoding='utf-8'))

    def verify(self):
        if self.current() != self.digest:
            raise ExternalStateError('Static XML bytes changed')
        return self.digest


class CallbackState:
    """Verify callback code/defaults/closure identities; closure state is graphed separately."""
    def __init__(self, callback):
        if not callable(callback):
            raise TypeError('Expected callable')
        self.callback = callback
        self.identity = id(callback)
        self.digest = self.current()

    def current(self):
        fn = getattr(self.callback, '__func__', self.callback)
        code = getattr(fn, '__code__', None)
        if code is None:
            raise ExternalStateError('Callback has no Python code object')
        payload = {
            'identity': self.identity,
            'module': getattr(fn, '__module__', None),
            'qualname': getattr(fn, '__qualname__', None),
            'code': _sha(marshal.dumps(code)),
            'defaults': _stable_scalar(getattr(fn, '__defaults__', None)),
            'kwdefaults': {k: _stable_scalar(v) for k, v in
                           sorted((getattr(fn, '__kwdefaults__', None) or {}).items())},
            'closure_ids': [id(cell.cell_contents) for cell in (getattr(fn, '__closure__', None) or ())],
            'bound_self_id': id(getattr(self.callback, '__self__', None)),
        }
        if id(self.callback) != self.identity:
            raise ExternalStateError('Callback identity changed')
        return _sha(json.dumps(payload, sort_keys=True).encode())

    def verify(self):
        if self.current() != self.digest:
            raise ExternalStateError('Callback definition or closure identity changed')
        return self.digest


class MjModelState:
    """Compiled MuJoCo model is static; verify its exact MJB serialization."""
    def __init__(self, model, mujoco_module):
        self.model = model
        self.mujoco = mujoco_module
        self.identity = id(model)
        self.digest = self.current()

    def current(self):
        if id(self.model) != self.identity:
            raise ExternalStateError('MjModel identity changed')
        buffer = np.empty(self.mujoco.mj_sizeModel(self.model), dtype=np.uint8)
        self.mujoco.mj_saveModel(self.model, None, buffer)
        return _sha(buffer.tobytes())

    def verify(self):
        if self.current() != self.digest:
            raise ExternalStateError('Compiled MjModel changed')
        return self.digest


class RendererRebuildState:
    """Renderer-native handles are rebuilt; exact raster is the state verifier."""
    def __init__(self, rebuild, render_bytes):
        if not callable(rebuild) or not callable(render_bytes):
            raise TypeError('Renderer adapter requires rebuild and render callbacks')
        self.rebuild = rebuild
        self.render_bytes = render_bytes
        self.raster_digest = self.current()

    def current(self):
        value = self.render_bytes()
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise ExternalStateError('Renderer verifier must return raw bytes')
        return _sha(bytes(value))

    def restore(self):
        self.rebuild()
        if self.current() != self.raster_digest:
            raise ExternalStateError('Raster differs after renderer rebuild')
        return self.raster_digest
