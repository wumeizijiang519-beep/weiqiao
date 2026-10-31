"""Registered final-step IQL/control worker; never read validation or formal data."""

import argparse
import json
from pathlib import Path
import random
import time
import traceback

import numpy as np

SEEDS = (202640101, 202640102, 202640103)
SOURCES = ('train_rl_fold.py', 'critic.py', 'matched_iql.py', 'core.py', 'features.py',
           'training_data.py', 'rl_corpus.py', 'rl_batches.py', 'critic_metrics.py', 'corpus_reader.py')


def validate_registration(reg):
    if (reg['seed'] not in SEEDS or reg['held_fold'] not in (0, 1, 2, 'full')
            or reg['updates'] != 20000 or reg['batch_size'] != 128
            or reg['learning_rate'] != 3e-4 or reg['gamma'] != 1.
            or reg['expectile'] != .7 or reg['target_ema'] != .005 or reg['width'] != 256):
        raise ValueError('Frozen RL parameters/seed/fold changed')
    if set(reg['source_sha256']) != set(SOURCES):
        raise ValueError('Incomplete training dependency registration')
    if not 1 <= reg['hard_gpu_seconds'] <= 1200:
        raise ValueError('Worker hard time exceeds registered1200seconds')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    reg = json.loads(args.registration.read_text())
    validate_registration(reg)
    from corpus_reader import checked_json, sha
    code = Path(__file__).parent
    for name, digest in reg['source_sha256'].items():
        if sha(code / name) != digest:
            raise RuntimeError('Frozen training dependency changed: ' + name)
    report = checked_json(reg['corpus_report'], reg['corpus_report_sha256'])
    folder = Path(reg['corpus_report']).parent
    if (report['status'] != 'FULL_FEATURE_CORPUS_INDEPENDENT_AUDIT_PASS'
            or report['dataset_result_sha256'] != reg['dataset_sha256']
            or not (folder / 'FEATURE_CORPUS_AUDIT_PASS').exists()):
        raise RuntimeError('Real full corpus qualification missing')
    if sha(folder / 'CORPUS.npz') != report['corpus_sha256']:
        raise RuntimeError('Certified fitting arrays changed')
    metadata = checked_json(folder / 'CORPUS_METADATA.json', report['metadata_sha256'])
    if metadata['scientific_episodes'] != 288:
        raise RuntimeError('Scientific denominator changed')
    run = Path(reg['run_directory'])
    run.mkdir()
    started = time.monotonic()
    try:
        import torch
        from critic import TwinQValue
        from critic_metrics import episode_mse
        from features import FoldScaler
        from matched_iql import MatchedIQL
        from rl_batches import ARRAY_KEYS, TrainingFold, training_batch, training_fold
        from training_data import GroupEpisodeSampler, permutation_indices

        torch.set_num_threads(4)
        random.seed(reg['seed'])
        np.random.seed(reg['seed'])
        torch.manual_seed(reg['seed'])
        torch.cuda.manual_seed_all(reg['seed'])
        torch.backends.cuda.matmul.allow_tf32 = False
        with np.load(folder / 'CORPUS.npz', allow_pickle=False) as saved:
            if set(saved.files) != set(ARRAY_KEYS):
                raise RuntimeError('Fitting array inventory changed')
            corpus = {key: saved[key].copy() for key in ARRAY_KEYS}
        corpus['episodes'] = {row['episode_id']: row for row in metadata['episodes'] if row['fitting_rows'] > 0}
        if len(corpus['episodes']) != metadata['nonempty_fitting_episodes']:
            raise RuntimeError('Missing/duplicate nonempty fitting episode')
        if reg['held_fold'] == 'full':
            train_indices = np.arange(len(corpus['action']))
            fold = TrainingFold(-1, train_indices, np.array([], dtype=np.int64), corpus['episodes'],
                                FoldScaler().fit(corpus['observation']))
        else:
            fold = training_fold(corpus, reg['held_fold'])
        sampler = GroupEpisodeSampler(fold.training_episodes, reg['seed'])
        permutation_seed = reg['seed'] + 10000 + (0 if reg['held_fold'] == 'full' else reg['held_fold'])
        permutation = permutation_indices(len(corpus['action']), permutation_seed)
        model = TwinQValue(metadata['feature_dimension'], width=256).to('cuda')
        learner = MatchedIQL(model, learning_rate=3e-4, expectile=.7, tau=.005, gamma=1.)
        np.savez_compressed(run / 'NORMALIZER.npz', **fold.scaler.state())
        split = dict(seed=reg['seed'], held_fold=reg['held_fold'], updates=20000,
            training_episodes=sorted(fold.training_episodes),
            held_episodes=sorted(set(corpus['episodes'])-set(fold.training_episodes)),
            bootstrap_groups=sampler.bootstrap_groups, permutation_seed=permutation_seed,
            scientific_episodes=288, nonempty_fitting_episodes=len(corpus['episodes']))
        (run / 'SPLIT.json').write_text(json.dumps(split, indent=2))
        timings = []
        for update in range(1, 20001):
            if time.monotonic() - started >= reg['hard_gpu_seconds']:
                raise RuntimeError('Registered critic time budget exhausted, not performance stopping')
            torch.cuda.synchronize()
            tick = time.monotonic()
            indices, weights = sampler.sample(128)
            batch = training_batch(corpus, fold, indices, weights, permutation, device='cuda')
            losses = learner.update(batch)
            torch.cuda.synchronize()
            timings.append(time.monotonic() - tick)
            if update == 200:
                p90 = float(np.quantile(timings[50:], .9))
                predicted_each = (time.monotonic()-started) + (20000-200)*p90 + 30
                budget = reg['phase_gpu_seconds_before_qualification'] + 12*predicted_each
                forecast = dict(update=200, step_p90_seconds=p90, predicted_each_gpu_seconds=predicted_each,
                                conservative12fit_phase_forecast_seconds=budget,
                                cost_gate_pass=budget <= .8*8*3600,
                                performance_metrics_used_for_stopping=False)
                (run / 'COST_FORECAST.json').write_text(json.dumps(forecast, indent=2))
                if not forecast['cost_gate_pass']:
                    raise RuntimeError('Measured critic cost exceeds phase reserve; no loss-based stopping')
                (run / 'COST_GATE_PASS').touch()
            if update % 1000 == 0:
                print('fixed_update', update, 'elapsed', time.monotonic()-started, flush=True)
        torch.save(dict(models={name: value.state_dict() for name, value in learner.models.items()},
                        targets={name: value.state_dict() for name, value in learner.targets.items()},
                        updates=20000, registration_sha256=sha(args.registration)), run / 'FINAL_20000.pt')
        held = fold.held_indices
        episode_errors = []
        if len(held):
            predictions = {name: [] for name in (*learner.models, 'action_permuted')}
            held_td = []
            with torch.no_grad():
                for first in range(0, len(held), 256):
                    index = held[first:first+256]
                    obs = torch.as_tensor(fold.scaler.transform(corpus['observation'][index]), device='cuda')
                    action = torch.as_tensor(corpus['action'][index], device='cuda')
                    shuffled = torch.as_tensor(corpus['bank'][index, permutation[index]], device='cuda')
                    mask = torch.as_tensor(corpus['mask'][index], device='cuda')
                    from core import semimdp_target
                    next_obs = torch.as_tensor(fold.scaler.transform(corpus['next_observation'][index]), device='cuda')
                    common_td = semimdp_target(
                        torch.as_tensor(corpus['rewards'][index], device='cuda'),
                        torch.as_tensor(corpus['executed_steps'][index], device='cuda'),
                        torch.as_tensor(corpus['terminal'][index], device='cuda'),
                        learner.targets['action'].value(next_obs).squeeze(-1), 1.)
                    held_td.append(common_td.cpu().numpy())
                    for name, value in learner.models.items():
                        supplied = torch.zeros_like(action) if name == 'state_only' else shuffled if name == 'permutation' else action
                        predictions[name].append(value.conservative_q(obs, supplied, mask).cpu().numpy())
                    predictions['action_permuted'].append(learner.models['action'].conservative_q(obs, shuffled, mask).cpu().numpy())
            predictions = {name: np.concatenate(values) for name, values in predictions.items()}
            common_td = np.concatenate(held_td)
            ids = np.empty(len(corpus['action']), dtype='<U10')
            for name, row in corpus['episodes'].items():
                ids[row['transition_indices']] = name
            target = corpus['mc_return'][held]
            errors = {name: episode_mse(value, target, ids[held]) for name, value in predictions.items()}
            td_errors = {name: episode_mse(value, common_td, ids[held]) for name, value in predictions.items()}
            for name in sorted(set(ids[held])):
                episode_errors.append(dict(episode_id=name,
                    physical_group=corpus['episodes'][name]['physical_group'],
                    **{key+'_mse': values[name] for key, values in errors.items()},
                    **{key+'_shared_td_mse': values[name] for key, values in td_errors.items()}))
            baseline = np.mean([corpus['mc_return'][row['transition_indices']].mean()
                                for row in fold.training_episodes.values()])
            np.savez_compressed(run / 'HELD_PREDICTIONS.npz', **predictions, target=target,
                                episode_id=ids[held], transition_index=held,
                                common_td_target=common_td,
                                fixed_training_prevalence=np.full(len(held), baseline, dtype=np.float32))
        result = dict(status='FIXED_20000_CRITIC_WORKER_COMPLETE_NOT_QUALIFICATION', seed=reg['seed'],
            held_fold=reg['held_fold'], updates=20000, registration_sha256=sha(args.registration),
            checkpoint_sha256=sha(run / 'FINAL_20000.pt'), episode_errors=episode_errors,
            wall_seconds=time.monotonic()-started, peak_cuda_bytes=torch.cuda.max_memory_allocated(),
            qualification_decision=None, online_efficacy=None)
        (run / 'REPORT.json').write_text(json.dumps(result, indent=2))
        (run / 'CRITIC_WORKER_COMPLETE').touch()
    except BaseException:
        (run / 'FAILED.txt').write_text(traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
