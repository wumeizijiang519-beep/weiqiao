"""Explicit global and registered-local RNG capture without initializing CUDA."""
import copy
import hashlib
import json
import random
import numpy as np


def signature(value):
    def encode(v):
        if isinstance(v, np.ndarray):
            return {'dtype': v.dtype.str, 'shape': v.shape,
                    'sha256': hashlib.sha256(v.tobytes()).hexdigest()}
        if isinstance(v, np.generic):
            return v.item()
        if isinstance(v, dict):
            return {k: encode(x) for k, x in sorted(v.items())}
        if isinstance(v, (tuple, list)):
            return [encode(x) for x in v]
        if hasattr(v, 'detach'):
            return encode(v.detach().cpu().numpy())
        return v
    return hashlib.sha256(json.dumps(encode(value), sort_keys=True).encode()).hexdigest()


class RngState:
    def __init__(self, local_generators=None, torch_module=None):
        self.local = local_generators or {}
        self.local_ids = {k: id(v) for k, v in self.local.items()}
        self.torch = torch_module
        self.cuda_initialized = bool(self.torch and self.torch.cuda.is_initialized())
        self.state = self.current()
        self.digest = signature(self.state)

    def _local_state(self, value):
        if isinstance(value, np.random.Generator):
            return ('numpy_generator', copy.deepcopy(value.bit_generator.state))
        if isinstance(value, np.random.RandomState):
            return ('numpy_randomstate', copy.deepcopy(value.get_state()))
        if type(value) is random.Random:
            return ('python_random', value.getstate())
        if self.torch is not None and isinstance(value, self.torch.Generator):
            return ('torch_generator', value.get_state().clone())
        raise TypeError('Unregistered RNG kind: ' + str(type(value)))

    def current(self):
        if {k: id(v) for k, v in self.local.items()} != self.local_ids:
            raise RuntimeError('Local RNG registry identity changed')
        state = {'python': random.getstate(), 'numpy': copy.deepcopy(np.random.get_state()),
                 'locals': {k: self._local_state(v) for k, v in self.local.items()}}
        if self.torch is not None:
            if self.torch.cuda.is_initialized() != self.cuda_initialized:
                raise RuntimeError('CUDA initialization changed across snapshot')
            state['torch_cpu'] = self.torch.get_rng_state().clone()
            state['torch_cuda'] = [s.clone() for s in self.torch.cuda.get_rng_state_all()] if self.cuda_initialized else []
        return state

    def restore(self):
        # Validate registry and CUDA initialization before mutating global RNG.
        self.current()
        random.setstate(self.state['python'])
        np.random.set_state(self.state['numpy'])
        if self.torch is not None:
            self.torch.set_rng_state(self.state['torch_cpu'])
            if self.cuda_initialized:
                self.torch.cuda.set_rng_state_all(self.state['torch_cuda'])
        for name, value in self.local.items():
            kind, saved = self.state['locals'][name]
            if kind == 'numpy_generator':
                value.bit_generator.state = copy.deepcopy(saved)
            elif kind == 'numpy_randomstate':
                value.set_state(saved)
            elif kind == 'python_random':
                value.setstate(saved)
            elif kind == 'torch_generator':
                value.set_state(saved)
        if signature(self.current()) != self.digest:
            raise RuntimeError('RNG restore is not exact')
