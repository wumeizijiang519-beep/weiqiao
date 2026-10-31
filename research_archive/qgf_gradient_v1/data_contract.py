"""Replayable RNG and actual-execution contracts, independent of WAM/simulator."""

import hashlib
import json
import random

import numpy as np
import torch


OBS_KEYS = ('agentview_image', 'robot0_eye_in_hand_image', 'robot0_eef_pos',
            'robot0_eef_quat', 'robot0_gripper_qpos')


def array_hash(value):
    value = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    digest.update(str(value.dtype).encode())
    digest.update(json.dumps(list(value.shape)).encode())
    digest.update(value.tobytes())
    return digest.hexdigest()


def observation_payload(obs):
    result = {key: np.array(obs[key], copy=True) for key in OBS_KEYS}
    if not all(np.isfinite(value).all() for value in result.values()):
        raise ValueError('Nonfinite observation')
    return result


def observation_hash(obs):
    return hashlib.sha256(json.dumps(
        {key: array_hash(obs[key]) for key in OBS_KEYS}, sort_keys=True).encode()).hexdigest()


def capture_rng():
    numpy_state = np.random.get_state()
    return {
        'python': random.getstate(),
        'numpy': (numpy_state[0], numpy_state[1].copy(), *numpy_state[2:]),
        'torch_cpu': torch.get_rng_state().clone(),
        'torch_cuda': [state.clone() for state in torch.cuda.get_rng_state_all()]
        if torch.cuda.is_available() else [],
    }


def restore_rng(state):
    random.setstate(state['python'])
    np.random.set_state(state['numpy'])
    torch.set_rng_state(state['torch_cpu'])
    if state['torch_cuda']:
        torch.cuda.set_rng_state_all(state['torch_cuda'])


def rng_hash(state):
    digest = hashlib.sha256()
    digest.update(json.dumps(state['python']).encode())
    numpy_state = state['numpy']
    digest.update(json.dumps([numpy_state[0], *numpy_state[2:]]).encode())
    digest.update(numpy_state[1].tobytes())
    for tensor in [state['torch_cpu'], *state['torch_cuda']]:
        digest.update(tensor.cpu().numpy().tobytes())
    return digest.hexdigest()


def _tuple_tree(value):
    return tuple(_tuple_tree(x) for x in value) if isinstance(value, list) else value


def save_rng(path, state):
    metadata = {'python': state['python'], 'numpy': [state['numpy'][0], *state['numpy'][2:]],
                'cuda_count': len(state['torch_cuda']), 'hash': rng_hash(state)}
    np.savez_compressed(path, metadata=np.asarray(json.dumps(metadata)),
                        numpy_keys=state['numpy'][1],
                        torch_cpu=state['torch_cpu'].cpu().numpy(),
                        **{f'torch_cuda_{i}': value.cpu().numpy()
                           for i, value in enumerate(state['torch_cuda'])})


def load_rng(path):
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data['metadata']))
        state = {'python': _tuple_tree(meta['python']),
                 'numpy': (meta['numpy'][0], data['numpy_keys'].copy(), *meta['numpy'][1:]),
                 'torch_cpu': torch.from_numpy(data['torch_cpu'].copy()),
                 'torch_cuda': [torch.from_numpy(data[f'torch_cuda_{i}'].copy())
                                for i in range(meta['cuda_count'])]}
    if rng_hash(state) != meta['hash']:
        raise ValueError('RNG file corruption')
    return state


def normalized_executed_action(native, scale, offset):
    """Inverse official native affine map, using the actually binarized gripper.

    No [-5,5] training-preprocessor clipping is applied: inverse affine mapping
    must preserve the exact executed continuous action and be invertible.
    """
    value = np.asarray(native, dtype=np.float32).copy()
    if value.shape[-1] != 7 or not np.isin(value[..., -1], [-1, 1]).all():
        raise ValueError('Invalid native gripper/action shape')
    scale, offset = np.asarray(scale), np.asarray(offset)
    if not np.isfinite(scale).all() or np.any(scale == 0):
        raise ValueError('Invalid action normalizer')
    value[..., -1] = (1 - value[..., -1]) / 2
    return (value * scale + offset).astype(np.float32)


