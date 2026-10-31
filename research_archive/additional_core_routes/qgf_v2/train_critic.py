"""Train a fixed-data MC/TD ablation with episode bootstrap and persistent checkpoints."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from torch.nn import functional as F
from learning import calibrated_q_loss
from models import Critic


def discounted_returns(rewards, steps, terminal, gamma):
    index = torch.arange(rewards.shape[1], device=rewards.device)
    reward = (rewards * gamma ** index * (index[None] < steps[:, None])).sum(1)
    result = torch.zeros_like(reward)
    value = reward.new_zeros(())
    for n in range(len(reward) - 1, -1, -1):
        value = reward[n] + gamma ** steps[n] * (~terminal[n]).float() * value
        result[n] = value
    return reward, result


def load_data(directory, device, gamma, *, small_data_cv=False):
    manifest = json.loads((directory / 'manifest.json').read_text())
    if not (directory / 'COMPLETE').exists() or manifest['state_dim'] != 701:
        raise ValueError('dataset export is not complete or feature contract mismatches')
    scaler_path = directory / 'training_scaler.npz'
    if hashlib.sha256(scaler_path.read_bytes()).hexdigest() != manifest['scaler_sha256']:
        raise ValueError('scaler SHA mismatch')
    with np.load(scaler_path, allow_pickle=False) as raw:
        scaler = {key: raw[key].copy() for key in raw.files}
    partitions = {}
    for partition, records in manifest['partitions'].items():
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
            reward, mc = discounted_returns(tensors['rewards'], tensors['steps'], tensors['terminal'], gamma)
            tensors.update(chunk_reward=reward, mc=mc)
            episodes.append({'seed': int(record['seed']), 'success': bool(record['success']), **tensors})
        partitions[partition] = episodes
    contract = (manifest.get('dataset_episode_count', 40), manifest['split_seed'])
    if small_data_cv:
        if (manifest['schema'] != 'qgf_v2_small_data_cv_v1' or contract != (60, 202621500)
                or manifest['source_audit_sha256'] != 'bde57dcd15dddfd07d63fe5209a3faded3e8b7f1e63ddb217a84718e33e74483'
                or manifest['fold'] not in range(4)):
            raise ValueError('small-data diagnostic contract mismatch')
    elif contract not in ((40, 202615500), (60, 202616500)):
        raise ValueError('unregistered dataset contract')
    train_count, val_count = (45, 15) if small_data_cv else ((32, 8) if contract[0] == 40 else (48, 12))
    if len(partitions['train']) != train_count or len(partitions['validation']) != val_count:
        raise ValueError('fixed registered split is required before real training')
    train_seeds = {row['seed'] for row in partitions['train']}
    validation_seeds = {row['seed'] for row in partitions['validation']}
    if len(train_seeds) != train_count or len(validation_seeds) != val_count or train_seeds & validation_seeds:
        raise ValueError('episode uniqueness or isolation failure')
    minima = (('train', 3), ('validation', 1)) if small_data_cv else (('train', 4), ('validation', 2))
    for name, minimum in minima:
        if sum(not row['success'] for row in partitions[name]) < minimum or not any(row['success'] for row in partitions[name]):
            raise ValueError('failure/success training admission not met')
        if small_data_cv and sum(not row['success'] for row in partitions[name]) != minimum:
            raise ValueError('CV requires exactly3/1 held-out failure assignment')
    return partitions, scaler, manifest


def bootstrap_indices(episodes, rng):
    result = []
    for label in (False, True):
        indices = [n for n, row in enumerate(episodes) if row['success'] == label]
        if not indices:
            raise ValueError('bootstrap requires both outcome classes')
        result.extend(rng.choice(indices, len(indices), replace=True).tolist())
    return np.asarray(result)


@torch.no_grad()
def evaluate(model, episodes):
    squared_errors, initial, shuffled_changes, common_errors, per_episode = [], [], [], [], []
    model.eval()
    for row in episodes:
        scores = model.q(row['states'], row['actions']).amin(0)
        squared_errors.append(float((scores - row['mc']).square().mean()))
        common = float((scores - float(row['success'])).square().mean())
        common_errors.append(common)
        per_episode.append({'seed': row['seed'], 'success': row['success'],
                            'matched_mc_mse': squared_errors[-1], 'undiscounted_success_mse': common})
        initial.append({'seed': row['seed'], 'success': row['success'], 'q_initial': float(scores[0])})
        shuffled = model.q(row['states'], row['actions'].roll(1, dims=0)).amin(0)
        shuffled_changes.append(float((scores - shuffled).abs().mean()))
    return {'episode_equal_mc_mse': float(np.mean(squared_errors)),
            'action_shuffle_abs_delta': float(np.mean(shuffled_changes)), 'initial': initial,
            'episode_equal_undiscounted_success_mse': float(np.mean(common_errors)),
            'per_episode': per_episode}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--variant', choices=['td099', 'td1', 'calibrated1'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--state-only', action='store_true')
    parser.add_argument('--small-data-cv', action='store_true', help='separate diagnostic protocol; does not relax old data gate')
    parser.add_argument('--device', default='cuda')
    parser.add_argument('--steps', type=int, default=10000)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--eval-every', type=int, default=500)
    args = parser.parse_args()
    if args.output.exists() or min(args.steps, args.batch_size, args.eval_every) < 1:
        raise ValueError('need fresh output directory and positive training settings')
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    gamma = .99 if args.variant == 'td099' else 1.
    mc_weight = .5 if args.variant == 'calibrated1' else 0.
    device = torch.device(args.device)
    data, scaler, manifest = load_data(args.data, device, gamma, small_data_cv=args.small_data_cv)
    bootstrap = bootstrap_indices(data['train'], rng)
    model = Critic(state_only=args.state_only).to(device)
    target = deepcopy(model).eval().requires_grad_(False)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
    args.output.mkdir(parents=True)
    settings = {**vars(args), 'data': str(args.data), 'output': str(args.output),
                'gamma': gamma, 'mc_weight': mc_weight, 'width': 256,
                'feature_source': manifest['feature_source'],
                'bootstrap_seeds': [data['train'][i]['seed'] for i in bootstrap],
                'dataset_manifest_sha256': hashlib.sha256((args.data / 'manifest.json').read_bytes()).hexdigest()}
    (args.output / 'config.json').write_text(json.dumps(settings, indent=2) + '\n')
    started, best = time.monotonic(), float('inf')
    for step in range(1, args.steps + 1):
        model.train()
        selected = rng.choice(bootstrap, args.batch_size, replace=True)
        draws = [(data['train'][i], int(rng.integers(len(data['train'][i]['states'])))) for i in selected]
        batch = {key: torch.stack([episode[key][row] for episode, row in draws])
                 for key in ('states', 'next_states', 'actions', 'chunk_reward', 'steps', 'terminal', 'mc')}
        with torch.no_grad():
            target_q = target.q(batch['states'], batch['actions']).amin(0)
            td = batch['chunk_reward'] + gamma ** batch['steps'] * (~batch['terminal']).float() * model.v(batch['next_states'])
        qloss, _ = calibrated_q_loss(model.q(batch['states'], batch['actions']), td, batch['mc'],
                                    torch.arange(args.batch_size, device=device), mc_weight=mc_weight)
        advantage = target_q - model.v(batch['states'])
        vloss = (torch.where(advantage > 0, .7, .3) * advantage.square()).mean()
        loss = qloss + vloss
        if not torch.isfinite(loss):
            raise FloatingPointError('nonfinite training loss')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 10., error_if_nonfinite=True)
        optimizer.step()
        with torch.no_grad():
            for old, new in zip(target.parameters(), model.parameters(), strict=True):
                old.lerp_(new, .005)
        if step == 1 or step % args.eval_every == 0 or step == args.steps:
            metrics = {'step': step, 'loss': float(loss.detach()),
                       'elapsed_seconds': time.monotonic() - started, **evaluate(model, data['validation'])}
            if not np.isfinite(metrics['episode_equal_mc_mse']):
                raise FloatingPointError('nonfinite validation score')
            with (args.output / 'metrics.jsonl').open('a') as stream:
                stream.write(json.dumps(metrics) + '\n')
            payload = {'model': {key: value.detach().cpu() for key, value in model.state_dict().items()},
                       'settings': settings, 'scaler': {key: torch.from_numpy(value) for key, value in scaler.items()},
                       'validation': metrics}
            temporary = args.output / 'latest.tmp.pt'
            torch.save(payload, temporary)
            temporary.replace(args.output / 'latest.pt')
            if metrics['episode_equal_mc_mse'] < best:
                best = metrics['episode_equal_mc_mse']
                torch.save(payload, args.output / 'best.tmp.pt')
                (args.output / 'best.tmp.pt').replace(args.output / 'best.pt')
            print(json.dumps({key: value for key, value in metrics.items() if key != 'initial'}), flush=True)
    (args.output / 'COMPLETE').touch()


if __name__ == '__main__':
    main()
