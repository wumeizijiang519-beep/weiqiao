"""Registered real-environment A-B-A checkpoint restoration gate."""
import argparse
import hashlib
import json
from pathlib import Path
import pickle
import random
import time
import traceback

import numpy as np
import torch

from native_state import NativeState


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'paired_action_v1'
ARCHIVE = ROOT / 'runs/qgf_gradient_remaining257_v2_shard2/train_0205'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_sha(value):
    value = np.ascontiguousarray(value)
    return hashlib.sha256(value.tobytes()).hexdigest()


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True))


def rng_digest():
    pieces = [pickle.dumps(random.getstate(), protocol=4),
              pickle.dumps(np.random.get_state(), protocol=4),
              torch.get_rng_state().cpu().numpy().tobytes()]
    pieces.extend(state.cpu().numpy().tobytes() for state in torch.cuda.get_rng_state_all())
    return hashlib.sha256(b''.join(pieces)).hexdigest()


def image_hash(obs):
    return hashlib.sha256(obs['agentview_image'].tobytes() +
                          obs['robot0_eye_in_hand_image'].tobytes()).hexdigest()


def proprio(obs):
    return np.concatenate([
        np.asarray(obs['robot0_eef_pos'], dtype='<f8').reshape(-1),
        np.asarray(obs['robot0_eef_quat'], dtype='<f8').reshape(-1),
        np.asarray(obs['robot0_gripper_qpos'], dtype='<f8').reshape(-1),
    ])


def load_actions():
    prefix, a_actions, b_actions, hashes = [], [], [], {}
    for index in range(20):
        path = ARCHIVE / ('transition_%04d/transition.npz' % index)
        hashes[str(path.relative_to(ROOT))] = sha(path)
        with np.load(path, allow_pickle=False) as loaded:
            if index < 10:
                prefix.extend(np.asarray(loaded['executed_actions'], dtype=np.float32))
            else:
                a_actions.extend(np.asarray(loaded['candidates_native'][0, :10], dtype=np.float32))
                b_actions.extend(np.asarray(loaded['candidates_native'][1, :10], dtype=np.float32))
    prefix, a_actions, b_actions = map(lambda x: np.stack(x), (prefix, a_actions, b_actions))
    if prefix.shape != (100, 7) or a_actions.shape != (100, 7) or b_actions.shape != (100, 7):
        raise RuntimeError('Frozen action schedule has wrong shape')
    if np.array_equal(a_actions, b_actions):
        raise RuntimeError('A and B schedules do not differ')
    return prefix, a_actions, b_actions, hashes


