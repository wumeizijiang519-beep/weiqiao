"""Matched TD targets and decision-time masks for IQL/control qualification."""

import copy

import torch

from core import iql_losses, semimdp_target


class MatchedIQL:
    def __init__(self, model, learning_rate=3e-4, expectile=.7, tau=.005, gamma=1., mc_ablation=True):
        if not 0 < tau <= 1 or not 0 < expectile < 1:
            raise ValueError('Invalid fixed IQL parameters')
        names = ['action', 'state_only', 'permutation'] + (['mc_action'] if mc_ablation else [])
        self.models = {name: copy.deepcopy(model) for name in names}
        self.targets = {name: copy.deepcopy(value).requires_grad_(False)
                        for name, value in self.models.items()}
        self.optimizers = {name: torch.optim.Adam(value.parameters(), lr=learning_rate)
                           for name, value in self.models.items()}
        self.expectile, self.tau, self.gamma = expectile, tau, gamma
        self.last_td_target = None

    @staticmethod
    def action_input(name, batch):
        if name == 'state_only':
            return torch.zeros_like(batch['action'])
        if name == 'permutation':
            index = batch['permutation_index']
            return batch['bank'][torch.arange(len(index), device=index.device), index]
        return batch['action']

    def update(self, batch):
        mask, actual, remaining = batch['mask'], batch['executed_steps'], batch['remaining_before']
        planned = torch.minimum(remaining, torch.full_like(remaining, 10))
        if not torch.equal(mask.sum(1), planned) or (actual < 1).any() or (actual > planned).any():
            raise ValueError('Critic mask must be known planned length; TD uses actual feedback length')
        primary_target = self.targets['action']
        with torch.no_grad():
            td_target = semimdp_target(
                batch['rewards'], actual, batch['terminal'],
                primary_target.value(batch['next_observation']).squeeze(-1), self.gamma)
        self.last_td_target = td_target.detach().clone()
        losses = {}
        for name, model in self.models.items():
            action = self.action_input(name, batch)
            target = self.targets[name]
            with torch.no_grad():
                target_q = target.conservative_q(batch['observation'], action, mask)
                label = batch['mc_return'] if name == 'mc_action' else td_target
            q1, q2 = model.q1(batch['observation'], action, mask), model.q2(batch['observation'], action, mask)
            value = model.value(batch['observation']).squeeze(-1)
            qloss, vloss = iql_losses(q1, q2, value, target_q, label,
                                       batch['episode_weights'], self.expectile)
            optimizer = self.optimizers[name]
            optimizer.zero_grad(set_to_none=True)
            (qloss + vloss).backward()
            # Infinity leaves the gradient unchanged; the finite check is still enforced.
            torch.nn.utils.clip_grad_norm_(model.parameters(), float('inf'), error_if_nonfinite=True)
            optimizer.step()
            with torch.no_grad():
                for parameter, target_parameter in zip(model.parameters(), target.parameters()):
                    target_parameter.lerp_(parameter, self.tau)
            losses[name] = {'q_loss': qloss.detach(), 'value_loss': vloss.detach(),
                            'target': label.detach().clone()}
        return losses
