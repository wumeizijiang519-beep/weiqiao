import unittest
from prepare_dataset import split_rows


class ExtensionSplitTests(unittest.TestCase):
    def test_all_admitted_prevalences(self):
        for failures in range(6, 55):
            rows = [{'seed': n, 'success': n >= failures} for n in range(60)]
            train, val = split_rows(rows, 202616500, 60, 12)
            self.assertEqual((len(train), len(val)), (48, 12))
            self.assertGreaterEqual(sum(not r['success'] for r in train), 4)
            self.assertGreaterEqual(sum(not r['success'] for r in val), 2)
            self.assertTrue(any(r['success'] for r in train))
            self.assertTrue(any(r['success'] for r in val))
            self.assertFalse({r['seed'] for r in train} & {r['seed'] for r in val})

    def test_insufficient_failures_stop(self):
        rows = [{'seed': n, 'success': n >= 5} for n in range(60)]
        with self.assertRaisesRegex(ValueError, 'STOP_INSUFFICIENT_CLASSES'):
            split_rows(rows, 202616500, 60, 12)