def compare_trace(reference, actual, label):
    if reference['steps'] != actual['steps']:
        raise RuntimeError(label + ' branch length differs')
    for key in ('rewards', 'done', 'success', 'proprio', 'native', 'env_state'):
        left, right = reference[key], actual[key]
        if not np.array_equal(left, right):
            delta = np.max(np.abs(left.astype(np.float64) - right.astype(np.float64)))
            raise RuntimeError('%s %s differs, max=%r' % (label, key, float(delta)))
    for key in ('rng', 'policy_raster', 'direct_raster'):
        if reference[key] != actual[key]:
            mismatch = next(i for i, (a, b) in enumerate(zip(reference[key], actual[key])) if a != b)
            raise RuntimeError('%s %s differs at step %d' % (label, key, mismatch))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='replay_aba_gate_v1')
    args = parser.parse_args()
    run = CODE / args.output
    run.mkdir(exist_ok=False)
    started = time.time()
    env = None
    try:
        registration = json.loads((CODE / 'REGISTRATION.json').read_text())
        entry = registration['entries'][0]
        if entry['episode_id'] != 'train_0205' or entry['paired_boundary_model_step'] != 100:
            raise RuntimeError('First frozen registration changed')
        archived_entry = json.loads((ARCHIVE / 'config.json').read_text())
        comparable_entry = dict(entry)
        comparable_entry.pop('paired_boundary_model_step')
        if comparable_entry != archived_entry:
            raise RuntimeError('Archived trajectory registration differs')
        prefix, a_actions, b_actions, action_hashes = load_actions()
        source_names = (
            'native_state.py', 'run_replay_aba_gate_v1.py',
            'REPLAY_ABA_GATE_V1.md', 'REGISTRATION.json')
        sources = {name: sha(CODE / name) for name in source_names}
        json_write(run / 'REGISTRATION.json', {
            'entry': entry, 'sources': sources, 'action_sources': action_hashes,
            'prefix_sha256': array_sha(prefix), 'a_sha256': array_sha(a_actions),
            'b_sha256': array_sha(b_actions), 'actions': {'prefix': 100, 'A': 100, 'B': 100},
            'threshold': 1e-6, 'wam_loaded': False, 'critic_loaded': False})

        from experiments.libero.libero_utils import (LIBERO_ENV_RESOLUTION,
                                                     get_libero_dummy_action, get_libero_env)
        from libero.libero import benchmark
        for path_key, hash_key in (('bddl_path', 'bddl_sha256'),
                                   ('initial_state_path', 'initial_file_sha256')):
            if sha(entry[path_key]) != entry[hash_key]:
                raise RuntimeError('Frozen scene asset mismatch')
        task = benchmark.get_benchmark_dict()['libero_10']().get_task(entry['task_id'])
        if task.name != entry['task_name']:
            raise RuntimeError('Task catalogue order changed')
        states = np.asarray(torch.load(entry['initial_state_path'], map_location='cpu', weights_only=False))
        if '_add_' in Path(entry['initial_state_path']).name or '_level' in Path(entry['initial_state_path']).name:
            states = states.reshape(1, -1)
        initial = np.asarray(states[entry['initial_state_index']], dtype='<f8')
        if array_sha(initial) != entry['state_sha256']:
            raise RuntimeError('Frozen initial state mismatch')

        def branch(label, actions):
            nonlocal env
            random.seed(entry['environment_seed'])
            np.random.seed(entry['environment_seed'])
            torch.manual_seed(entry['environment_seed'])
            torch.cuda.manual_seed_all(entry['environment_seed'])
            env, _ = get_libero_env(task, LIBERO_ENV_RESOLUTION, entry['environment_seed'])
            env.reset()
            obs = env.set_init_state(initial)
            with np.load(ARCHIVE / 'dummy_wait.npz', allow_pickle=False) as dummy:
                for index in range(30):
                    obs, reward, done, _ = env.step(get_libero_dummy_action())
                    success = bool(env.check_success())
                    if reward != dummy['rewards'][index] or done or success:
                        raise RuntimeError(label + ' dummy wait feedback differs')
                    actual = np.asarray(env.get_sim_state())
                    if not np.array_equal(actual, dummy['sim_states'][index + 1]):
                        raise RuntimeError(label + ' dummy wait simulator state differs')
            for index, action in enumerate(prefix):
                transition, offset = index // 10, index % 10
                path = ARCHIVE / ('transition_%04d/transition.npz' % transition)
                with np.load(path, allow_pickle=False) as saved:
                    obs, reward, done, _ = env.step(action.copy())
                    success = bool(env.check_success())
                    if (reward != saved['rewards'][offset]
                            or done != saved['step_environment_done'][offset]
                            or success != saved['step_success'][offset]
                            or not np.array_equal(np.asarray(env.get_sim_state()),
                                                  saved['sim_states'][offset + 1])):
                        raise RuntimeError('%s frozen prefix differs at step %d' % (label, index))

            base = env.env if hasattr(env, 'env') else env
            sim = base.sim
            native = NativeState(sim.model._model, sim.data._data)

            def direct_raster_bytes():
                first = sim.render(width=256, height=256, camera_name='agentview', mode='offscreen')
                second = sim.render(width=256, height=256, camera_name='robot0_eye_in_hand', mode='offscreen')
                return first.tobytes() + second.tobytes()

            boundary = {
                'policy_raster': image_hash(obs),
                'direct_raster': hashlib.sha256(direct_raster_bytes()).hexdigest(),
                'rng': rng_digest(),
                'proprio': proprio(obs),
                'native': native.current(),
                'env_state': np.asarray(env.get_sim_state()).copy(),
            }
            rows = {'steps': 0, 'rewards': [], 'done': [], 'success': [], 'proprio': [],
                    'native': [], 'env_state': [], 'rng': [], 'policy_raster': [],
                    'direct_raster': [], 'boundary': boundary}
            try:
                for action in actions:
                    obs_now, reward, done, _ = env.step(action.copy())
                    success = bool(env.check_success())
                    rows['rewards'].append(float(reward))
                    rows['done'].append(bool(done))
                    rows['success'].append(success)
                    rows['proprio'].append(proprio(obs_now))
                    rows['native'].append(native.current())
                    rows['env_state'].append(np.asarray(env.get_sim_state()).copy())
                    rows['rng'].append(rng_digest())
                    rows['policy_raster'].append(image_hash(obs_now))
                    rows['direct_raster'].append(hashlib.sha256(direct_raster_bytes()).hexdigest())
                    rows['steps'] += 1
                    if done or success:
                        break
            finally:
                env.close()
                env = None
            for key in ('rewards', 'done', 'success', 'proprio', 'native', 'env_state'):
                rows[key] = np.asarray(rows[key])
            np.savez_compressed(run / (label + '.npz'), **{
                key: value for key, value in rows.items() if isinstance(value, np.ndarray)})
            json_write(run / (label + '_hashes.json'), {
                'steps': rows['steps'], 'rng': rows['rng'],
                'policy_raster': rows['policy_raster'], 'direct_raster': rows['direct_raster'],
                'boundary': {key: (array_sha(value) if isinstance(value, np.ndarray) else value)
                             for key, value in boundary.items()}})
            return rows

        a0 = branch('A0', a_actions)
        b0 = branch('B0', b_actions)
        a1 = branch('A1', a_actions)
        a2 = branch('A2', a_actions)
        for label, actual in (('B0 boundary', b0), ('A1 boundary', a1), ('A2 boundary', a2)):
            for key in ('proprio', 'native', 'env_state'):
                if not np.array_equal(a0['boundary'][key], actual['boundary'][key]):
                    raise RuntimeError(label + ' ' + key + ' differs')
            for key in ('policy_raster', 'direct_raster', 'rng'):
                if a0['boundary'][key] != actual['boundary'][key]:
                    raise RuntimeError(label + ' ' + key + ' differs')
        compare_trace(a0, a1, 'A1')
        compare_trace(a0, a2, 'A2')
        if (a0['steps'] == b0['steps'] and np.array_equal(a0['native'], b0['native'])
                and a0['policy_raster'] == b0['policy_raster']):
            raise RuntimeError('B branch did not perturb the trajectory')
        report = {
            'status': 'REPLAY_ABA_RESTORE_PASS', 'entry': entry['episode_id'],
            'prefix_actions_per_branch': 100, 'dummy_actions_per_branch': 30,
            'branch_steps': {key: value['steps'] for key, value in
                             (('A0', a0), ('B0', b0), ('A1', a1), ('A2', a2))},
            'action_replay_max_abs_error': 0.0, 'exact_trace_match': True,
            'fresh_environment_per_branch': True, 'wam_loaded': False,
            'critic_loaded': False,
            'robot_actions': 4 * 130 + a0['steps'] + b0['steps'] + a1['steps'] + a2['steps'],
            'wall_seconds': time.time() - started, 'sources': sources,
        }
        json_write(run / 'REPORT.json', report)
        (run / 'REPLAY_ABA_RESTORE_PASS').touch()
        print(json.dumps(report, sort_keys=True), flush=True)
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise
    finally:
        if env is not None:
            env.close()


if __name__ == '__main__':
    main()
