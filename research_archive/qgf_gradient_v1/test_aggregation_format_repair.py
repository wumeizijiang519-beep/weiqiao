import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from aggregate_training_v2_format_repair import verify_saved_registration


class FormatRepairTests(unittest.TestCase):
    def fixture(self, changed=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        registration = root / 'shard0.json'
        run = root / 'run'
        run.mkdir()
        registration.write_text(json.dumps({'seed': 10, 'episode_ids': ['fixed']}, indent=2))
        saved = run / 'registration.json'
        saved.write_text(json.dumps({'seed': 11 if changed else 10, 'episode_ids': ['fixed']}, sort_keys=True))
        digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
        return dict(registration=str(registration), run_directory=str(run), sha256=digest(registration)), digest(saved)

    def test_only_serialization_difference_passes(self):
        row, saved_sha = self.fixture()
        with patch.dict('aggregate_training_v2_format_repair.SAVED_REGISTRATION_SHA', {'shard0.json': saved_sha}):
            verify_saved_registration(row)

    def test_changed_scientific_value_rejected_even_with_raw_pins(self):
        row, saved_sha = self.fixture(changed=True)
        with patch.dict('aggregate_training_v2_format_repair.SAVED_REGISTRATION_SHA', {'shard0.json': saved_sha}):
            with self.assertRaisesRegex(RuntimeError, 'values differ'):
                verify_saved_registration(row)

    def test_changed_raw_bytes_rejected(self):
        row, saved_sha = self.fixture()
        with patch.dict('aggregate_training_v2_format_repair.SAVED_REGISTRATION_SHA', {'shard0.json': '0' * 64}):
            with self.assertRaisesRegex(RuntimeError, 'raw registration'):
                verify_saved_registration(row)


if __name__ == '__main__':
    unittest.main()
