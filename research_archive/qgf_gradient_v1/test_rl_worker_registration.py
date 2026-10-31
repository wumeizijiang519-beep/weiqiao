import unittest

from train_rl_fold import SOURCES, validate_registration


class WorkerRegistrationTests(unittest.TestCase):
    def fixture(self):
        return dict(seed=202640101, held_fold=0, updates=20000, batch_size=128,
                    learning_rate=3e-4, gamma=1., expectile=.7, target_ema=.005,
                    width=256, hard_gpu_seconds=1200,
                    source_sha256={name: '0' * 64 for name in SOURCES})

    def test_fixed_oof_and_full_parameters(self):
        value = self.fixture()
        validate_registration(value)
        value['held_fold'] = 'full'
        validate_registration(value)

    def test_cannot_shorten_updates_or_pick_seed(self):
        for key, changed in [('updates', 19999), ('seed', 42), ('width', 512), ('held_fold', 3)]:
            value = self.fixture()
            value[key] = changed
            with self.assertRaises(ValueError):
                validate_registration(value)

    def test_missing_source_and_excess_budget_rejected(self):
        value = self.fixture()
        value['source_sha256'].pop('matched_iql.py')
        with self.assertRaises(ValueError):
            validate_registration(value)
        value = self.fixture()
        value['hard_gpu_seconds'] = 1201
        with self.assertRaises(ValueError):
            validate_registration(value)


if __name__ == '__main__':
    unittest.main()
