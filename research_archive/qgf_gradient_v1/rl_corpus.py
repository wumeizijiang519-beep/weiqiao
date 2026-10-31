"""Pure array assembly for future admitted data; no file reads, fitting or admission."""

import numpy as np

from training_data import transition_example


def episode_arrays(transitions, current_features, *, episode_id, physical_group, fold, gamma=1.):
    """Use audited actual feedback for targets and known predecision plans for Q.

    current_features has R+1 current-only observation rows, including the last
    measured observation. Caller must first verify dataset/feature admission
    and immutable source hashes. This array helper cannot certify those gates.
    """
    features = np.asarray(current_features, dtype=np.float32)
    if (not transitions or features.ndim != 2 or features.shape[0] != len(transitions) + 1
            or features.shape[1] < 1
            or not np.isfinite(features).all() or not 0 < gamma <= 1 or fold not in (0, 1, 2)):
        raise ValueError('Invalid R+1 feature sequence, fold or gamma')
    examples = []
    previous_remaining = None
    for index, data in enumerate(transitions):
        selected, actual = int(data['selected_index']), int(data['actual_length'])
        before, after = int(data['remaining_before']), int(data['remaining_after'])
        rewards = np.asarray(data['rewards'], dtype=np.float32)
        if (not 1 <= before <= 700 or not 1 <= actual <= min(10, before)
                or rewards.shape != (actual,) or not np.isfinite(rewards).all()):
            raise ValueError('Invalid measured feedback length')
        if previous_remaining is not None and before != previous_remaining:
            raise ValueError('Remaining-horizon discontinuity')
        previous_remaining = after
        terminal = bool(data['terminal'])
        if not terminal and actual != min(10, before):
            raise ValueError('Nonterminal execution did not complete its committed plan')
        if terminal != (index == len(transitions) - 1):
            raise ValueError('Missing terminal or action after terminal')
        if terminal != (bool(data['environment_done']) or bool(data['success']) or bool(data['time_limit'])):
            raise ValueError('Finite-task terminal mask disagrees with actual feedback')
        if bool(data['time_limit']) != (after == 0):
            raise ValueError('Finite-horizon limit flag mismatch')
        labels = np.asarray(data['candidate_returns'])
        if (not 0 <= selected < 4 or labels.shape != (4,)
                or not np.isnan(np.delete(labels, selected)).all()
                or not np.isclose(labels[selected], rewards.sum(dtype=np.float64), atol=1e-6)):
            raise ValueError('Unexecuted candidate labelled or real reward sum differs')
        executed = np.asarray(data['executed_actions'])
        native = np.asarray(data['candidates_native'])
        if (executed.shape != (actual, 7) or native.shape != (4, 32, 7)
                or not np.isfinite(executed).all() or not np.isfinite(native).all()
                or np.max(np.abs(executed - native[selected, :actual])) > 1e-6):
            raise ValueError('Executed prefix differs from selected native candidate')
        example = transition_example(data, features[index], features[index + 1],
                                     episode_id, physical_group, fold)
        example['remaining_before'] = before
        examples.append(example)
    returns = np.empty(len(examples), dtype=np.float32)
    following = 0.
    for index in reversed(range(len(examples))):
        example = examples[index]
        length = example['executed_steps']
        measured = example['rewards'][:length].astype(np.float64)
        reward_sum = float(np.dot(np.power(gamma, np.arange(length)), measured))
        following = reward_sum + (0. if example['terminal'] else gamma ** length * following)
        returns[index] = following
    tensor_keys = ('observation', 'next_observation', 'action', 'bank', 'mask', 'rewards')
    arrays = {key: np.stack([row[key] for row in examples]) for key in tensor_keys}
    for key in ('executed_steps', 'planned_steps', 'remaining_before', 'selected_index'):
        arrays[key] = np.asarray([row[key] for row in examples], dtype=np.int64)
    arrays['terminal'] = np.asarray([row['terminal'] for row in examples], dtype=np.bool_)
    arrays['mc_return'] = returns
    return arrays, {'episode_id': episode_id, 'physical_group': physical_group,
                    'fold': fold, 'transitions': len(examples), 'feature_dimension': features.shape[1],
                    'targets': 'actual logged-policy finite returns; no unexecuted-candidate labels',
                    'admission_decision': None}


def split_episode_groups(metadata, held_fold):
    if held_fold not in (0, 1, 2):
        raise ValueError('Unregistered held-out fold')
    ids, group_folds = set(), {}
    training, held = [], []
    for row in metadata:
        name, group, fold = row['episode_id'], row['physical_group'], row['fold']
        if name in ids or fold not in (0, 1, 2):
            raise ValueError('Duplicate episode or invalid fold')
        ids.add(name)
        if group in group_folds and group_folds[group] != fold:
            raise ValueError('Physical group assigned across folds')
        group_folds[group] = fold
        (held if fold == held_fold else training).append(name)
    if not training or not held:
        raise ValueError('Empty fitting or held-out partition')
    return sorted(training), sorted(held)
