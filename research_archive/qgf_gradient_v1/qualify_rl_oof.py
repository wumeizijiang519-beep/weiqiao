"""Independent complete-cohort OOF reconciliation and frozen offline critic gate."""

import argparse
import json
from pathlib import Path
import subprocess

import numpy as np

from corpus_reader import checked_json, sha
from critic_metrics import QUALIFICATION_SEEDS, episode_mse, summarize_critic_diagnostics
from training_data import GroupEpisodeSampler
from train_rl_fold import validate_registration


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
MODELS = ('action', 'state_only', 'permutation', 'mc_action', 'action_permuted')


def offline_gate(statistics):
    values = statistics['per_seed_episode_equal_errors']
    if set(values) != {str(seed) for seed in QUALIFICATION_SEEDS}:
        raise ValueError('All three fixed critic seeds required')
    checks = {}
    for seed in QUALIFICATION_SEEDS:
        row = values[str(seed)]
        checks[str(seed)+'_action_beats_state'] = row['action_mse'] < row['state_only_mse']
        checks[str(seed)+'_action_beats_permutation'] = row['action_mse'] < row['permutation_mse']
        checks[str(seed)+'_action_sensitive'] = row['within_model_permutation_error_increase'] > 0
    for name in ('state_only_minus_action', 'permutation_minus_action', 'action_permuted_minus_action'):
        interval = statistics['paired_group_intervals'][name]['paired_physical_group_percentile95_ci']
        if len(interval) != 2 or not np.isfinite(interval).all() or interval[0] > interval[1]:
            raise ValueError('Invalid preregistered group interval')
        checks[name+'_group_lower_positive'] = interval[0] > 0
    return dict(status='ADMIT_FOR_FIXED_ALL_TRAINING_REFITS' if all(checks.values())
                else 'NO_STABLE_EXECUTION_ALIGNED_ACTION_VALUE_EVIDENCE',
                checks={name: bool(value) for name, value in checks.items()},
                online_efficacy=None, causal_same_state_action_value_proof=False)


def calibration(prediction, target, episode_ids):
    prediction, target, episode_ids = map(np.asarray, (prediction, target, episode_ids))
    counts = {name: np.count_nonzero(episode_ids == name) for name in set(episode_ids)}
    weights = np.asarray([1/counts[name] for name in episode_ids])
    bins = np.minimum((np.clip(prediction, 0, 1)*10).astype(int), 9)
    rows, error = [], 0.
    for number in range(10):
        selected = bins == number
        if not selected.any():
            continue
        weight = weights[selected].sum()
        mean_prediction = float(np.average(prediction[selected], weights=weights[selected]))
        mean_return = float(np.average(target[selected], weights=weights[selected]))
        error += weight/weights.sum()*abs(mean_prediction-mean_return)
        rows.append(dict(bin=number, transitions=int(selected.sum()),
                         predicted_value=mean_prediction, actual_return=mean_return))
    return dict(fixed_ten_bins=rows, episode_equal_absolute_calibration_error=float(error),
                out_of_unit_interval_predictions=int(((prediction < 0)|(prediction > 1)).sum()),
                predictions_clipped_for_mse_or_bin_means=False)


