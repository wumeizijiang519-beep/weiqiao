import unittest

from extract_remaining_features import REQUIRED_SOURCES, validate_registration


class RegistrationTests(unittest.TestCase):
    def registration(self):
        return dict(stage='REMAINING_FIXED_286_FEATURE_EXTRACTION',
                    episode_ids=[f'train_{i:04d}' for i in range(2, 288)],
                    hard_gpu_seconds=5400,
                    source_sha256={name: '0' * 64 for name in REQUIRED_SOURCES})

    def test_exact_remaining_population(self):
        validate_registration(self.registration())

    def test_pilot_reencoding_rejected(self):
        value = self.registration()
        value['episode_ids'][0] = 'train_0000'
        with self.assertRaises(ValueError):
            validate_registration(value)

    def test_budget_and_missing_source_rejected(self):
        value = self.registration()
        value['hard_gpu_seconds'] = 5401
        with self.assertRaises(ValueError):
            validate_registration(value)
        value = self.registration()
        value['source_sha256'].pop('feature_publication.py')
        with self.assertRaises(ValueError):
            validate_registration(value)


if __name__ == '__main__':
    unittest.main()
