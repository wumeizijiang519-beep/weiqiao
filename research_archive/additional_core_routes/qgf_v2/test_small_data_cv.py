import unittest
from prepare_small_data_cv import folds_for


class SmallCVTests(unittest.TestCase):
    def test_fold_isolation_and_coverage(self):
        rows = [{'seed': n, 'success': n >= 4} for n in range(60)]
        folds = folds_for(rows)
        held = []
        for train, validation in folds:
            self.assertEqual((len(train), len(validation)), (45, 15))
            self.assertEqual(sum(not r['success'] for r in train), 3)
            self.assertEqual(sum(not r['success'] for r in validation), 1)
            self.assertFalse({r['seed'] for r in train} & {r['seed'] for r in validation})
            held.extend(r['seed'] for r in validation)
        self.assertEqual(sorted(held), list(range(60)))
        self.assertEqual(folds, folds_for(list(reversed(rows))))

    def test_wrong_population_is_rejected(self):
        with self.assertRaises(ValueError):
            folds_for([{'seed': n, 'success': n >= 5} for n in range(60)])
