import torch

from simplewam_visual_rl.features import SimpleWAMFeatureSpec, extract_current_video_features
from simplewam_visual_rl.learning import chunk_td_target, planned_prefix


def test_current_frame_camera_coordinates():
    # [time=2, row=2, concatenated camera width=4], one scalar per token.
    values = torch.arange(16, dtype=torch.float32).reshape(1, 16, 1)
    features, positions = extract_current_video_features(
        {3: values}, (2, 2, 4), SimpleWAMFeatureSpec((3,), num_views=2)
    )
    assert features.shape == (1, 8, 1)
    assert features.flatten().tolist() == [0.0, 1.0, 4.0, 5.0, 2.0, 3.0, 6.0, 7.0]
    assert positions.shape == (8, 5)
    assert positions[:, 2].eq(0).all()
    assert set(positions[:, 1].tolist()) == {-1.0, 1.0}


def test_q_input_does_not_use_realized_length():
    actions = torch.arange(2 * 4 * 2, dtype=torch.float32).reshape(2, 4, 2)
    planned = torch.tensor([4, 3])
    first = planned_prefix(actions, planned, 4)
    # Different realized lengths are deliberately absent from this function.
    second = planned_prefix(actions, planned, 4)
    torch.testing.assert_close(first, second, rtol=0, atol=0)
    assert second[1, 3].eq(0).all()


def test_td_target_uses_real_feedback_length():
    rewards = torch.tensor([[1.0, 2.0, 0.0], [3.0, 0.0, 0.0]])
    target = chunk_td_target(
        rewards,
        torch.tensor([2, 1]),
        torch.tensor([False, True]),
        torch.tensor([10.0, 10.0]),
        0.5,
    )
    torch.testing.assert_close(target, torch.tensor([4.5, 3.0]))
