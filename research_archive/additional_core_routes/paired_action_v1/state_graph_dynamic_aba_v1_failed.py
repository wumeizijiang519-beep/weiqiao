"""Fail-closed in-process Python state graph, not a complete simulator checkpoint.

Every object class needs an exact field schema. Native handles must instead
have an explicit external verifier; identity-only exclusions are not accepted.
No pickle, implicit deepcopy of native handles, or silent skipped fields.
"""
import hashlib
import struct
from collections import OrderedDict

import numpy as np


class CoverageError(RuntimeError):
    pass


def digest_array(value):
    if value.dtype.hasobject:
        raise CoverageError('Object arrays are not serializable')
    return (value.dtype.str, value.shape,
            hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest())


class StateGraph:
    def __init__(self, roots, schemas, externals=None):
        self.schemas = schemas
        self.externals = externals or {}
        self.nodes = {}
        self.root = self._capture(roots, 'roots')

    def _capture(self, value, path):
        if value is None or type(value) in (str, bytes, bool, int, float):
            return ('scalar', value)
        if isinstance(value, np.generic):
            return ('numpy_scalar', value.copy())
        identity = id(value)
        if identity in self.nodes:
            return ('ref', identity)
        node = {'value': value, 'path': path}
        self.nodes[identity] = node
        if identity in self.externals:
            verifier = self.externals[identity]
            signature = verifier(value)
            if not isinstance(signature, str) or len(signature) != 64:
                raise CoverageError('External verifier must return an immutable SHA256 digest: ' + path)
            node.update(kind='external', verifier=verifier, signature=signature)
        elif isinstance(value, np.ndarray):
            digest_array(value)
            node.update(kind='array', snapshot=value.copy(), writeable=value.flags.writeable)
        elif type(value) in (dict, OrderedDict, list, tuple):
            node['kind'] = 'ordered_dict' if type(value) is OrderedDict else type(value).__name__
            if type(value) in (dict, OrderedDict):
                if not all(type(k) in (str, int) for k in value):
                    raise CoverageError('Unsupported dictionary key at ' + path)
                node['items'] = [(k, self._capture(v, path + '[' + repr(k) + ']'))
                                 for k, v in value.items()]
            else:
                node['items'] = [self._capture(v, path + '[' + str(i) + ']')
                                 for i, v in enumerate(value)]
        elif type(value) in self.schemas:
            fields = set(vars(value))
            if fields != set(self.schemas[type(value)]):
                raise CoverageError('Schema mismatch at ' + path + ': ' + repr(sorted(fields)))
            node.update(kind='object', fields=sorted(fields))
            node['items'] = {k: self._capture(vars(value)[k], path + '.' + k)
                             for k in sorted(fields)}
        else:
            raise CoverageError('Unhandled type at ' + path + ': ' + str(type(value)))
        return ('ref', identity)

    def _decode(self, token):
        return self.nodes[token[1]]['value'] if token[0] == 'ref' else token[1]

    def restore(self):
        # Preflight every node before changing any state. External components
        # must already have been restored by their separately audited adapter.
        for node in self.nodes.values():
            value, kind = node['value'], node['kind']
            if kind == 'external' and node['verifier'](value) != node['signature']:
                raise CoverageError('External component differs: ' + node['path'])
            if kind == 'array':
                saved = node['snapshot']
                if value.shape != saved.shape or value.dtype != saved.dtype:
                    raise CoverageError('Array layout changed: ' + node['path'])
                if value.flags.writeable != node['writeable']:
                    raise CoverageError('Array writeability changed: ' + node['path'])
                if not value.flags.writeable and digest_array(value) != digest_array(saved):
                    raise CoverageError('Read-only array changed: ' + node['path'])
            if kind == 'object' and set(vars(value)) != set(node['fields']):
                raise CoverageError('Runtime field schema changed: ' + node['path'])
        for node in self.nodes.values():
            value, kind = node['value'], node['kind']
            if kind == 'array' and value.flags.writeable:
                np.copyto(value, node['snapshot'], casting='no')
            elif kind in ('dict', 'ordered_dict'):
                value.clear()
                value.update((k, self._decode(v)) for k, v in node['items'])
            elif kind == 'list':
                value[:] = [self._decode(v) for v in node['items']]
            elif kind == 'object':
                for k, token in node['items'].items():
                    vars(value)[k] = self._decode(token)
        self.verify()
        return self._decode(self.root)

    def verify(self):
        for node in self.nodes.values():
            value, kind = node['value'], node['kind']
            if kind == 'array':
                if digest_array(value) != digest_array(node['snapshot']):
                    raise CoverageError('Array bytes differ: ' + node['path'])
            elif kind == 'external':
                if node['verifier'](value) != node['signature']:
                    raise CoverageError('External verifier mismatch: ' + node['path'])
            elif kind in ('dict', 'ordered_dict', 'object'):
                actual = value if kind in ('dict', 'ordered_dict') else vars(value)
                items = node['items'] if kind in ('dict', 'ordered_dict') else list(node['items'].items())
                if set(actual) != {k for k, _ in items}:
                    raise CoverageError('Keys differ: ' + node['path'])
                for k, token in items:
                    self._verify_token(actual[k], token, node['path'])
            elif kind in ('list', 'tuple'):
                if len(value) != len(node['items']):
                    raise CoverageError('Length differs: ' + node['path'])
                for actual, token in zip(value, node['items']):
                    self._verify_token(actual, token, node['path'])

    def _verify_token(self, actual, token, path):
        expected = self._decode(token)
        if token[0] == 'ref':
            same = actual is expected
        elif type(actual) is float and type(expected) is float:
            same = struct.pack('!d', actual) == struct.pack('!d', expected)
        elif token[0] == 'numpy_scalar':
            same = type(actual) is type(expected) and actual.tobytes() == expected.tobytes()
        else:
            same = type(actual) is type(expected) and actual == expected
        if not same:
            raise CoverageError('Value or alias differs: ' + path)

    def coverage(self):
        return [{'path': n['path'], 'kind': n['kind'],
                 'type': type(n['value']).__module__ + '.' + type(n['value']).__qualname__}
                for n in self.nodes.values()]
