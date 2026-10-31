import torch

from simplewam_visual_rl.deployment import QGFConfig
from simplewam_visual_rl.models import VisualTwinQ


def test_visual_twin_q_action_gradient_and_frozen_parameters():
    critic = VisualTwinQ().eval().requires_grad_(False)
    state = torch.randn(2, 2057)
    action = torch.randn(2, 10, 7, requires_grad=True)
    score = critic(state, action).min(0).values
    gradient, = torch.autograd.grad(score.sum(), action)
    assert gradient.shape == action.shape
    assert torch.isfinite(gradient).all()
    assert all(parameter.grad is None for parameter in critic.parameters())


def test_qgf_contract_excludes_gripper():
    config = QGFConfig()
    assert config.execution_horizon == 10
    assert config.action_dim == 7
    assert config.continuous_dims == 6