def native_from_normalized(value, scale, offset):
    result = (np.asarray(value, dtype=np.float32) - offset) / scale
    result = result.astype(np.float32)
    result[..., -1] = np.sign(1 - 2 * result[..., -1])
    return result


def validate_transition(data, previous_next=None):
    bank = data['candidates_native']
    normalized = data['candidates_executed_normalized']
    if bank.shape != (4, 32, 7) or normalized.shape != bank.shape:
        raise ValueError('Bank shape mismatch')
    if not np.isfinite(bank).all() or not np.isfinite(normalized).all():
        raise ValueError('Nonfinite bank')
    if len({array_hash(x) for x in bank}) != 4:
        raise ValueError('Identical candidates')
    if not np.isin(bank[..., -1], [-1, 1]).all():
        raise ValueError('Gripper contract violation')
    selected = int(data['selected_index'])
    length = int(data['actual_length'])
    before, after = int(data['remaining_before']), int(data['remaining_after'])
    if not 0 <= selected < 4 or not 1 <= length <= min(10, before):
        raise ValueError('Invalid selected index/actual length')
    if after != before - length or after < 0:
        raise ValueError('Incorrect finite-horizon progression')
    executed, rewards = data['executed_actions'], data['rewards']
    if executed.shape != (length, 7) or rewards.shape != (length,):
        raise ValueError('Executed action/reward length mismatch')
    if not np.isfinite(executed).all() or not np.isfinite(rewards).all():
        raise ValueError('Nonfinite actual feedback')
    if np.max(np.abs(executed - bank[selected, :length])) > 1e-6:
        raise ValueError('Selected prefix was not committed')
    reconstruction = native_from_normalized(normalized, data['action_scale'], data['action_offset'])
    if np.max(np.abs(reconstruction - bank)) > 1e-6:
        raise ValueError('Native/normalized action mismatch')
    labels = data['candidate_returns']
    if labels.shape != (4,) or not np.isnan(np.delete(labels, selected)).all():
        raise ValueError('Unexecuted candidate received a label')
    if not np.isclose(labels[selected], rewards.sum(dtype=np.float64), atol=1e-6):
        raise ValueError('Actual reward sum mismatch')
    terminated, timeout = bool(data['environment_done']), bool(data['time_limit'])
    if bool(data['terminal']) != (terminated or timeout or bool(data['success'])):
        raise ValueError('Finite-horizon terminal mask mismatch')
    if timeout != (after == 0):
        raise ValueError('Timeout mask mismatch')
    if not bool(data['terminal']) and length != 10:
        raise ValueError('Premature nonterminal chunk')
    if str(data['caller_rng_hash']) != str(data['candidate0_post_rng_hash']):
        raise ValueError('Unexecuted candidates modified caller RNG')
    if float(data['selected_replay_error']) > 1e-6:
        raise ValueError('Selected candidate replay mismatch')
    current = {key: data['current_' + key] for key in OBS_KEYS}
    next_obs = {key: data['next_' + key] for key in OBS_KEYS}
    if previous_next is not None and observation_hash(current) != observation_hash(previous_next):
        raise ValueError('Observation continuity broken')
    if not all(np.isfinite(x).all() for x in (*current.values(), *next_obs.values())):
        raise ValueError('Nonfinite recorded observation')
    states = data['sim_states']
    if states.ndim != 2 or states.shape[0] != length + 1 or not np.isfinite(states).all():
        raise ValueError('Missing actual step state trace')
    return {'commit_error': float(np.max(np.abs(executed - bank[selected, :length]))),
            'reward_sum': float(rewards.sum(dtype=np.float64)), 'next_obs': next_obs}
