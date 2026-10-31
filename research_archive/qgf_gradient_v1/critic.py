"""Small action-injected twin-Q / IQL value model; never loads old critics."""

import copy
import torch
from torch import nn

from core import iql_losses, semimdp_target


class ActionQ(nn.Module):
    def __init__(self, observation_dim, horizon=10, action_dim=7, width=256):
        super().__init__()
        self.horizon, self.action_dim = horizon, action_dim
        # Actual-length mask is an input, so a terminal short prefix is distinct
        # from a full prefix whose last actions happen to be zero.
        action_input = horizon * (action_dim + 1)
        self.first = nn.Linear(observation_dim + action_input, width)
        self.second = nn.Linear(width + action_input, width)
        self.last = nn.Linear(width + action_input, 1)

    def forward(self, observation, action, mask):
        if action.shape[1:] != (self.horizon, self.action_dim) or mask.shape != action.shape[:2]:
            raise ValueError('Invalid committed-prefix shape or mask')
        if mask.dtype != torch.bool or (mask[:, 1:] > mask[:, :-1]).any() or not mask[:, 0].all():
            raise ValueError('Prefix mask must be nonempty and contiguous')
        if not torch.isfinite(action[mask]).all():
            raise ValueError('Non-finite executed action')
        masked = torch.where(mask[:, :, None], action, 0)
        inputs = torch.cat((masked.flatten(1), mask.float()), 1)
        hidden = torch.nn.functional.silu(self.first(torch.cat((observation, inputs), 1)))
        hidden = torch.nn.functional.silu(self.second(torch.cat((hidden, inputs), 1)))
        return self.last(torch.cat((hidden, inputs), 1)).squeeze(-1)


class TwinQValue(nn.Module):
    def __init__(self, observation_dim, horizon=10, action_dim=7, width=256):
        super().__init__()
        self.q1 = ActionQ(observation_dim, horizon, action_dim, width)
        self.q2 = ActionQ(observation_dim, horizon, action_dim, width)
        self.value = nn.Sequential(nn.Linear(observation_dim, width), nn.SiLU(),
                                   nn.Linear(width, width), nn.SiLU(), nn.Linear(width, 1))

    def conservative_q(self, observation, action, mask):
        return torch.minimum(self.q1(observation, action, mask), self.q2(observation, action, mask))


class IQLLearner:
    def __init__(self, model, learning_rate=3e-4, gamma=1., expectile=.7, tau=.005):
        self.model = model
        self.target = copy.deepcopy(model).requires_grad_(False)
        self.optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        if not 0 < tau <= 1:
            raise ValueError('Invalid EMA coefficient')
        self.gamma, self.expectile, self.tau = gamma, expectile, tau

    def update(self, batch):
        model, target = self.model, self.target
        observation, action, mask = (batch[name] for name in ('observation', 'action', 'mask'))
        if not torch.equal(mask.sum(1), batch['executed_steps']):
            raise ValueError('Action mask does not match actual execution length')
        # States must include remaining horizon, and the collector supplies true
        # finite-task terminal status, including its registered step deadline.
        with torch.no_grad():
            td = semimdp_target(batch['rewards'], batch['executed_steps'], batch['terminal'],
                                target.value(batch['next_observation']).squeeze(-1), self.gamma)
            tq = target.conservative_q(observation, action, mask)
        q1, q2 = model.q1(observation, action, mask), model.q2(observation, action, mask)
        value = model.value(observation).squeeze(-1)
        qloss, vloss = iql_losses(q1, q2, value, tq, td, batch['episode_weights'], self.expectile)
        self.optimizer.zero_grad(set_to_none=True)
        (qloss + vloss).backward()
        for parameter in model.parameters():
            if parameter.grad is not None and not torch.isfinite(parameter.grad).all():
                self.optimizer.zero_grad(set_to_none=True)
                raise RuntimeError('Non-finite RL gradient')
        self.optimizer.step()
        with torch.no_grad():
            for source, destination in zip(model.parameters(), target.parameters()):
                destination.lerp_(source, self.tau)
        return {'q_loss': float(qloss.detach()), 'v_loss': float(vloss.detach())}
