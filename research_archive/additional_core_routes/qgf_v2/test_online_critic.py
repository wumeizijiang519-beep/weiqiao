import tempfile
from pathlib import Path
import unittest
import numpy as np
import torch
from features import encode_states
from models import Critic
from online_critic import EnsembleCritic, encode_observation


class OnlineCriticTests(unittest.TestCase):
    def test_single_observation_offline_parity(self):
        rng = np.random.default_rng(7)
        observation = {key: rng.integers(0, 256, (96, 96, 3), dtype=np.uint8)
                       for key in ('head_rgb', 'left_rgb', 'right_rgb')}
        observation.update(joint_positions=rng.normal(size=38), tcp_pose=rng.normal(size=14))
        data = {key: np.stack([value, value]) for key, value in observation.items()}
        data.update(action_chunks=np.zeros((1, 10, 16)), replan_steps=np.array([27]),
                    final_steps=37, task_limit=1200)
        np.testing.assert_array_equal(encode_observation(observation, 27, 1200), encode_states(data)[0])

    def checkpoints(self, directory):
        scaler = {name: torch.full((width,), value) for name, width, value in (
            ('state_mean', 701, 0.), ('state_scale', 701, 2.),
            ('action_mean', 16, 0.), ('action_scale', 16, 3.))}
        paths = []
        for seed in range(3):
            torch.manual_seed(seed)
            model = Critic(width=16)
            path = Path(directory) / f'{seed}.pt'
            torch.save({'model': model.state_dict(), 'scaler': scaler,
                        'settings': {'seed': seed, 'width': 16, 'state_only': False,
                                     'dataset_manifest_sha256': 'synthetic-test-only',
                                     'variant': 'calibrated1', 'gamma': 1., 'mc_weight': .5}}, path)
            paths.append(path)
        return paths

    def test_checkpoint_scoring_matches_direct_scoring(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = EnsembleCritic(self.checkpoints(directory))
            state = np.ones(701, np.float32)
            actions = np.zeros((4, 10, 16), np.float32)
            actions[1:] = np.arange(1, 4)[:, None, None] * .1
            result = runtime.score(state, actions)
            with torch.no_grad():
                expected = [m.q(torch.ones(4, 701) / 2, torch.from_numpy(actions) / 3).amin(0).numpy()
                            for m in runtime.models]
            np.testing.assert_allclose(result['candidate_q'], expected, atol=1e-7)
            self.assertIn(result['selected_index'], range(4))
            self.assertGreaterEqual(result['latency_seconds'], 0)
            with self.assertRaisesRegex(ValueError, 'diversity'):
                runtime.score(state, np.zeros_like(actions))
            actions[2, 0, 0] = np.nan
            with self.assertRaisesRegex(ValueError, 'nonfinite'):
                runtime.score(state, actions)

    def test_repeated_initialization_seed_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = self.checkpoints(directory)
            with self.assertRaisesRegex(ValueError, 'seeds0/1/2'):
                EnsembleCritic([paths[0]] * 3)
