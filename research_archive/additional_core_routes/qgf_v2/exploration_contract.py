"""Training-only WAM candidate exploration, with no reward-conditioned selection."""
import numpy as np


def choose_random_candidate(candidates, rng):
    actions = np.asarray(candidates, dtype=np.float32)
    if actions.shape != (4, 10, 16) or not np.isfinite(actions).all():
        raise ValueError('expected four finite10x16 WAM candidates')
    if not any(not np.array_equal(row, actions[0]) for row in actions[1:]):
        raise ValueError('no candidate diversity')
    return int(rng.integers(4))


def validate_commit(candidates, selected, committed):
    action = np.asarray(committed, dtype=np.float32)
    if action.shape != (10, 16) or not np.isfinite(action).all():
        raise ValueError('invalid committed action')
    np.testing.assert_allclose(action, candidates[selected], rtol=0, atol=1e-6,
                               err_msg='committed action does not reproduce selected proposal')
    return action
