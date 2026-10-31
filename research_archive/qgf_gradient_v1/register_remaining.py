"""Admit fixed remaining training scenes using audited integrity and cost only."""

import json

from wam_runtime import MANIFEST_SHA, ROOT, file_sha


def main():
    code = ROOT / 'qgf_gradient_v1'
    integrity = ROOT / 'runs/qgf_gradient_collector_integrity_v1'
    manifest_path = code / 'evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Frozen manifest changed')
    for flag in ['COLLECTOR_AUDIT_PASS', 'COLLECTION_COMPLETE', 'PROCESS_COMPLETE']:
        if not (integrity / flag).exists():
            raise RuntimeError('Integrity not admitted: ' + flag)
    if (integrity / 'process_exit_code').read_text().strip() != '0':
        raise RuntimeError('Integrity process did not exit cleanly')
    audit_path = integrity / 'INDEPENDENT_AUDIT.json'
    audit = json.loads(audit_path.read_text())
    report = json.loads((integrity / 'report.json').read_text())
    original = json.loads((integrity / 'registration.json').read_text())
    if audit['status'] != 'COLLECTOR_INTEGRITY_PASS' or len(audit['episodes']) != 4:
        raise RuntimeError('Missing four independent episode audits')
    completed = {row['episode_id'] for row in audit['episodes'] if row['audit_pass']}
    if completed != set(original['episode_ids']):
        raise RuntimeError('Not all integrity entries passed')
    manifest = json.loads(manifest_path.read_text())
    remaining = [row['episode_id'] for row in manifest['partitions']['train']
                 if row['episode_id'] not in completed]
    if len(remaining) != 284 or len(set(remaining) | completed) != 288:
        raise RuntimeError('Incomplete/duplicate fixed cohort')
    source_names = list(original['source_sha256'])
    for name, expected in original['source_sha256'].items():
        if file_sha(code / name) != expected:
            raise RuntimeError('Registered collector code changed: ' + name)
    p90 = float(audit['p90_episode_seconds'])
    overhead = max(0., report['wall_seconds'] - sum(row['wall_seconds'] for row in report['episodes']))
    # Measured Slurm elapsed819s includes the first audit; keep that actual cost.
    spent_seconds = 819
    model_step_cap = 16500
    shard_count = 4
    forecast_seconds = spent_seconds + len(remaining) * p90 + shard_count * (overhead + 60)
    hard_gpu_seconds = spent_seconds + shard_count * model_step_cap
    usable_seconds = 24 * 3600 * .8
    if forecast_seconds > usable_seconds or hard_gpu_seconds > usable_seconds:
        raise RuntimeError('Fixed cohort exceeds the budget with20percent reserve')
    destination = code / 'training288_v1'
    if destination.exists():
        raise RuntimeError('Never overwrite a training registration')
    destination.mkdir()
    source_names = [name for name in source_names if name != 'run_collector.sh']
    source_names += ['run_training_shard.sh', 'dispatch_training.sh', 'TRAINING288_V1.md']
    common = {
        'version': 'qgf_gradient_training288_v1_20261026',
        'manifest_sha256': MANIFEST_SHA, 'partition': 'train',
        'source_sha256': {name: file_sha(code / name) for name in source_names},
        'model_step_cap_seconds': model_step_cap,
        'cpu_audit_after_gpu_release': True,
        'no_automatic_retry': True,
        'settings': original['settings'],
    }
    registrations = []
    for index in range(shard_count):
        ids = remaining[index * 71:(index + 1) * 71]
        row = {**common, 'shard': index, 'episode_ids': ids,
               'run_directory': str(ROOT / f'runs/qgf_gradient_training288_v1_shard{index}'),
               'preceding_completed_integrity_ids': sorted(completed)}
        path = destination / f'shard{index}.json'
        path.write_text(json.dumps(row, indent=2, sort_keys=True))
        registrations.append({'path': str(path), 'sha256': file_sha(path),
                              'run_directory': row['run_directory'], 'episodes': len(ids)})
    result = {
        'status': 'FIXED_REMAINING284_ADMITTED_FOR_COLLECTION',
        'cohort_size': 288, 'completed_integrity_ids': sorted(completed),
        'integrity_audit_sha256': file_sha(audit_path),
        'manifest_sha256': MANIFEST_SHA, 'shards': registrations,
        'budget': {'collection_cap_gpu_hours': 24, 'reserve_fraction': .2,
                   'already_spent_gpu_seconds': spent_seconds,
                   'measured_p90_episode_seconds': p90, 'measured_load_overhead_seconds': overhead,
                   'forecast_gpu_hours': forecast_seconds / 3600,
                   'hard_gpu_hours_including_integrity': hard_gpu_seconds / 3600,
                   'cpu_audit_gpu_hours': 0,
                   'cpu_audit_cap_minutes_per_shard': 30,
                   'note': 'CPU-only file audit follows GPU step release; no scientific/model changes.'},
        'qualification_after_all288': {'successes_at_least': 12, 'failures_at_least': 12,
                                        'physical_groups_per_class_at_least': 8,
                                        'every_group_oof_fold_both_classes': True},
    }
    (destination / 'REGISTRATION.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