def worker_paths(seed, fold):
    name = f'qgf_rl_oof_seed{seed}_fold{fold}_v1'
    first = (seed, fold) == (202640101, 0)
    return (ROOT/'runs'/name,
            CODE/'FIRST_RL_FIT_REGISTRATION.json' if first else CODE/'rl_oof_remaining_v1_retry1'/(name+'.json'),
            ROOT/'runs/qgf_rl_first_fit_v1_process' if first else ROOT/'runs'/(name+'_extern_process'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    if (CODE/'OOF_QUALIFICATION_RESULT.json').exists():
        raise RuntimeError('Qualification result already frozen; never overwrite or rerun')
    registration = json.loads(args.registration.read_text())
    for name, digest in registration['source_sha256'].items():
        if sha(CODE/name) != digest:
            raise RuntimeError('Independent OOF audit source changed')
    # Never inspect partial outcome metrics or decide on a subset of fits.
    for seed in QUALIFICATION_SEEDS:
        for fold in range(3):
            run, _, process = worker_paths(seed, fold)
            if not (run/'CRITIC_WORKER_COMPLETE').exists() or (process/'process_exit_code').read_text().strip() != '0':
                raise RuntimeError('All nine original fixed fits must finish cleanly first')
    if (CODE/'rl_oof_owned_extern_v1/dispatcher_exit_code').read_text().strip() != '0':
        raise RuntimeError('Owned extern dispatcher nonclean')
    accounting = subprocess.check_output(['sacct', '-j', '1598338.21,1598338.22,1598338.23',
        '-n', '-P', '--format=JobID,State,ExitCode,ElapsedRaw'], text=True)
    expected_cost = {'1598338.21': ('COMPLETED','0:0',743),
                     '1598338.22': ('FAILED','41:0',0), '1598338.23': ('FAILED','1:0',0)}
    seen_steps = set()
    for line in accounting.splitlines():
        fields = line.split('|')
        if fields[0] in expected_cost:
            if fields[0] in seen_steps or (fields[1],fields[2],int(fields[3])) != expected_cost[fields[0]]:
                raise RuntimeError('Original/failed Slurm step accounting changed')
            seen_steps.add(fields[0])
    if seen_steps != set(expected_cost):
        raise RuntimeError('Missing original/failed Slurm cost evidence')
    audit = Path(registration['corpus_report'])
    certificate = checked_json(audit, registration['corpus_report_sha256'])
    if (certificate['status'] != 'FULL_FEATURE_CORPUS_INDEPENDENT_AUDIT_PASS'
            or certificate['dataset_result_sha256'] != registration['dataset_sha256']):
        raise RuntimeError('Independent corpus not qualified for this dataset')
    metadata = checked_json(audit.parent/'CORPUS_METADATA.json', certificate['metadata_sha256'])
    if sha(audit.parent/'CORPUS.npz') != certificate['corpus_sha256']:
        raise RuntimeError('Ground-truth corpus changed')
    with np.load(audit.parent/'CORPUS.npz', allow_pickle=False) as saved:
        actual_returns = saved['mc_return'].copy()
        observations = saved['observation'].copy()
    episodes = {row['episode_id']: row for row in metadata['episodes'] if row['fitting_rows'] > 0}
    all_ids = np.empty(len(actual_returns), dtype='<U10')
    for name, row in episodes.items():
        all_ids[row['transition_indices']] = name
    seeds, evidence, summaries, normalizers = {}, [], {}, {}
    extern_seconds = 0
    for seed in QUALIFICATION_SEEDS:
        seed_rows, seen = [], set()
        calibration_parts = {name: [] for name in (*MODELS, 'fixed_training_prevalence')}
        target_parts, id_parts = [], []
        for fold in range(3):
            run, reg_path, process = worker_paths(seed, fold)
            reg = json.loads(reg_path.read_text())
            validate_registration(reg)
            if (reg['seed'], reg['held_fold']) != (seed, fold):
                raise RuntimeError('Worker registration changed seed/fold')
            for name, digest in reg['source_sha256'].items():
                if sha(CODE/name) != digest:
                    raise RuntimeError('Fitted model dependency changed')
            report = json.loads((run/'REPORT.json').read_text())
            if (report['status'] != 'FIXED_20000_CRITIC_WORKER_COMPLETE_NOT_QUALIFICATION'
                    or report['seed'] != seed or report['held_fold'] != fold
                    or report['updates'] != 20000 or report['registration_sha256'] != sha(reg_path)
                    or report['checkpoint_sha256'] != sha(run/'FINAL_20000.pt')):
                raise RuntimeError('Nonfinal checkpoint/registration evidence')
            split = json.loads((run/'SPLIT.json').read_text())
            held = sorted(name for name, row in episodes.items() if row['fold'] == fold)
            train = sorted(set(episodes)-set(held))
            if split['training_episodes'] != train or split['held_episodes'] != held:
                raise RuntimeError('OOF episode split differs from fixed group fold')
            if ({episodes[name]['physical_group'] for name in train}
                    & {episodes[name]['physical_group'] for name in held}):
                raise RuntimeError('OOF physical-group leakage')
            bootstrap = GroupEpisodeSampler({name: episodes[name] for name in train}, seed)
            if split['bootstrap_groups'] != bootstrap.bootstrap_groups or split['permutation_seed'] != seed+10000+fold:
                raise RuntimeError('Bootstrap/permutation stream changed')
            indices = np.asarray([i for name in held for i in episodes[name]['transition_indices']], dtype=np.int64)
            training_indices = np.asarray([i for name in train for i in episodes[name]['transition_indices']], dtype=np.int64)
            if fold not in normalizers:
                values = observations[training_indices].astype(np.float64)
                normalizers[fold] = (values.mean(0).astype(np.float32),
                                     np.maximum(values.std(0), 1e-5).astype(np.float32))
                del values
            with np.load(run/'NORMALIZER.npz', allow_pickle=False) as scaler:
                for key, expected in zip(('mean', 'scale'), normalizers[fold]):
                    if not np.allclose(scaler[key], expected, atol=1e-7, rtol=1e-6):
                        raise RuntimeError('Normalizer was not fitted on training fold only')
            with np.load(run/'HELD_PREDICTIONS.npz', allow_pickle=False) as saved:
                prediction = {key: saved[key].copy() for key in saved.files}
            expected_keys = set(MODELS)|{'target','episode_id','transition_index','common_td_target','fixed_training_prevalence'}
            if set(prediction) != expected_keys or not np.array_equal(prediction['transition_index'], indices):
                raise RuntimeError('Missing/extra/reordered held-out predictions')
            if (not np.array_equal(prediction['target'], actual_returns[indices])
                    or not np.array_equal(prediction['episode_id'], all_ids[indices])):
                raise RuntimeError('Targets/episode identity not actual shared MC return')
            target = prediction['target']
            if any(prediction[name].shape != target.shape or not np.isfinite(prediction[name]).all()
                   for name in (*MODELS,'common_td_target','fixed_training_prevalence')):
                raise RuntimeError('Invalid held-out prediction/target array')
            baseline = np.mean([actual_returns[episodes[name]['transition_indices']].mean() for name in train])
            if not np.allclose(prediction['fixed_training_prevalence'], baseline, atol=1e-7, rtol=1e-6):
                raise RuntimeError('Prevalence reference used nontraining labels')
            errors = {name: episode_mse(prediction[name], target, prediction['episode_id']) for name in MODELS}
            td_errors = {name: episode_mse(prediction[name], prediction['common_td_target'], prediction['episode_id']) for name in MODELS}
            stored = {row['episode_id']: row for row in report['episode_errors']}
            if set(stored) != set(held) or len(stored) != len(report['episode_errors']):
                raise RuntimeError('Stored held episode error inventory differs')
            for name in held:
                row = dict(episode_id=name, physical_group=episodes[name]['physical_group'],
                           **{key+'_mse': table[name] for key, table in errors.items()},
                           **{key+'_shared_td_mse': table[name] for key, table in td_errors.items()})
                if stored[name]['physical_group'] != row['physical_group'] or any(
                        not np.isclose(stored[name][key], value, atol=1e-12, rtol=1e-12)
                        for key, value in row.items() if key.endswith('_mse')):
                    raise RuntimeError('Independent episode errors disagree with worker report')
                if name in seen:
                    raise RuntimeError('Duplicate held episode across folds')
                seen.add(name)
                seed_rows.append(row)
            for name in calibration_parts:
                calibration_parts[name].append(prediction[name])
            target_parts.append(target)
            id_parts.append(prediction['episode_id'])
            if (seed,fold) != (202640101,0):
                if '/job_1598338/step_extern' not in (process/'cgroup.txt').read_text():
                    raise RuntimeError('Owned allocation evidence missing')
                extern_seconds += int((process/'charged_gpu_seconds').read_text())
            evidence.append(dict(seed=seed, fold=fold, report_sha256=sha(run/'REPORT.json'),
                                 checkpoint_sha256=report['checkpoint_sha256'],
                                 predictions_sha256=sha(run/'HELD_PREDICTIONS.npz'),
                                 split_sha256=sha(run/'SPLIT.json'), normalizer_sha256=sha(run/'NORMALIZER.npz')))
        if seen != set(episodes):
            raise RuntimeError('Seed does not cover all measured fitting episodes')
        seeds[seed] = seed_rows
        targets, ids = np.concatenate(target_parts), np.concatenate(id_parts)
        summaries[str(seed)] = {name: calibration(np.concatenate(parts), targets, ids)
                                for name, parts in calibration_parts.items()}
    statistics = summarize_critic_diagnostics(seeds, bootstrap_seed=202640901, draws=10000)
    result = {**offline_gate(statistics), 'statistics': statistics, 'calibration': summaries,
              'all_episode_errors': {str(seed): rows for seed, rows in seeds.items()}, 'evidence': evidence,
              'registration_sha256': sha(args.registration), 'source_sha256': sha(Path(__file__)),
              'scientific_episodes': 288, 'fitting_episodes': len(episodes),
              'measured_extern_gpu_seconds': extern_seconds,
              'completed_gpu_seconds_through_oof': 38979+extern_seconds,
              'feature_critic_phase_gpu_seconds_through_oof': 4269+extern_seconds,
              'scope': 'Necessary offline action-value screen only; no online efficacy or causal proof.'}
    if result['feature_critic_phase_gpu_seconds_through_oof'] > .8*8*3600:
        result.update(status='STOP_PHASE_BUDGET_EXCEEDED', budget_reserve_ok=False)
    destination = CODE/'OOF_QUALIFICATION_RESULT.json'
    with destination.open('x') as stream:
        json.dump(result, stream, indent=2)
    (CODE/'OOF_QUALIFICATION_RESULT_SHA256.txt').write_text(sha(destination)+'\n')
    print(json.dumps({key: result[key] for key in ('status','checks','completed_gpu_seconds_through_oof')}, indent=2))


if __name__ == '__main__':
    main()
