import unittest

from aggregate_training_v2 import parse_costs, reconcile_entries


class AggregateV2Tests(unittest.TestCase):
    def cohort(self):
        return [{'episode_id': f'train_{i:04d}', 'physical_input_group': str(i),
                 'group_oof_fold': i % 3} for i in range(288)]

    def test_exact_unique_fixed_population(self):
        rows = self.cohort()
        reconcile_entries(rows, {row['episode_id']: row for row in rows})

    def test_recovered_prefix_cannot_count_twice(self):
        rows = self.cohort()
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            reconcile_entries(rows + [rows[30]], {row['episode_id']: row for row in rows})

    def test_missing_entry_cannot_be_replaced(self):
        rows = self.cohort()
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            reconcile_entries(rows[:-1], {row['episode_id']: row for row in rows})

    def test_group_leakage_rejected(self):
        rows = self.cohort()
        rows[1]['physical_input_group'] = rows[0]['physical_input_group']
        with self.assertRaisesRegex(RuntimeError, 'leakage'):
            reconcile_entries(rows, {row['episode_id']: row for row in rows})

    def test_failed_costs_retained(self):
        text = '1593640.316|FAILED|1:0|2825|cpu=16,gres/gpu=1,mem=45G\n'
        result = parse_costs(text, {'1593640.316': ('FAILED', 2825)})
        self.assertEqual(result[0]['gpu_seconds'], 2825)
        self.assertEqual(result[0]['state'], 'FAILED')

    def test_missing_failed_costs_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            parse_costs('', {'1593640.316': ('FAILED', 2825)})

    def test_changed_historical_cost_rejected(self):
        text = '1593640.316|FAILED|1:0|0|cpu=16,gres/gpu=1\n'
        with self.assertRaisesRegex(RuntimeError, 'cost changed'):
            parse_costs(text, {'1593640.316': ('FAILED', 2825)})


if __name__ == '__main__':
    unittest.main()
