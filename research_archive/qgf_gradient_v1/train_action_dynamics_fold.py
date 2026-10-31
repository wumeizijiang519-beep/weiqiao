"""Frozen action-conditioned feature-dynamics auxiliary worker."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np


SEEDS = (202641201, 202641202, 202641203)
UPDATES = 5000
BATCH_SIZE = 256


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def signed_projection(rows, columns, seed):
    rng = np.random.default_rng(seed)
    return rng.choice(np.array([-1., 1.], dtype=np.float32), size=(rows, columns)) / np.sqrt(rows)


def episode_equal(values, episode_ids):
    return float(np.mean([values[episode_ids == name].mean() for name in np.unique(episode_ids)]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    if (reg['seed'] not in SEEDS or reg['held_fold'] not in (0, 1, 2)
            or reg['updates'] != UPDATES or reg['batch_size'] != BATCH_SIZE
            or reg['hard_gpu_seconds'] != 900):
        raise ValueError('Frozen auxiliary parameters changed')
    code = Path(__file__).parent
    if sha(code / 'train_action_dynamics_fold.py') != reg['worker_sha256']:
        raise RuntimeError('Worker source changed')
    if sha(reg['corpus']) != reg['corpus_sha256'] or sha(reg['metadata']) != reg['metadata_sha256']:
        raise RuntimeError('Audited corpus or metadata changed')
    run = Path(reg['run_directory'])
    run.mkdir()
    started = time.monotonic()
    try:
        import torch
        from torch import nn

        torch.set_num_threads(4)
        random.seed(reg['seed'])
        np.random.seed(reg['seed'])
        torch.manual_seed(reg['seed'])
        torch.cuda.manual_seed_all(reg['seed'])
        torch.backends.cuda.matmul.allow_tf32 = False

        metadata = json.loads(Path(reg['metadata']).read_text())
        with np.load(reg['corpus'], allow_pickle=False) as saved:
            corpus = {key: saved[key].copy() for key in saved.files}
        count, feature_dim = corpus['observation'].shape
        episode_ids = np.empty(count, dtype='<U10')
        folds = np.empty(count, dtype=np.int8)
        groups = np.empty(count, dtype='<U64')
        for row in metadata['episodes']:
            index = np.asarray(row['transition_indices'], dtype=np.int64)
            episode_ids[index] = row['episode_id']
            folds[index] = row['fold']
            groups[index] = row['physical_group']
        if not np.all(episode_ids != ''):
            raise RuntimeError('Transition-to-episode coverage changed')
        train = np.flatnonzero(folds != reg['held_fold'])
        held = np.flatnonzero(folds == reg['held_fold'])
        if not len(train) or not len(held) or set(groups[train]) & set(groups[held]):
            raise RuntimeError('Physical-group split invalid')

        obs_mean = corpus['observation'][train].mean(0, dtype=np.float64).astype(np.float32)
        obs_scale = np.maximum(corpus['observation'][train].std(0, dtype=np.float64), 1e-5).astype(np.float32)
        delta = corpus['next_observation'] - corpus['observation']
        delta_mean = delta[train].mean(0, dtype=np.float64).astype(np.float32)
        delta_scale = np.maximum(delta[train].std(0, dtype=np.float64), 1e-5).astype(np.float32)
        state_projection = signed_projection(feature_dim, 256, reg['seed'] + 11)
        target_projection = signed_projection(feature_dim, 128, reg['seed'] + 29)

        def project(values, mean, scale, projection):
            output = []
            for first in range(0, len(values), 512):
                batch = torch.as_tensor((values[first:first + 512] - mean) / scale, device='cuda')
                matrix = torch.as_tensor(projection, device='cuda')
                output.append((batch @ matrix).cpu())
            return torch.cat(output)

        state = project(corpus['observation'], obs_mean, obs_scale, state_projection)
        target = project(delta, delta_mean, delta_scale, target_projection)
        true_action = np.nan_to_num(corpus['action'].reshape(count, -1), nan=0.).astype(np.float32)
        alternate_index = (corpus['selected_index'] + 1 + reg['seed'] % 3) % 4
        alternate = corpus['bank'][np.arange(count), alternate_index]
        alternate = np.nan_to_num(alternate.reshape(count, -1), nan=0.).astype(np.float32)
        mask = corpus['mask'].astype(np.float32)
        known = np.concatenate((mask, (corpus['planned_steps'] / 10.).reshape(-1, 1)), axis=1).astype(np.float32)
        true_input = torch.from_numpy(np.concatenate((true_action, known), axis=1))
        alt_input = torch.from_numpy(np.concatenate((alternate, known), axis=1))
        zero_input = torch.zeros_like(true_input)

        class Predictor(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(nn.Linear(337, 256), nn.SiLU(), nn.Linear(256, 256),
                                         nn.SiLU(), nn.Linear(256, 128))

            def forward(self, state_value, action_value):
                return self.net(torch.cat((state_value, action_value), dim=-1))

        models = {name: Predictor().cuda() for name in ('action', 'state_only', 'within_bank')}
        optimizers = {name: torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-4)
                      for name, model in models.items()}
        generator = np.random.default_rng(reg['seed'] + 101)
        train_state, train_target = state[train], target[train]
        inputs = {'action': true_input[train], 'state_only': zero_input[train],
                  'within_bank': alt_input[train]}
        for update in range(1, UPDATES + 1):
            if time.monotonic() - started >= reg['hard_gpu_seconds']:
                raise RuntimeError('Registered auxiliary time budget exhausted')
            index = torch.from_numpy(generator.integers(0, len(train), BATCH_SIZE, dtype=np.int64))
            s = train_state[index].cuda(non_blocking=True)
            y = train_target[index].cuda(non_blocking=True)
            for name, model in models.items():
                prediction = model(s, inputs[name][index].cuda(non_blocking=True))
                loss = (prediction - y).square().mean()
                optimizers[name].zero_grad(set_to_none=True)
                loss.backward()
                optimizers[name].step()
            if update % 1000 == 0:
                print('fixed_update', update, 'elapsed', time.monotonic() - started, flush=True)

        held_state, held_target = state[held].cuda(), target[held].cuda()
        predictions = {}
        with torch.no_grad():
            for name, supplied in (('action', true_input), ('state_only', zero_input),
                                   ('within_bank', alt_input)):
                predictions[name] = models[name](held_state, supplied[held].cuda()).cpu().numpy()
            predictions['action_with_alternate'] = models['action'](
                held_state, alt_input[held].cuda()).cpu().numpy()
        truth = held_target.cpu().numpy()
        row_mse = {name: np.mean((value - truth) ** 2, axis=1) for name, value in predictions.items()}
        episode_metrics = []
        for episode in sorted(np.unique(episode_ids[held])):
            take = episode_ids[held] == episode
            episode_metrics.append(dict(episode_id=episode, physical_group=str(groups[held][take][0]),
                **{name + '_mse': float(value[take].mean()) for name, value in row_mse.items()}))
        np.savez_compressed(run / 'NORMALIZER_AND_PROJECTIONS.npz', obs_mean=obs_mean,
            obs_scale=obs_scale, delta_mean=delta_mean, delta_scale=delta_scale,
            state_projection=state_projection, target_projection=target_projection)
        torch.save({name: model.state_dict() for name, model in models.items()}, run / 'FINAL_5000.pt')
        result = dict(status='ACTION_DYNAMICS_AUX_WORKER_COMPLETE_NOT_QUALIFICATION',
            seed=reg['seed'], held_fold=reg['held_fold'], updates=UPDATES,
            training_rows=int(len(train)), held_rows=int(len(held)), held_episodes=len(episode_metrics),
            episode_equal_mse={name: episode_equal(value, episode_ids[held]) for name, value in row_mse.items()},
            episode_metrics=episode_metrics, wall_seconds=time.monotonic() - started,
            peak_cuda_bytes=torch.cuda.max_memory_allocated(), online_efficacy=None,
            causal_signal_v2_read=False)
        (run / 'REPORT.json').write_text(json.dumps(result, indent=2))
        (run / 'WORKER_COMPLETE').touch()
    except BaseException:
        run.mkdir(exist_ok=True)
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()

