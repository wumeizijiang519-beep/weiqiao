import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from corpus_reader import MANIFEST_SHA, certified_population, contained_file, read_episode, sha
from test_rl_corpus import transition


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def population(self):
        return dict(status='ADMIT_FOR_RL_QUALIFICATION', episodes=288,
                    manifest_sha256=MANIFEST_SHA, checks={'frozen_gate': True},
                    entries=[dict(episode_id=f'train_{i:04d}', physical_input_group=f'g{i}',
                                  group_oof_fold=i % 3, audit_pass=True) for i in range(288)])

    def certificate(self, data):
        path = self.root / 'dataset.json'
        path.write_text(json.dumps(data))
        return path, sha(path)

    def fixture(self, count=1):
        folder = self.root / 'episode'
        folder.mkdir()
        (folder / 'EPISODE_COMPLETE').touch()
        observations = []
        for i in range(count + 1):
            path = folder / f'observation_{i:04d}.npz'
            np.savez(path, measured=np.zeros(3))
            observations.append(sha(path))
        records = []
        if count:
            target = folder / 'transition_0000'
            target.mkdir()
            np.savez(target / 'transition.npz', **transition(20, [1], True))
            records.append(dict(transition_sha256=sha(target / 'transition.npz')))
        summary = dict(episode_id='train_0000', physical_input_group='g', replans=count,
                       success=True, transitions=records)
        path = folder / 'summary.json'
        path.write_text(json.dumps(summary))
        entry = dict(summary, episode_directory=str(folder), summary_sha256=sha(path), group_oof_fold=0)
        return entry, np.zeros((count + 1, 4), dtype=np.float32), observations

    def test_population_and_hash_guard(self):
        path, digest = self.certificate(self.population())
        self.assertEqual(len(certified_population(path, digest)), 288)
        with self.assertRaisesRegex(ValueError, 'hash'):
            certified_population(path, '0' * 64)

    def test_incomplete_population_is_not_admitted(self):
        data = self.population()
        data['entries'].pop()
        with self.assertRaisesRegex(ValueError, 'union'):
            certified_population(*self.certificate(data))

    def test_group_leakage_rejected(self):
        data = self.population()
        data['entries'][1]['physical_input_group'] = 'g0'
        with self.assertRaisesRegex(ValueError, 'leakage'):
            certified_population(*self.certificate(data))

    def test_episode_feedback_and_features(self):
        arrays, info = read_episode(*self.fixture())
        self.assertEqual(info['fitting_rows'], 1)
        self.assertEqual(arrays['mask'].sum(), 10)
        self.assertEqual(arrays['executed_steps'][0], 1)

    def test_zero_transition_remains_in_ledger_without_labels(self):
        arrays, info = read_episode(*self.fixture(count=0))
        self.assertIsNone(arrays)
        self.assertTrue(info['zero_transition_episode'])
        self.assertTrue(info['success'])

    def test_observation_provenance_rejected(self):
        entry, values, hashes = self.fixture()
        hashes[0] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'provenance'):
            read_episode(entry, values, hashes)

    def test_missing_final_feature_rejected(self):
        entry, values, hashes = self.fixture()
        with self.assertRaisesRegex(ValueError, 'R\+1'):
            read_episode(entry, values[:-1], hashes)

    def test_artifact_path_escape_rejected(self):
        with self.assertRaisesRegex(ValueError, 'escaped'):
            contained_file(self.root, '../not_registered.npz')


if __name__ == '__main__':
    unittest.main()
