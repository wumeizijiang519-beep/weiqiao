"""Fail-closed binding of the audited runtime graph to checkpoint adapters."""
import hashlib
import inspect
import json
import struct
import types
import xml.etree.ElementTree as ET
from collections import OrderedDict

import numpy as np

from checkpoint import CompositeCheckpoint
from external_state import CallbackState, MjModelState, RendererRebuildState, StaticXmlState
from rng_state import RngState
from state_graph import CoverageError, StateGraph


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _fqcn(value):
    return type(value).__module__ + '.' + type(value).__qualname__


class RuntimeCheckpoint:
    """Capture every reachable Python field, with explicit native exclusions."""

    RENDER_NATIVE = {
        'OpenGL._opaque.EGLContext_pointer',
        'mujoco._render.MjrContext',
        'mujoco._structs.MjvCamera',
        'mujoco._structs.MjvOption',
        'mujoco._structs.MjvPerturb',
        'mujoco._structs.MjvScene',
    }

    def __init__(self, env, torch_module, render_bytes, rebuild_renderer, local_generators=None):
        from native_state import NativeState
        self.env = env
        base = env.env if hasattr(env, 'env') else env
        self.sim = base.sim
        self.native = NativeState(self.sim.model._model, self.sim.data._data)
        self.model_state = MjModelState(self.sim.model._model, __import__('mujoco'))
        self.rng = RngState(local_generators=local_generators, torch_module=torch_module)
        self.static_states = [self.model_state]
        self.externals = {}
        self.schemas = {}
        self._seen = set()
        self._discover(env, 'env')
        self.graph = StateGraph({'env': env}, self.schemas, self.externals)
        self.renderer = RendererRebuildState(rebuild_renderer, render_bytes)
        self.composite = CompositeCheckpoint(
            self.native, self.graph, self.rng,
            static_verifiers=self.static_states, renderer=self.renderer)

    def _external(self, value, verifier):
        self.externals[id(value)] = verifier

    def _discover(self, value, path):
        if value is None or type(value) in (str, bytes, bool, int, float) or isinstance(value, np.generic):
            return
        identity = id(value)
        if identity in self._seen:
            return
        self._seen.add(identity)
        name = _fqcn(value)
        if isinstance(value, np.ndarray):
            if value.dtype.hasobject:
                raise CoverageError('Object array at ' + path)
            return
        if inspect.ismethod(value) or inspect.isfunction(value):
            state = CallbackState(value)
            self.static_states.append(state)
            self._external(value, lambda _value, state=state: state.current())
            return
        if isinstance(value, ET.Element):
            state = StaticXmlState(value)
            self.static_states.append(state)
            self._external(value, lambda _value, state=state: state.current())
            return
        if name == 'mujoco._structs.MjModel':
            self._external(value, lambda _value: self.model_state.current())
            return
        if name == 'mujoco._structs.MjData':
            self._external(value, lambda _value: _digest(self.native.current().tobytes()))
            return
        if name in self.RENDER_NATIVE or name.endswith('.MjRenderContextOffscreen') or name.endswith('.EGLGLContext'):
            signature = _digest((name + '|' + str(identity)).encode())
            self._external(value, lambda actual, signature=signature, identity=identity:
                           signature if id(actual) == identity else _digest(b'identity-changed'))
            return
        if inspect.ismodule(value) or inspect.isclass(value):
            location = inspect.getsourcefile(value) or ''
            signature = _digest((name + '|' + str(identity) + '|' + location).encode())
            self._external(value, lambda actual, signature=signature, identity=identity:
                           signature if id(actual) == identity else _digest(b'identity-changed'))
            return
        if type(value) in (dict, OrderedDict):
            if not all(k is None or type(k) in (str, int) for k in value):
                raise CoverageError('Unsupported dictionary key at ' + path)
            for key, item in value.items():
                self._discover(item, path + '[' + repr(key) + ']')
            return
        if type(value) in (list, tuple):
            for index, item in enumerate(value):
                self._discover(item, path + '[' + str(index) + ']')
            return
        if not hasattr(value, '__dict__'):
            raise CoverageError('Unhandled native type at ' + path + ': ' + name)
        fields = tuple(sorted(vars(value)))
        previous = self.schemas.setdefault(type(value), fields)
        if tuple(previous) != fields:
            raise CoverageError('Inconsistent field schema for ' + name)
        for field in fields:
            self._discover(vars(value)[field], path + '.' + field)

    def restore(self):
        return self.composite.restore()

    def coverage(self):
        return self.graph.coverage()

    def digest(self):
        """Hash the complete live graph, including scalar fields and alias layout."""
        rows = []
        dynamic_seen = {}
        for identity, node in sorted(self.graph.nodes.items(), key=lambda item: item[1]['path']):
            value, kind = node['value'], node['kind']
            row = {'path': node['path'], 'kind': kind, 'type': _fqcn(value)}
            if kind == 'array':
                row['value'] = _digest(np.ascontiguousarray(value).tobytes())
                row['layout'] = [value.dtype.str, list(value.shape), bool(value.flags.writeable)]
            elif kind == 'external':
                row['value'] = node['verifier'](value)
            elif kind == 'object':
                row['fields'] = {key: self._live_token(vars(value)[key], dynamic_seen)
                                 for key in node['fields']}
            elif kind in ('dict', 'ordered_dict'):
                row['items'] = [[repr(key), self._live_token(item, dynamic_seen)]
                                for key, item in value.items()]
            elif kind in ('list', 'tuple'):
                row['items'] = [self._live_token(item, dynamic_seen) for item in value]
            rows.append(row)
        return _digest(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode())

    def _live_token(self, value, dynamic_seen=None):
        if value is None or type(value) in (str, bytes, bool, int):
            return [_fqcn(value), repr(value)]
        if type(value) is float:
            return ['float64bits', struct.pack('!d', value).hex()]
        if isinstance(value, np.generic):
            return [_fqcn(value), value.tobytes().hex()]
        name = _fqcn(value)
        if name in self.RENDER_NATIVE or name.endswith('.MjRenderContextOffscreen') or name.endswith('.EGLGLContext'):
            return ['renderer_component', name]
        node = self.graph.nodes.get(id(value))
        if node is not None:
            return ['ref', node['path']]
        return self._dynamic_token(value, {} if dynamic_seen is None else dynamic_seen)

    def _dynamic_token(self, value, seen):
        """Content-address a cache value created after checkpoint capture."""
        if value is None or type(value) in (str, bool, int):
            return [_fqcn(value), repr(value)]
        if type(value) is bytes:
            return ['bytes', _digest(value), len(value)]
        if type(value) is float:
            return ['float64bits', struct.pack('!d', value).hex()]
        if isinstance(value, np.generic):
            return [_fqcn(value), value.tobytes().hex()]

        identity = id(value)
        if identity in seen:
            return ['dynamic_alias', seen[identity]]
        label = 'd%d' % len(seen)
        seen[identity] = label

        if isinstance(value, np.ndarray):
            if value.dtype.hasobject:
                raise CoverageError('Dynamic object array is unsupported')
            return ['dynamic_array', label, value.dtype.str, list(value.shape),
                    bool(value.flags.writeable),
                    _digest(np.ascontiguousarray(value).tobytes())]
        if type(value) in (dict, OrderedDict):
            if not all(key is None or type(key) in (str, int) for key in value):
                raise CoverageError('Unsupported dynamic dictionary key')
            kind = 'ordered_dict' if type(value) is OrderedDict else 'dict'
            return ['dynamic_' + kind, label,
                    [[repr(key), self._dynamic_token(item, seen)]
                     for key, item in value.items()]]
        if type(value) in (list, tuple):
            return ['dynamic_' + type(value).__name__, label,
                    [self._dynamic_token(item, seen) for item in value]]

        name = _fqcn(value)
        if (name in self.RENDER_NATIVE or name.endswith('.MjRenderContextOffscreen')
                or name.endswith('.EGLGLContext')):
            raise CoverageError('Unexpected dynamic renderer handle: ' + name)
        if inspect.ismodule(value) or inspect.isclass(value):
            raise CoverageError('Unexpected dynamic module or class: ' + name)
        if inspect.ismethod(value) or inspect.isfunction(value):
            return ['dynamic_callback', label, value.__module__, value.__qualname__]
        if not hasattr(value, '__dict__'):
            raise CoverageError('Unhandled dynamic native type: ' + name)
        return ['dynamic_object', label, name,
                [[field, self._dynamic_token(vars(value)[field], seen)]
                 for field in sorted(vars(value))]]
