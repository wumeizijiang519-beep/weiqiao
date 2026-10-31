import unittest

from aggregate_training import qualification


class QualificationTests(unittest.TestCase):
    def rows(self):
        return [{'success': bool(i % 2), 'physical_input_group': str(i), 'group_oof_fold': i % 3}
                for i in range(24)]

    def test_exact_minimum_passes_without_expansion(self):
        result = qualification(self.rows())
        self.assertEqual(result['status'], 'ADMIT_FOR_RL_QUALIFICATION')

    def test_many_episodes_in_too_few_groups_fail(self):
        rows = self.rows()
        for row in rows:
            row['physical_input_group'] = 'same-group'
        self.assertEqual(qualification(rows)['status'], 'DATA_INSUFFICIENT_FOR_VALUE_IDENTIFICATION')

    def test_global_balance_does_not_replace_fold_coverage(self):
        rows = self.rows()
        for row in rows:
            row['group_oof_fold'] = int(row['success'])
        self.assertFalse(qualification(rows)['checks']['every_group_oof_fold_has_both_classes'])


if __name__ == '__main__':
    unittest.main()
