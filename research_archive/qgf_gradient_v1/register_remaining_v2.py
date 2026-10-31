"""Register untouched fixed cohort entries after the audited checkpoint repair."""

import json
import math
import subprocess

from wam_runtime import ROOT, MANIFEST_SHA, file_sha


def main():
    code = ROOT / 'qgf_gradient_v1'
    runs = ROOT / 'runs'
    resume = runs / 'qgf_gradient_resume_v2_one'
    if not (resume / 'RESUME_AUDIT_PASS').exists():
        raise RuntimeError('Independent continuation audit must pass first')
    recovered = json.loads((resume / 'RESUME_AUDIT.json').read_text())
    if recovered['status'] != 'RESUMED_EPISODE_INDEPENDENT_AUDIT_PASS':
        raise RuntimeError('Recovery not admitted')
    manifest_path = code / 'evidence/COHORT_MANIFEST.json'
    if file_sha(manifest_path) != MANIFEST_SHA:
        raise RuntimeError('Cohort changed')
    old_plan = json.loads((code / 'training288_v1/REGISTRATION.json').read_text())
    preservation_path = code / 'gripper_failure_v1/PRESERVATION_AUDIT.json'
    if file_sha(preservation_path) != '7c45722ff35004976276f01a7fa79ebd34c5e742617269c18d4188869c06bb89':
        raise RuntimeError('Frozen preservation audit changed')
    preserved = json.loads(preservation_path.read_text())
    if preserved['complete_episode_count'] != 26:
        raise RuntimeError('Unexpected inherited completion count')
    directories = {}
    for base, count in [(runs / 'qgf_gradient_collector_integrity_v1', 4),
                        (runs / 'qgf_gradient_training288_v1_shard0', 26), (resume, 1)]:
        found = sorted(base.glob('train_*/EPISODE_COMPLETE'))
        if len(found) != count:
            raise RuntimeError('Unexpected completed entry count at ' + str(base))
        for marker in found:
            name = marker.parent.name
            if name in directories:
                raise RuntimeError('Duplicate fixed entry')
            directories[name] = str(marker.parent)
    manifest = json.loads(manifest_path.read_text())
    remaining = [row['episode_id'] for row in manifest['partitions']['train']
                 if row['episode_id'] not in directories]
    if len(directories) != 31 or len(remaining) != 257 or len(set(remaining)) != 257:
        raise RuntimeError('Fixed cohort accounting error')
    elapsed = subprocess.check_output(['sacct', '-j', '1593640.323', '-P', '-n',
                                       '--format=JobID,State,ExitCode,ElapsedRaw'], text=True)
    matching = [line.split('|') for line in elapsed.splitlines() if line.startswith('1593640.323|')]
    if len(matching) != 1 or matching[0][1:3] != ['COMPLETED', '0:0']:
        raise RuntimeError('Continuation Slurm exit not clean')
    spent = 4350 + int(matching[0][3])
    p90 = old_plan['budget']['measured_p90_episode_seconds']
    overhead = old_plan['budget']['measured_load_overhead_seconds'] + 60
    forecast = spent + len(remaining) * p90 + 4 * overhead
    hard_per_shard = 15600
    hard_total = spent + 4 * hard_per_shard
    if max(forecast, hard_total) > 24 * 3600 * .8:
        raise RuntimeError('No collection budget with twenty percent reserve')
    destination = code / 'training288_v2_remaining'
    destination.mkdir(exist_ok=False)
    sources = list(json.loads((resume / 'registration.json').read_text())['source_sha256'])
    sources += ['run_remaining_shard_v2.sh', 'dispatch_remaining_v2.sh']
    hashes = {name: file_sha(code / name) for name in dict.fromkeys(sources)}
    common = {'version': 'fixed257_v2_after_checkpoint_repair', 'source_sha256': hashes,
              'manifest_sha256': MANIFEST_SHA, 'resume_episode_ids': [],
              'no_automatic_retry': True, 'hard_wall_seconds': hard_per_shard - 100}
    shards = []
    for index in range(4):
        # Preserve manifest order, without stratifying on observed outcomes.
        ids = remaining[math.ceil(index * 257 / 4):math.ceil((index + 1) * 257 / 4)]
        run = runs / f'qgf_gradient_remaining257_v2_shard{index}'
        if run.exists():
            raise RuntimeError('Run already exists')
        path = destination / f'shard{index}.json'
        path.write_text(json.dumps({**common, 'episode_ids': ids, 'run_directory': str(run)}, indent=2))
        shards.append({'registration': str(path), 'sha256': file_sha(path),
                       'run_directory': str(run), 'episode_ids': ids})
    result = {'status': 'FIXED_UNTOUCHED257_ADMITTED_FOR_COLLECTION_ONLY', 'shards': shards,
              'completed_episode_directories': directories, 'manifest_sha256': MANIFEST_SHA,
              'resume_audit_sha256': file_sha(resume / 'RESUME_AUDIT.json'),
              'preservation_audit_sha256': file_sha(preservation_path),
              'budget': {'spent_collection_gpu_seconds': spent,
                         'p90_episode_seconds': p90, 'forecast_gpu_hours': forecast / 3600,
                         'hard_total_gpu_hours': hard_total / 3600,
                         'cap_gpu_hours': 24, 'reserve_fraction': .2},
              'qualification_unchanged': '288 complete; >=12S12F; >=8 groups per class; all3 OOF folds dual class',
              'old_failed_attempts_preserved_and_charged': True}
    (destination / 'REGISTRATION.json').write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({'plan': str(destination), 'budget': result['budget'],
                      'sha256': file_sha(destination / 'REGISTRATION.json')}, indent=2))


if __name__ == '__main__':
    main()
