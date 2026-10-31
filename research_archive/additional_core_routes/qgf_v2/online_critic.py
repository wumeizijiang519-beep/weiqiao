"""Reward-free ensemble scoring; integration is gated on real checkpoint parity."""
import hashlib
from pathlib import Path
import time
import numpy as np
import torch
from features import CAMERAS, encode_states
from models import Critic
from selection import SelectionConfig, select_candidate


def encode_observation(observation, elapsed_steps, task_limit):
    """Use the identical offline encoder on a single current observation."""
    data = {key: np.asarray(observation[key])[None] for key in CAMERAS}
    data.update(joint_positions=np.asarray(observation['joint_positions'])[None],
                tcp_pose=np.asarray(observation['tcp_pose'])[None],
                action_chunks=np.empty((0, 10, 16), dtype=np.float32),
                replan_steps=np.empty(0), final_steps=elapsed_steps, task_limit=task_limit)
    return encode_states(data)[0]


class EnsembleCritic:
    def __init__(self, checkpoints, device='cpu'):
        if len(checkpoints) != 3:
            raise ValueError('exactly three independent critic checkpoints required')
        self.device = torch.device(device)
        self.models, self.hashes = [], []
        seeds, contracts = set(), set()
        self.scaler = None
        for checkpoint in checkpoints:
            path = Path(checkpoint)
            payload = torch.load(path, map_location='cpu', weights_only=True)
            settings = payload['settings']
            seeds.add(settings['seed'])
            contracts.add((settings['dataset_manifest_sha256'], settings['variant'],
                           settings['gamma'], settings['mc_weight'], settings['state_only']))
            scaler = {key: value.numpy() for key, value in payload['scaler'].items()}
            for name, width in (('state_mean', 701), ('state_scale', 701),
                                ('action_mean', 16), ('action_scale', 16)):
                value = scaler[name]
                if value.shape != (width,) or not np.isfinite(value).all():
                    raise ValueError('invalid checkpoint scaler')
                if name.endswith('scale') and (value <= 0).any():
                    raise ValueError('scaler must be positive')
                if self.scaler is not None and not np.array_equal(value, self.scaler[name]):
                    raise ValueError('ensemble normalization mismatch')
            self.scaler = scaler
            model = Critic(width=settings['width'], state_only=settings['state_only'])
            model.load_state_dict(payload['model'], strict=True)
            if not all(torch.isfinite(p).all() for p in model.parameters()):
                raise ValueError('nonfinite checkpoint parameter')
            self.models.append(model.to(self.device).eval().requires_grad_(False))
            self.hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
        if seeds != {0, 1, 2} or len(contracts) != 1:
            raise ValueError('need seeds0/1/2 with identical data and objective')

    @torch.inference_mode()
    def score(self, state, candidates, config=SelectionConfig()):
        started = time.perf_counter()
        state = np.asarray(state, dtype=np.float32)
        candidates = np.asarray(candidates, dtype=np.float32)
        if state.shape != (701,) or candidates.shape != (4, 10, 16):
            raise ValueError('expected one701D state and four10x16 candidate chunks')
        if not np.isfinite(state).all() or not np.isfinite(candidates).all():
            raise ValueError('nonfinite input; caller must not execute invalid actions')
        if not any(not np.array_equal(candidates[0], row) for row in candidates[1:]):
            raise ValueError('candidate diversity gate failed')
        normalized_state = (state - self.scaler['state_mean']) / self.scaler['state_scale']
        normalized_actions = (candidates - self.scaler['action_mean']) / self.scaler['action_scale']
        states = torch.as_tensor(np.repeat(normalized_state[None], 4, axis=0), device=self.device)
        actions = torch.as_tensor(normalized_actions, device=self.device)
        q = torch.stack([model.q(states, actions).amin(0) for model in self.models])
        scores = q.cpu().numpy()
        if not np.isfinite(scores).all():
            raise ValueError('nonfinite critic scores')
        result = select_candidate(scores.tolist(), candidates.tolist(),
                                  self.scaler['action_scale'].tolist(), config)
        distances = np.sqrt(np.mean((normalized_actions - normalized_actions[0]) ** 2, axis=(1, 2)))
        mean_q = scores.mean(0)
        ordered = np.sort(mean_q)
        result.update(candidate_q=scores.tolist(), mean_q=mean_q.tolist(),
                      ungated_index=int(mean_q.argmax()), top_two_margin=float(ordered[-1] - ordered[-2]),
                      normalized_candidate_distance=distances.tolist(),
                      latency_seconds=time.perf_counter() - started,
                      checkpoint_sha256=self.hashes,
                      note='ensemble disagreement is heuristic, not a calibrated confidence bound')
        return result
