"""Zero-model-action inventory of the first fixed scene; not a restoration gate."""
import hashlib
import inspect
import json
import argparse
from pathlib import Path
import random
import traceback

import numpy as np
import torch


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(root):
    seen = {}
    records = []

    def walk(value, path, depth):
        type_name = type(value).__module__ + '.' + type(value).__qualname__
        if value is None or isinstance(value, (str, bytes, bool, int, float, np.generic)):
            return
        if id(value) in seen:
            records.append({'path': path, 'alias_of': seen[id(value)], 'type': type_name})
            return
        seen[id(value)] = path
        item = {'path': path, 'type': type_name}
        records.append(item)
        if isinstance(value, np.ndarray):
            item.update(shape=list(value.shape), dtype=str(value.dtype),
                        object_dtype=bool(value.dtype.hasobject))
            return
        if depth >= 14:
            item['requires_manual_coverage'] = 'depth_limit'
            return
        if isinstance(value, dict):
            item['keys'] = [repr(k) for k in value]
            for k, v in value.items():
                walk(v, path + '[' + repr(k) + ']', depth + 1)
        elif isinstance(value, (list, tuple)):
            for i, v in enumerate(value):
                walk(v, path + '[' + str(i) + ']', depth + 1)
        elif inspect.ismethod(value):
            item['callback'] = value.__qualname__
            walk(value.__self__, path + '.__self__', depth + 1)
        elif inspect.isfunction(value):
            item['callback'] = value.__module__ + '.' + value.__qualname__
            item['global_state_audit_required'] = True
            for name, cell in zip(value.__code__.co_freevars, value.__closure__ or ()):
                walk(cell.cell_contents, path + '.closure.' + name, depth + 1)
            walk(value.__defaults__, path + '.defaults', depth + 1)
        elif inspect.ismodule(value) or inspect.isclass(value):
            item['requires_manual_coverage'] = 'module_or_class'
        elif hasattr(value, '__dict__'):
            item['fields'] = sorted(vars(value))
            for k, v in sorted(vars(value).items()):
                walk(v, path + '.' + k, depth + 1)
        else:
            item['requires_manual_coverage'] = 'native_or_slot_object'
            item['visible_attributes'] = sorted(n for n in dir(value) if not n.startswith('__'))

    walk(root, 'env', 0)
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='runtime_inventory_v1')
    args = parser.parse_args()
    code = ROOT / 'paired_action_v1'
    run = code / args.output
    run.mkdir(exist_ok=False)
    registration = json.loads((code / 'static_inventory_v1/REGISTRATION.json').read_text())
    entry = registration['entries'][0]
    (run / 'REGISTRATION.json').write_text(json.dumps({
        'source_sha256': sha(Path(__file__)), 'entry': entry,
        'protocol_sha256': sha(code / 'PROTOCOL.md'),
        'robot_model_actions': 0, 'loads_wam': False,
        'purpose': 'Runtime type/field inventory, not branch admission'}, indent=2))
    env = None
    try:
        from experiments.libero.libero_utils import LIBERO_ENV_RESOLUTION, get_libero_env
        from libero.libero import benchmark
        for path_key, hash_key in [('bddl_path', 'bddl_sha256'),
                                   ('initial_state_path', 'initial_file_sha256')]:
            if sha(Path(entry[path_key])) != entry[hash_key]:
                raise RuntimeError('Frozen scene assets differ')
        random.seed(entry['environment_seed'])
        np.random.seed(entry['environment_seed'])
        torch.manual_seed(entry['environment_seed'])
        torch.cuda.manual_seed_all(entry['environment_seed'])
        task = benchmark.get_benchmark_dict()['libero_10']().get_task(entry['task_id'])
        if task.name != entry['task_name']:
            raise RuntimeError('Task order mismatch')
        env, _ = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry['environment_seed'])
        states = np.asarray(torch.load(entry['initial_state_path'], map_location='cpu', weights_only=False))
        if '_add_' in Path(entry['initial_state_path']).name or '_level' in Path(entry['initial_state_path']).name:
            states = states.reshape(1, -1)
        initial = np.asarray(states[entry['initial_state_index']], dtype='<f8')
        if hashlib.sha256(initial.tobytes()).hexdigest() != entry['state_sha256']:
            raise RuntimeError('Initial state mismatch')
        env.reset()
        obs = env.set_init_state(initial)
        records = describe(env)
        (run / 'OBJECTS.json').write_text(json.dumps(records, indent=2, sort_keys=True))
        report = {'status': 'RUNTIME_INVENTORY_ONLY_NO_RESTORE_PASS',
                  'records': len(records), 'robot_model_actions': 0, 'loads_wam': False,
                  'unresolved_native_or_depth_records': sum('requires_manual_coverage' in r for r in records),
                  'observation_keys': sorted(obs),
                  'rendering_initialized': True, 'source_sha256': sha(Path(__file__))}
        (run / 'REPORT.json').write_text(json.dumps(report, indent=2, sort_keys=True))
        print(json.dumps(report), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise
    finally:
        if env is not None:
            env.close()


if __name__ == '__main__':
    main()
