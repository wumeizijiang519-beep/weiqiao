import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from corpus_reader import sha
from feature_corpus import OBS_KEYS, encode_episode, persist_episode


class FeatureCorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, count=1):
        folder = self.root / 'logged'
        folder.mkdir()
        (folder / 'EPISODE_COMPLETE').touch()
        (folder / 'runtime_config.json').write_text(json.dumps(dict(task_description='fixed instruction')))
        for i in range(count + 1):
            np.savez(folder / f'observation_{i:04d}.npz',
                     **{key: np.full(3, i, dtype=np.float32) for key in OBS_KEYS})
        records = []
        if count:
            target = folder / 'transition_0000'
            target.mkdir()
            np.savez(target / 'transition.npz', remaining_before=700, actual_length=3,
                     remaining_after=697, future_reward=9999)
            records.append(dict(transition_sha256=sha(target / 'transition.npz')))
        summary = folder / 'summary.json'
        summary.write_text(json.dumps(dict(episode_id='train_0000', replans=count, transitions=records)))
        return dict(episode_id='train_0000', replans=count, summary_sha256=sha(summary), episode_directory=str(folder))

    def encoder(self, obs, description, remaining):
        self.assertEqual(set(obs), set(OBS_KEYS))
        self.assertEqual(description, 'fixed instruction')
        return np.array([obs['agentview_image'][0], remaining / 700], dtype=np.float32)

    def test_encoder_only_receives_current_sensor_and_known_horizon(self):
        values, report = encode_episode(self.fixture(), self.encoder)
        np.testing.assert_allclose(values, [[0, 1], [1, 697 / 700]])
        self.assertEqual(report['observation_count'], 2)

    def test_zero_action_episode_has_one_measured_feature(self):
        values, report = encode_episode(self.fixture(0), self.encoder)
        self.assertEqual(values.shape, (1, 2))
        self.assertTrue(report['zero_transition_episode'])

    def test_features_are_written_once(self):
        entry = self.fixture()
        output = self.root / 'encoded'
        record = persist_episode(output, entry, self.encoder)
        self.assertEqual(sha(output / record['file']), record['sha256'])
        with self.assertRaisesRegex(ValueError, 'exists'):
            persist_episode(output, entry, self.encoder)

    def test_changed_feedback_fails_provenance(self):
        entry = self.fixture()
        path = Path(entry['episode_directory']) / 'transition_0000/transition.npz'
        np.savez(path, remaining_before=700, actual_length=4, remaining_after=696)
        with self.assertRaisesRegex(ValueError, 'archive'):
            encode_episode(entry, self.encoder)

    def test_invalid_feature_dtype_rejected(self):
        with self.assertRaisesRegex(ValueError, 'vector'):
            encode_episode(self.fixture(), lambda *args: np.zeros(2, dtype=np.float64))

    def test_encoder_cannot_mutate_sensor_inputs(self):
        def mutate(obs, *args):
            obs['agentview_image'][0] += 1
            return np.zeros(2, dtype=np.float32)
        with self.assertRaisesRegex(ValueError, 'mutated'):
            encode_episode(self.fixture(), mutate)


if __name__ == '__main__':
    unittest.main()
