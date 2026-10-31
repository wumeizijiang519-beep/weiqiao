"""Fixed-step QGF-v3 training over frozen UNITAS representations."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch

from learning import calibrated_q_loss
from models_v3 import LatentActionCritic
from train_critic import bootstrap_indices, discounted_returns, evaluate

SOURCE_SHA = 'bde57dcd15dddfd07d63fe5209a3faded3e8b7f1e63ddb217a84718e33e74483'


def load_data(directory, device):
    manifest = json.loads((directory / 'manifest.json').read_text())
    if (manifest.get('schema') != 'qgf_v3_unitas_latent_cv_v1' or manifest.get('state_dim') != 9269
            or manifest.get('source_audit_sha256') != SOURCE_SHA or not (directory / 'COMPLETE').exists()):
        raise ValueError('v3 data contract mismatch')
    scaler_path = directory / 'training_scaler.npz'
    if hashlib.sha256(scaler_path.read_bytes()).hexdigest() != manifest['scaler_sha256']:
        raise ValueError('scaler SHA mismatch')
    with np.load(scaler_path, allow_pickle=False) as raw:
        scaler = {key: raw[key].copy() for key in raw.files}
    partitions = {}
    for name, records in manifest['partitions'].items():
        episodes = []
        for record in records:
            path = directory / record['feature_file']
            if hashlib.sha256(path.read_bytes()).hexdigest() != record['feature_sha256']:
                raise ValueError('feature SHA mismatch')
            with np.load(path, allow_pickle=False) as raw:
                states = (raw['states'] - scaler['state_mean']) / scaler['state_scale']
                actions = (raw['actions'] - scaler['action_mean']) / scaler['action_scale']
                arrays = {'states': states[:-1], 'next_states': states[1:], 'actions': actions,
                          'rewards': raw['rewards'], 'steps': raw['steps'], 'terminal': raw['terminal']}
            tensors = {key: torch.as_tensor(value, device=device) for key, value in arrays.items()}
            reward, mc = discounted_returns(tensors['rewards'], tensors['steps'], tensors['terminal'], 1.)
            tensors.update(chunk_reward=reward, mc=mc)
            episodes.append({'seed': int(record['seed']), 'success': bool(record['success']), **tensors})
        partitions[name] = episodes
    if (len(partitions['train']), len(partitions['validation'])) != (45, 15):
        raise ValueError('fixed fold sizes required')
    return partitions, scaler, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--state-only', action='store_true')
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--steps', type=int, default=10000)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--eval-every', type=int, default=500)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    device = torch.device(args.device)
    data, scaler, manifest = load_data(args.data, device)
    bootstrap = bootstrap_indices(data['train'], rng)
    model = LatentActionCritic(state_only=args.state_only).to(device)
    target = deepcopy(model).eval().requires_grad_(False)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    args.output.mkdir(parents=True)
    settings = {**vars(args), 'data': str(args.data), 'output': str(args.output),
                'gamma': 1., 'mc_weight': .5, 'architecture': 'unitas-latent-action-transformer-v1',
                'bootstrap_seeds': [data['train'][i]['seed'] for i in bootstrap],
                'dataset_manifest_sha256': hashlib.sha256((args.data / 'manifest.json').read_bytes()).hexdigest()}
    (args.output / 'config.json').write_text(json.dumps(settings, indent=2, default=str) + '\n')
    started = time.monotonic()
    for step in range(1, args.steps + 1):
        model.train()
        selected = rng.choice(bootstrap, args.batch_size, replace=True)
        draws = [(data['train'][i], int(rng.integers(len(data['train'][i]['states'])))) for i in selected]
        batch = {key: torch.stack([episode[key][row] for episode, row in draws])
                 for key in ('states', 'next_states', 'actions', 'chunk_reward', 'steps', 'terminal', 'mc')}
        with torch.no_grad():
            target_q = target.q(batch['states'], batch['actions']).amin(0)
            td = batch['chunk_reward'] + (~batch['terminal']).float() * model.v(batch['next_states'])
        qloss, _ = calibrated_q_loss(model.q(batch['states'], batch['actions']), td, batch['mc'],
                                     torch.arange(args.batch_size, device=device), mc_weight=.5)
        advantage = target_q - model.v(batch['states'])
        vloss = (torch.where(advantage > 0, .7, .3) * advantage.square()).mean()
        loss = qloss + vloss
        if not torch.isfinite(loss):
            raise FloatingPointError('nonfinite loss')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10., error_if_nonfinite=True)
        optimizer.step()
        with torch.no_grad():
            for old, new in zip(target.parameters(), model.parameters(), strict=True):
                old.lerp_(new, .005)
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            metrics = {'step': step, 'loss': float(loss.detach()), 'elapsed_seconds': time.monotonic() - started,
                       **evaluate(model, data['validation'])}
            with (args.output / 'metrics.jsonl').open('a') as stream:
                stream.write(json.dumps(metrics) + '\n')
            payload = {'model': {k: v.detach().cpu() for k, v in model.state_dict().items()},
                       'settings': settings, 'validation': metrics}
            torch.save(payload, args.output / 'latest.tmp.pt')
            (args.output / 'latest.tmp.pt').replace(args.output / 'latest.pt')
            print(json.dumps({k: v for k, v in metrics.items() if k not in ('initial', 'per_episode')}), flush=True)
    (args.output / 'COMPLETE').touch()


if __name__ == '__main__':
    main()
