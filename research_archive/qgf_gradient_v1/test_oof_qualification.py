import copy
import unittest

import numpy as np

from qualify_rl_oof import calibration, offline_gate


class QualificationTests(unittest.TestCase):
    def passing(self):
        return dict(per_seed_episode_equal_errors={str(seed): dict(action_mse=.1,
            state_only_mse=.2, permutation_mse=.3, within_model_permutation_error_increase=.1)
            for seed in (202640101,202640102,202640103)}, paired_group_intervals={
                name: dict(paired_physical_group_percentile95_ci=[.01,.2]) for name in
                ('state_only_minus_action','permutation_minus_action','action_permuted_minus_action')})

    def test_all_required_evidence_passes(self):
        self.assertEqual(offline_gate(self.passing())['status'], 'ADMIT_FOR_FIXED_ALL_TRAINING_REFITS')

    def test_single_bad_seed_stops_no_cherry_picking(self):
        value = self.passing()
        value['per_seed_episode_equal_errors']['202640103']['state_only_mse'] = .09
        self.assertTrue(offline_gate(value)['status'].startswith('NO_STABLE'))

    def test_nonsensitive_or_uncertain_control_stops(self):
        value = self.passing()
        value['per_seed_episode_equal_errors']['202640101']['within_model_permutation_error_increase'] = 0
        self.assertTrue(offline_gate(value)['status'].startswith('NO_STABLE'))
        value = self.passing()
        value['paired_group_intervals']['permutation_minus_action']['paired_physical_group_percentile95_ci'] = [-.1,.2]
        self.assertTrue(offline_gate(value)['status'].startswith('NO_STABLE'))

    def test_missing_seed_and_invalid_ci_rejected(self):
        value = self.passing()
        value['per_seed_episode_equal_errors'].pop('202640103')
        with self.assertRaises(ValueError):
            offline_gate(value)
        value = self.passing()
        value['paired_group_intervals']['state_only_minus_action']['paired_physical_group_percentile95_ci'] = [.2,.1]
        with self.assertRaises(ValueError):
            offline_gate(value)

    def test_calibration_is_episode_equal_and_does_not_clip_predictions(self):
        values = calibration(np.array([2.,0.,0.]), np.array([0.,0.,0.]), np.array(['a','b','b']))
        self.assertEqual(values['episode_equal_absolute_calibration_error'], 1.)
        self.assertEqual(values['out_of_unit_interval_predictions'], 1)
        self.assertFalse(values['predictions_clipped_for_mse_or_bin_means'])


if __name__ == '__main__':
    unittest.main()
