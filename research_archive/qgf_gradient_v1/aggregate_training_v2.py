"""Reconcile preserved/recovered/fresh cohort evidence without erasing failures."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

import numpy as np

from aggregate_training import qualification
from data_contract import OBS_KEYS, observation_hash
from wam_runtime import MANIFEST_SHA, ROOT, file_sha


PRESERVATION_SHA = '7c45722ff35004976276f01a7fa79ebd34c5e742617269c18d4188869c06bb89'
PLAN_SHA = '9a3cacec0af53238345a2ede162b05dd9d738042e234ec3ffdb986fd34471c87'
COLLECTION_STEPS = {314: ('COMPLETED', 819), 316: ('FAILED', 2825),
                    317: ('COMPLETED', 468), 319: ('FAILED', 67),
                    320: ('FAILED', 92), 321: ('COMPLETED', 29),
                    322: ('COMPLETED', 50), 323: ('COMPLETED', 491)}
INTEGRATION_STEPS = {307: ('FAILED', 225), 309: ('FAILED', 402), 310: ('COMPLETED', 431)}


def reconcile_entries(rows, expected):
    ids = [row['episode_id'] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError('Duplicate cohort entries; prefix cannot count twice')
    if set(ids) != set(expected) or len(ids) != 288:
        raise RuntimeError('Fixed cohort incomplete or replaced')
    for row in rows:
        entry = expected[row['episode_id']]
        if (row['physical_input_group'] != entry['physical_input_group']
                or row['group_oof_fold'] != entry['group_oof_fold']):
            raise RuntimeError('Frozen group/fold metadata changed')
    for fold in range(3):
        train = {row['physical_input_group'] for row in rows if row['group_oof_fold'] != fold}
        held = {row['physical_input_group'] for row in rows if row['group_oof_fold'] == fold}
        if train & held:
            raise RuntimeError('OOF physical-group leakage')


def verify_episode(folder, entry, certificate):
    if not (folder / 'EPISODE_COMPLETE').exists():
        raise RuntimeError('Episode not complete: ' + str(folder))
    if json.loads((folder / 'config.json').read_text()) != entry:
        raise RuntimeError('Frozen scene configuration changed')
    summary_path = folder / 'summary.json'
    summary = json.loads(summary_path.read_text())
    for key in ('episode_id', 'physical_input_group', 'task_id', 'environment_seed',
                'selection_seed', 'initial_state_index'):
        if summary[key] != entry[key]:
            raise RuntimeError('Summary metadata changed: ' + key)
    if not certificate['audit_pass']:
        raise RuntimeError('Missing independent episode certificate')
    for key in ('success', 'replans', 'model_steps', 'selected_counts', 'video_frames'):
        if summary[key] != certificate[key]:
            raise RuntimeError('Summary differs from independent certificate: ' + key)
    if file_sha(folder / 'rollout.mp4') != summary['video_sha256']:
        raise RuntimeError('Audited video changed')
    records = summary['transitions']
    if len(records) != summary['replans']:
        raise RuntimeError('Missing transition records')
    paths = sorted(folder.glob('transition_*/transition.npz'))
    if len(paths) != len(records) or len(list(folder.glob('observation_*.npz'))) != len(paths) + 1:
        raise RuntimeError('Missing or extra transition/observation')
    for index, (path, record) in enumerate(zip(paths, records)):
        if path.parent.name != f'transition_{index:04d}' or file_sha(path) != record['transition_sha256']:
            raise RuntimeError('Archived audited transition changed')
        # Feature extraction consumes observation files, so verify their equality
        # to the already audited transition arrays, not just filenames.
        with np.load(path, allow_pickle=False) as data:
            for prefix, number in (('current', index), ('next', index + 1)):
                with np.load(folder / f'observation_{number:04d}.npz', allow_pickle=False) as obs:
                    if observation_hash({key: obs[key] for key in OBS_KEYS}) != observation_hash(
                            {key: data[prefix + '_' + key] for key in OBS_KEYS}):
                        raise RuntimeError('Observation file differs from audited transition')
    return {**certificate, 'group_oof_fold': entry['group_oof_fold'],
            'family': entry['family'], 'category': entry['category'],
            'episode_directory': str(folder), 'summary_sha256': file_sha(summary_path)}


def parse_costs(accounting, expected_steps):
    costs = {}
    for line in accounting.splitlines():
        fields = line.split('|')
        if len(fields) < 5 or fields[0] not in expected_steps:
            continue
        step, state, exit_code, elapsed, tres = fields[:5]
        if step in costs:
            raise RuntimeError('Duplicate accounting row')
        expected_state, expected_seconds = expected_steps[step]
        if state != expected_state or (state == 'COMPLETED' and exit_code != '0:0'):
            raise RuntimeError('Unexpected Slurm status: ' + step)
        if state == 'FAILED' and exit_code == '0:0':
            raise RuntimeError('Failed attempt unexpectedly reports clean exit')
        if not re.search(r'(^|,)gres/gpu=1(,|$)', tres):
            raise RuntimeError('Unexpected GPU allocation: ' + step)
        seconds = int(elapsed)
        if expected_seconds is not None and seconds != expected_seconds:
            raise RuntimeError('Frozen historical cost changed: ' + step)
        costs[step] = {'step': step, 'state': state, 'exit_code': exit_code,
                       'gpu_count': 1, 'gpu_seconds': seconds}
    if set(costs) != set(expected_steps):
        raise RuntimeError('Accounting missing registered steps')
    return list(costs.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, default=ROOT / 'qgf_gradient_v1/training288_v2_remaining')
    parser.add_argument('--check-readiness', action='store_true')
    parser.add_argument('--verify-preserved-only', action='store_true')
    args = parser.parse_args()
    plan, code, runs = args.plan, ROOT / 'qgf_gradient_v1', ROOT / 'runs'
    if file_sha(plan / 'REGISTRATION.json') != PLAN_SHA:
        raise RuntimeError('Remaining-cohort registration changed')
    ready = ((plan / 'ALL_SHARDS_AUDITED').exists()
             and (plan / 'dispatcher_exit_code').exists()
             and (plan / 'dispatcher_exit_code').read_text().strip() == '0')
    if args.check_readiness:
        print(json.dumps({'ready': ready, 'qualification_run': False,
                          'reason': 'All registered shards and independent audits must finish first.'}))
        return
    if not ready and not args.verify_preserved_only:
        raise RuntimeError('Full fixed cohort not ready; no intermediate qualification')
    destination = plan / 'DATASET_RESULT.json'
    if destination.exists():
        raise RuntimeError('Never overwrite a frozen dataset result')
    manifest_path = code / 'evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Manifest changed')
    expected = {row['episode_id']: row for row in json.loads(manifest_path.read_text())['partitions']['train']}
    registration = json.loads((plan / 'REGISTRATION.json').read_text())
    rows, evidence, completed_paths = [], [], {}

    def add(folder, certificate):
        name = certificate['episode_id']
        if name in completed_paths:
            raise RuntimeError('Repeated cohort entry: ' + name)
        completed_paths[name] = str(folder)
        rows.append(verify_episode(folder, expected[name], certificate))

    integrity = runs / 'qgf_gradient_collector_integrity_v1'
    integrity_audit = integrity / 'INDEPENDENT_AUDIT.json'
    old_registration = json.loads((code / 'training288_v1/REGISTRATION.json').read_text())
    if file_sha(integrity_audit) != old_registration['integrity_audit_sha256']:
        raise RuntimeError('Original integrity certificate changed')
    for row in json.loads(integrity_audit.read_text())['episodes']:
        add(integrity / row['episode_id'], row)
    preservation = code / 'gripper_failure_v1/PRESERVATION_AUDIT.json'
    if file_sha(preservation) != PRESERVATION_SHA:
        raise RuntimeError('Preservation certificate changed')
    retained = json.loads(preservation.read_text())
    if retained['complete_episode_count'] != 26 or retained['censored_episode_policy_outcome'] is not None:
        raise RuntimeError('Old partial episode got an invented outcome')
    for item in retained['censored_prefix']:
        if file_sha(Path(item['path'])) != item['sha256']:
            raise RuntimeError('Original partial prefix changed')
    if file_sha(code / 'training288_v2/STOP_RESULT.json') != 'ba9bd2cdbe03910d8ab6d0327f3d431dcac64fec5e136ccaab2612e7ba8f66c4':
        raise RuntimeError('Original recovery failure record changed')
    if not (runs / 'qgf_gradient_training288_v1_shard0/PROCESS_FAILED').exists():
        raise RuntimeError('Original failed collection marker was removed')
    for row in retained['complete_episode_audits']:
        add(runs / 'qgf_gradient_training288_v1_shard0' / row['episode_id'], row)
    resumed = runs / 'qgf_gradient_resume_v2_one'
    resume_audit = resumed / 'RESUME_AUDIT.json'
    if (not (resumed / 'RESUME_AUDIT_PASS').exists()
            or file_sha(resume_audit) != registration['resume_audit_sha256']):
        raise RuntimeError('Resume certificate changed or missing')
    resumed_result = json.loads(resume_audit.read_text())
    if resumed_result['status'] != 'RESUMED_EPISODE_INDEPENDENT_AUDIT_PASS':
        raise RuntimeError('Recovery not qualified')
    inherited = json.loads((resumed / 'train_0030/inherited_prefix.json').read_text())
    for name, digest in inherited['sha256'].items():
        if (file_sha(Path(inherited['source']) / name) != digest
                or file_sha(resumed / 'train_0030' / name) != digest):
            raise RuntimeError('Recovered prefix provenance changed')
    add(resumed / 'train_0030', resumed_result['episode'])
    for name, folder in registration['completed_episode_directories'].items():
        if completed_paths.get(name) != folder:
            raise RuntimeError('Preserved31-entry ledger changed')
    if len(completed_paths) != 31:
        raise RuntimeError('Incorrect preserved/recovered entry count')
    if args.verify_preserved_only:
        print(json.dumps({'preserved_entries_verified': 31, 'qualification_run': False,
                          'source_sha256': file_sha(Path(__file__)),
                          'scope': 'Hash/provenance/observation reconciliation only; no data admission or fit.'}))
        return
    expected_steps = {f'1593640.{step}': value for step, value in COLLECTION_STEPS.items()}
    for shard in registration['shards']:
        run = Path(shard['run_directory'])
        for flag in ('COLLECTOR_AUDIT_PASS', 'COLLECTION_COMPLETE', 'PROCESS_COMPLETE'):
            if not (run / flag).exists():
                raise RuntimeError('Unfinished run: ' + str(run))
        if (run / 'process_exit_code').read_text().strip() != '0':
            raise RuntimeError('Nonclean fresh collection process')
        if file_sha(Path(shard['registration'])) != shard['sha256']:
            raise RuntimeError('Shard registration changed')
        if file_sha(run / 'registration.json') != shard['sha256']:
            raise RuntimeError('Run did not use the registered shard')
        audit_path = run / 'INDEPENDENT_AUDIT.json'
        audit = json.loads(audit_path.read_text())
        if audit['status'] != 'COLLECTOR_INTEGRITY_PASS' or file_sha(run / 'report.json') != audit['collection_report_sha256']:
            raise RuntimeError('Independent audit/report changed')
        if sorted(row['episode_id'] for row in audit['episodes']) != sorted(shard['episode_ids']):
            raise RuntimeError('Shard population differs')
        for row in audit['episodes']:
            add(run / row['episode_id'], row)
        match = re.search(r'job=(\d+) step=(\d+)', (run / 'allocation.txt').read_text())
        if not match or match.group(1) != '1593640':
            raise RuntimeError('Missing/changed allocation')
        step = match.group(1) + '.' + match.group(2)
        if step in expected_steps:
            raise RuntimeError('GPU accounting step counted twice')
        expected_steps[step] = ('COMPLETED', None)
        evidence.append({'run': str(run), 'audit_sha256': file_sha(audit_path),
                         'report_sha256': file_sha(run / 'report.json')})
    reconcile_entries(rows, expected)
    accounting = subprocess.check_output(['sacct', '-j', '1593640', '-P', '-n',
        '--format=JobID,State,ExitCode,ElapsedRaw,AllocTRES'], text=True)
    costs = parse_costs(accounting, expected_steps)
    integration = parse_costs(accounting, {f'1593640.{step}': value for step, value in INTEGRATION_STEPS.items()})
    collection_seconds = sum(row['gpu_seconds'] for row in costs)
    if collection_seconds > 24 * 3600:
        raise RuntimeError('Collection budget exceeded')
    result = {**qualification(rows), 'entries': rows, 'episodes': len(rows),
              'replans': sum(row['replans'] for row in rows),
              'physical_groups': len({row['physical_input_group'] for row in rows}),
              'family_counts': dict(Counter(row['family'] for row in rows)),
              'category_counts': dict(Counter(row['category'] for row in rows)),
              'manifest_sha256': MANIFEST_SHA, 'registration_sha256': PLAN_SHA,
              'preservation_audit_sha256': PRESERVATION_SHA,
              'resume_audit_sha256': file_sha(resume_audit), 'evidence': evidence,
              'collection_steps_including_failures': costs, 'integration_steps': integration,
              'collection_gpu_hours': collection_seconds / 3600,
              'total_gpu_hours_through_collection': (collection_seconds + sum(row['gpu_seconds'] for row in integration)) / 3600,
              'failed_training_attempts': [row for row in costs if row['state'] == 'FAILED'],
              'recovery_disclosure': 'V2 raw raster failed; V3 restored original measured sensor sample. Original controller snapshots unavailable; action/physical/feedback/RNG history and repeated controller traces audited. Reconstructed prefix video is not original footage.',
              'audit_source_sha256': file_sha(Path(__file__)),
              'scope': 'Fixed-cohort data qualification only. No critic fit or online method result.'}
    destination.write_text(json.dumps(result, indent=2, sort_keys=True))
    (plan / 'DATASET_RESULT_SHA256.txt').write_text(file_sha(destination) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('entries', 'evidence')}, indent=2))


if __name__ == '__main__':
    main()
