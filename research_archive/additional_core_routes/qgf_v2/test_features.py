import unittest
import numpy as np
from features import encode_states, training_scaler


class FeatureTests(unittest.TestCase):
    def test_camera_order_and_remaining_time(self):
        data = {'action_chunks': np.zeros((1, 10, 16)),
                'joint_positions': np.zeros((2, 38)), 'tcp_pose': np.zeros((2, 14)),
                'replan_steps': np.array([0]), 'final_steps': 10, 'task_limit': 20}
        for name, value in (('head_rgb', 0), ('left_rgb', 255), ('right_rgb', 127)):
            data[name] = np.full((2, 96, 96, 3), value, dtype=np.uint8)
        state = encode_states(data)
        self.assertEqual(state.shape, (2, 701))
        np.testing.assert_allclose(state[:, :3], 0)
        np.testing.assert_allclose(state[:, 216:219], 1)
        np.testing.assert_allclose(state[:, 432:435], 127 / 255, atol=1e-5)
        np.testing.assert_allclose(state[:, -1], [1, .5])

    def test_equal_episode_weight_not_row_weight(self):
        episodes = [{'states': np.zeros((2, 701), np.float32),
                     'actions': np.zeros((1, 10, 16), np.float32)},
                    {'states': np.ones((101, 701), np.float32),
                     'actions': np.ones((100, 10, 16), np.float32)}]
        scaler = training_scaler(episodes)
        np.testing.assert_allclose(scaler['state_mean'], .5)
        np.testing.assert_allclose(scaler['action_mean'], .5)
        np.testing.assert_allclose(scaler['state_scale'], .5)


if __name__ == '__main__':
    unittest.main()
