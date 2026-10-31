import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from corpus_reader import sha
from feature_publication import inherit_pilot, publish_index, validate_block


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fixture(self, count=2):
        pilot = self.root / 'pilot'
        (pilot / 'blocks').mkdir(parents=True)
        population, records = {}, []
        for i in range(count):
            name = f'train_{i:04d}'
            file = pilot / 'blocks' / (name + '.npz')
            np.savez(file, current_features=np.zeros((2, 3), dtype=np.float32))
            population[name] = dict(episode_id=name, replans=1, summary_sha256='0' * 64)
            records.append(dict(episode_id=name, file=file.name, sha256=sha(file),
                                summary_sha256='0' * 64, observation_file_sha256=['1' * 64] * 2))
        return dict(episodes=records, run_directory=str(pilot)), population

    def test_inherited_blocks_are_identical_not_reencoded(self):
        pilot, population = self.fixture()
        run = self.root / 'new'
        run.mkdir()
        rows = inherit_pilot(run, pilot, population, 3)
        self.assertEqual(len(rows), 2)
        self.assertFalse(json.loads((run / 'blocks/train_0000.json').read_text())['reencoded'])
        self.assertEqual(sha(run / 'blocks/train_0000.npz'), rows[0]['sha256'])

    def test_bad_block_hash_rejected(self):
        pilot, population = self.fixture()
        row = pilot['episodes'][0]
        row['sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'hash'):
            validate_block(Path(pilot['run_directory']) / 'blocks' / row['file'], row, population[row['episode_id']], 3)

    def test_partial_index_never_published(self):
        pilot, population = self.fixture()
        with self.assertRaisesRegex(ValueError, 'fixed288'):
            publish_index(self.root, pilot['episodes'], population, 3, '0' * 64, self.root / 'absent', 'f' * 64)


if __name__ == '__main__':
    unittest.main()
