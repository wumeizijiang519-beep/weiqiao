"""Explicit fixed RGB statistics for v2; not WAM hidden features."""
import numpy as np

CAMERAS = ('head_rgb', 'left_rgb', 'right_rgb')
PATCH = 16


def encode_states(data):
    """Return [R+1,701]: RGB patch statistics, joints, TCP, remaining time."""
    chunks = len(data['action_chunks'])
    outputs = []
    for key in CAMERAS:
        rgb = np.asarray(data[key])
        if rgb.shape != (chunks + 1, 96, 96, 3):
            raise ValueError('expected R+1 96px RGB observations')
        patches = rgb.astype(np.float32).reshape(chunks + 1, 6, PATCH, 6, PATCH, 3) / 255.
        mean = patches.mean(axis=(2, 4))
        std = patches.std(axis=(2, 4))
        outputs.append(np.concatenate([mean, std], axis=-1).reshape(chunks + 1, -1))
    for key, width in (('joint_positions', 38), ('tcp_pose', 14)):
        state = np.asarray(data[key], dtype=np.float32)
        if state.shape != (chunks + 1, width):
            raise ValueError('state shape mismatch')
        outputs.append(state)
    steps = np.append(data['replan_steps'], int(data['final_steps'])).astype(np.float32)
    limit = int(data['task_limit'])
    if limit < 1 or (steps < 0).any() or (steps > limit).any():
        raise ValueError('invalid remaining task time')
    outputs.append((1 - steps / limit)[:, None])
    encoded = np.concatenate(outputs, axis=1).astype(np.float32)
    if encoded.shape != (chunks + 1, 701) or not np.isfinite(encoded).all():
        raise ValueError('invalid fixed feature output')
    return encoded


def training_scaler(episodes):
    """Fit only on training episodes; give each episode equal total weight."""
    if not episodes:
        raise ValueError('empty training episodes')
    state_mean = np.mean([e['states'].mean(0) for e in episodes], axis=0)
    state_second = np.mean([(e['states'] ** 2).mean(0) for e in episodes], axis=0)
    action_mean = np.mean([e['actions'].reshape(-1, 16).mean(0) for e in episodes], axis=0)
    action_second = np.mean([(e['actions'].reshape(-1, 16) ** 2).mean(0) for e in episodes], axis=0)
    return {name: value.astype(np.float32) for name, value in {
        'state_mean': state_mean,
        'state_scale': np.maximum(np.sqrt(np.maximum(state_second - state_mean ** 2, 0)), 1e-3),
        'action_mean': action_mean,
        'action_scale': np.maximum(np.sqrt(np.maximum(action_second - action_mean ** 2, 0)), 1e-3)
    }.items()}
