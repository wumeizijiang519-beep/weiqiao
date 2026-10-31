import random
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch

from data_contract import (OBS_KEYS, capture_rng, load_rng, native_from_normalized,
                           normalized_executed_action, restore_rng, rng_hash,
                           save_rng, validate_transition)


class ContractTests(unittest.TestCase):
    def test_all_global_rng_roundtrip_and_disk(self):
        random.seed(41)
        np.random.seed(42)
        torch.manual_seed(43)
        before = capture_rng()
        def draw():
            values = [random.random(), float(np.random.random()), float(torch.rand(()))]
            if torch.cuda.is_available():
                values.append(float(torch.rand((), device='cuda')))
            return values
        expected = draw()
        restore_rng(before)
        self.assertEqual(draw(), expected)
        with tempfile.TemporaryDirectory() as folder:
            save_rng(Path(folder) / 'rng.npz', before)
            loaded = load_rng(Path(folder) / 'rng.npz')
        self.assertEqual(rng_hash(before), rng_hash(loaded))
        restore_rng(loaded)
        self.assertEqual(draw(), expected)

    def sample(self):
        generator = np.random.default_rng(5)
        bank = generator.normal(size=(4, 32, 7)).astype(np.float32)
        bank[..., -1] = np.where(bank[..., -1] >= 0, 1, -1)
        scale = np.arange(1, 8, dtype=np.float32) / 3
        offset = np.arange(7, dtype=np.float32) / 7
        labels = np.full(4, np.nan)
        labels[2] = 1
        data = dict(candidates_native=bank,
                    candidates_executed_normalized=normalized_executed_action(bank, scale, offset),
                    action_scale=scale, action_offset=offset, selected_index=np.asarray(2),
                    actual_length=np.asarray(3), remaining_before=np.asarray(3),
                    remaining_after=np.asarray(0), executed_actions=bank[2, :3].copy(),
                    rewards=np.asarray([0, 0, 1], dtype=np.float32), candidate_returns=labels,
                    terminal=np.asarray(True), environment_done=np.asarray(True),
                    time_limit=np.asarray(True), success=np.asarray(True),
                    caller_rng_hash=np.asarray('abc'), candidate0_post_rng_hash=np.asarray('abc'),
                    selected_replay_error=np.asarray(0.), sim_states=np.zeros((4, 9)))
        for key in OBS_KEYS:
            data['current_' + key] = np.zeros(3)
            data['next_' + key] = np.ones(3)
        return data

    def test_affine_actual_gripper_roundtrip(self):
        data = self.sample()
        value = native_from_normalized(data['candidates_executed_normalized'],
                                       data['action_scale'], data['action_offset'])
        np.testing.assert_allclose(value, data['candidates_native'], atol=1e-6)
        self.assertEqual(validate_transition(data)['reward_sum'], 1)

    def test_partial_timeout_is_terminal_and_no_counterfactual_labels(self):
        data = self.sample()
        data['terminal'] = np.asarray(False)
        with self.assertRaisesRegex(ValueError, 'terminal'):
            validate_transition(data)
        data = self.sample()
        data['candidate_returns'][0] = 0
        with self.assertRaisesRegex(ValueError, 'Unexecuted'):
            validate_transition(data)

    def test_wrong_commit_rng_or_observation_is_rejected(self):
        data = self.sample()
        data['executed_actions'][0, 0] += .1
        with self.assertRaisesRegex(ValueError, 'committed'):
            validate_transition(data)
        data = self.sample()
        data['caller_rng_hash'] = np.asarray('other')
        with self.assertRaisesRegex(ValueError, 'caller RNG'):
            validate_transition(data)
        with self.assertRaises(ValueError):
            validate_transition(self.sample(), {key: np.ones(3) for key in OBS_KEYS})


if __name__ == '__main__':
    unittest.main()
