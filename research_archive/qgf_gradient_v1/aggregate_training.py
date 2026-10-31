"""Freeze the complete fixed cohort's data qualification, without fitting a Q."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

from wam_runtime import MANIFEST_SHA, ROOT, file_sha


def qualification(rows):
    successes = [row for row in rows if row['success']]
    failures = [row for row in rows if not row['success']]
    class_groups = {name: {row['physical_input_group'] for row in values}
                    for name, values in [('success', successes), ('failure', failures)]}
    folds = {str(fold): {'success': sum(row['success'] for row in rows if row['group_oof_fold'] == fold),
                         'failure': sum(not row['success'] for row in rows if row['group_oof_fold'] == fold)}
             for fold in range(3)}
    checks = {'at_least12_successes': len(successes) >= 12,
              'at_least12_failures': len(failures) >= 12,
              'at_least8_success_groups': len(class_groups['success']) >= 8,
              'at_least8_failure_groups': len(class_groups['failure']) >= 8,
              'every_group_oof_fold_has_both_classes': all(v['success'] > 0 and v['failure'] > 0
                                                          for v in folds.values())}
    return {'status': 'ADMIT_FOR_RL_QUALIFICATION' if all(checks.values())
            else 'DATA_INSUFFICIENT_FOR_VALUE_IDENTIFICATION',
            'checks': checks, 'successes': len(successes), 'failures': len(failures),
            'physical_groups_per_class': {key: len(value) for key, value in class_groups.items()},
            'group_oof_fold_counts': folds}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, default=ROOT / 'qgf_gradient_v1/training288_v1')
    args = parser.parse_args()
    destination = args.plan / 'DATASET_RESULT.json'
    if destination.exists():
        raise RuntimeError('Dataset result already frozen; never overwrite')
    if not (args.plan / 'ALL_SHARDS_AUDITED').exists():
        raise RuntimeError('All fixed shards must finish first')
    if (args.plan / 'dispatcher_exit_code').read_text().strip() != '0':
        raise RuntimeError('Dispatcher did not exit cleanly')
    registration = json.loads((args.plan / 'REGISTRATION.json').read_text())
    failed_attempts = list((ROOT / 'runs').glob('qgf_gradient_training288_v1_shard*/PROCESS_FAILED'))
    if failed_attempts:
        raise RuntimeError('Failed attempts require explicit accounting before aggregation: '
                           + ','.join(str(path.parent) for path in failed_attempts))
    manifest_path = ROOT / 'qgf_gradient_v1/evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Manifest changed')
    manifest = json.loads(manifest_path.read_text())
    expected = {row['episode_id']: row for row in manifest['partitions']['train']}
    runs = [ROOT / 'runs/qgf_gradient_collector_integrity_v1']
    runs += [Path(row['run_directory']) for row in registration['shards']]
    rows, evidence, step_ids = [], [], []
    for run in runs:
        for flag in ['PROCESS_COMPLETE', 'COLLECTION_COMPLETE', 'COLLECTOR_AUDIT_PASS']:
            if not (run / flag).exists():
                raise RuntimeError('Incomplete run: ' + str(run))
        if (run / 'process_exit_code').read_text().strip() != '0':
            raise RuntimeError('Failed process: ' + str(run))
        run_registration = json.loads((run / 'registration.json').read_text())
        audit_path = run / 'INDEPENDENT_AUDIT.json'
        audit = json.loads(audit_path.read_text())
        report_path = run / 'report.json'
        if file_sha(report_path) != audit['collection_report_sha256']:
            raise RuntimeError('Changed audited report')
        if {row['episode_id'] for row in audit['episodes']} != set(run_registration['episode_ids']):
            raise RuntimeError('Run entries differ from its registration')
        for row in audit['episodes']:
            entry = expected[row['episode_id']]
            if not row['audit_pass'] or row['physical_input_group'] != entry['physical_input_group']:
                raise RuntimeError('Episode/group was not independently audited')
            summary_path = run / row['episode_id'] / 'summary.json'
            summary = json.loads(summary_path.read_text())
            if (summary['success'] != row['success'] or summary['task_id'] != entry['task_id']
                    or summary['environment_seed'] != entry['environment_seed']
                    or summary['selection_seed'] != entry['selection_seed']
                    or summary['initial_state_index'] != entry['initial_state_index']):
                raise RuntimeError('Scene/label differs from frozen entry')
            rows.append({**row, 'group_oof_fold': entry['group_oof_fold'],
                         'family': entry['family'], 'category': entry['category'],
                         'episode_directory': str(run / row['episode_id']),
                         'summary_sha256': file_sha(summary_path)})
        evidence.append({'run': str(run), 'audit_sha256': file_sha(audit_path),
                         'report_sha256': file_sha(report_path),
                         'registration_sha256': file_sha(run / 'registration.json')})
        allocation = (run / 'allocation.txt').read_text()
        match = re.search(r'job=(\d+) step=(\d+)', allocation)
        if not match:
            raise RuntimeError('Missing exact allocation: ' + str(run))
        step_ids.append(match.group(1) + '.' + match.group(2))
    if len(rows) != 288 or len({row['episode_id'] for row in rows}) != 288:
        raise RuntimeError('Cohort contains missing or duplicated episodes')
    if {row['episode_id'] for row in rows} != set(expected):
        raise RuntimeError('Collected cohort is not the fixed training population')
    for fold in range(3):
        train_groups = {row['physical_input_group'] for row in rows if row['group_oof_fold'] != fold}
        held_groups = {row['physical_input_group'] for row in rows if row['group_oof_fold'] == fold}
        if train_groups & held_groups:
            raise RuntimeError('OOF physical group leakage')
    accounting = subprocess.check_output(
        ['sacct', '-j', ','.join(step_ids), '--format=JobID,State,ExitCode,ElapsedRaw,AllocTRES', '-P', '-n'],
        text=True)
    costs = []
    for line in accounting.splitlines():
        fields = line.split('|')
        if len(fields) >= 5 and fields[0] in step_ids:
            if fields[1] != 'COMPLETED' or fields[2] != '0:0':
                raise RuntimeError('Nonclean Slurm step in admitted cohort')
            if not re.search(r'(^|,)gres/gpu=1(,|$)', fields[4]):
                raise RuntimeError('Unexpected GPU allocation')
            costs.append({'step': fields[0], 'seconds': int(fields[3]), 'gpu_count': 1})
    if {row['step'] for row in costs} != set(step_ids):
        raise RuntimeError('Slurm accounting incomplete')
    result = {**qualification(rows), 'entries': rows, 'evidence': evidence,
              'manifest_sha256': MANIFEST_SHA, 'registration_sha256': file_sha(args.plan / 'REGISTRATION.json'),
              'episodes': len(rows), 'replans': sum(row['replans'] for row in rows),
              'physical_groups': len({row['physical_input_group'] for row in rows}),
              'category_counts': dict(Counter(row['category'] for row in rows)),
              'family_counts': dict(Counter(row['family'] for row in rows)),
              'successful_gpu_steps': costs,
              'collection_gpu_hours': sum(row['seconds'] for row in costs) / 3600,
              'failed_training_attempts': [],
              'scope': 'Data qualification only; not critic quality or online efficacy.'}
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.plan / 'DATASET_RESULT_SHA256.txt').write_text(file_sha(destination) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ['entries', 'evidence']}, indent=2))


if __name__ == '__main__':
    main()
