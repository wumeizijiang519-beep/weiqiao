import unittest
from prepare_dataset import split_rows


class SplitTests(unittest.TestCase):
    def test_class_extremes_and_no_overlap(self):
        for failures in (6, 12, 34):
            rows = [{'seed': n, 'success': n >= failures} for n in range(40)]
            train, validation = split_rows(rows)
            self.assertEqual((len(train), len(validation)), (32, 8))
            self.assertGreaterEqual(sum(not r['success'] for r in train), 4)
            self.assertGreaterEqual(sum(not r['success'] for r in validation), 2)
            self.assertTrue(any(r['success'] for r in train))
            self.assertTrue(any(r['success'] for r in validation))
            self.assertFalse({r['seed'] for r in train} & {r['seed'] for r in validation})
            self.assertEqual((train, validation), split_rows(list(reversed(rows))))

    def test_single_class_rejected(self):
        with self.assertRaises(ValueError):
            split_rows([{'seed': n, 'success': True} for n in range(40)])


if __name__ == '__main__':
    unittest.main()
