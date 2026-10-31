"""User-approved official native gripper contract; V1 source stays immutable."""

import numpy as np

from data_contract import OBS_KEYS, array_hash, observation_hash, native_from_normalized


def normalized_executed_action(native, scale, offset):
    value = np.asarray(native, dtype=np.float32).copy()
    scale, offset = np.asarray(scale), np.asarray(offset)
    if value.shape[-1] != 7 or not np.isfinite(value).all():
        raise ValueError('Invalid finite native action shape')
    if not np.isin(value[..., -1], [-1., 0., 1.]).all():
        raise ValueError('Not an official sign-quantized gripper value')
    if not np.isfinite(scale).all() or not np.isfinite(offset).all() or np.any(scale == 0):
        raise ValueError('Invalid action normalizer')
    value[..., -1] = (1 - value[..., -1]) / 2
    return (value * scale + offset).astype(np.float32)


def official_native_from_raw(raw, scale, offset):
    value = ((np.asarray(raw, dtype=np.float32) - offset) / scale).astype(np.float32)
    value[..., -1] = value[..., -1] * 2 - 1
    value[..., -1] *= -1
    value[..., -1] = np.sign(value[..., -1])
    return value


def validate_bank(native, raw, scale, offset):
    if native.shape != (4, 32, 7) or raw.shape != native.shape:
        raise ValueError('Bank shape mismatch')
    if not np.isfinite(native).all() or not np.isfinite(raw).all():
        raise ValueError('Nonfinite native/raw bank')
    normalized = normalized_executed_action(native, scale, offset)
    decoded = official_native_from_raw(raw, scale, offset)
    native_error = float(np.max(np.abs(decoded - native)))
    roundtrip = float(np.max(np.abs(native_from_normalized(normalized, scale, offset) - native)))
    if native_error > 1e-6 or roundtrip > 1e-6:
        raise ValueError('Official raw/native/canonical mapping disagreement')
    if len({array_hash(x) for x in native}) != 4:
        raise ValueError('Identical native candidates')
    mad = [float(np.abs(native[i] - native[j]).mean()) for i in range(4) for j in range(i)]
    if min(mad) <= 0:
        raise ValueError('No positive native diversity')
    return normalized, {'native_postprocess_error': native_error, 'canonical_roundtrip_error': roundtrip,
                         'pairwise_mad_min': min(mad),
                         'neutral_zero_locations': np.argwhere(native[..., -1] == 0).tolist()}


def validate_transition(data, previous_next=None):
    bank = data['candidates_native']
    normalized, mapping = validate_bank(bank, data['candidates_raw_normalized'],
                                         data['action_scale'], data['action_offset'])
    if np.max(np.abs(normalized - data['candidates_executed_normalized'])) > 1e-6:
        raise ValueError('Stored actual-action normalization mismatch')
    selected, length = int(data['selected_index']), int(data['actual_length'])
    before, after = int(data['remaining_before']), int(data['remaining_after'])
    if not 0 <= selected < 4 or not 1 <= length <= min(10, before):
        raise ValueError('Invalid selection/length')
    if after != before - length or after < 0:
        raise ValueError('Finite horizon mismatch')
    executed, rewards = data['executed_actions'], data['rewards']
    if executed.shape != (length, 7) or rewards.shape != (length,):
        raise ValueError('Actual feedback length mismatch')
    if not np.isfinite(executed).all() or not np.isfinite(rewards).all():
        raise ValueError('Nonfinite actual feedback')
    error = float(np.max(np.abs(executed - bank[selected, :length])))
    if error > 1e-6:
        raise ValueError('Selected prefix was not committed')
    labels = data['candidate_returns']
    if labels.shape != (4,) or not np.isnan(np.delete(labels, selected)).all():
        raise ValueError('Unexecuted candidate got a label')
    if not np.isclose(labels[selected], rewards.sum(dtype=np.float64), atol=1e-6):
        raise ValueError('Measured reward sum mismatch')
    if bool(data['terminal']) != (bool(data['environment_done']) or bool(data['success']) or bool(data['time_limit'])):
        raise ValueError('Terminal mask mismatch')
    if bool(data['time_limit']) != (after == 0) or (not bool(data['terminal']) and length != 10):
        raise ValueError('Finite horizon/partial chunk mismatch')
    if str(data['caller_rng_hash']) != str(data['candidate0_post_rng_hash']):
        raise ValueError('Caller RNG drift')
    if not np.isfinite(data['selected_replay_error']) or float(data['selected_replay_error']) > 1e-6:
        raise ValueError('Selected candidate replay mismatch')
    current = {key: data['current_' + key] for key in OBS_KEYS}
    next_obs = {key: data['next_' + key] for key in OBS_KEYS}
    if previous_next is not None and observation_hash(current) != observation_hash(previous_next):
        raise ValueError('Observation discontinuity')
    if not all(np.isfinite(x).all() for x in (*current.values(), *next_obs.values())):
        raise ValueError('Nonfinite observation')
    states = data['sim_states']
    if states.ndim != 2 or states.shape[0] != length + 1 or not np.isfinite(states).all():
        raise ValueError('Missing actual simulator states')
    return {'commit_error': error, 'reward_sum': float(rewards.sum(dtype=np.float64)),
            'next_obs': next_obs, **mapping}
