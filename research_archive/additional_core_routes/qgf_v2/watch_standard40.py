"""Bounded CPU handoff: complete40 -> audited export -> one admitted training run."""
import argparse
import json
import os
import pwd
from pathlib import Path
import subprocess
import time

STATE_PREFIX = 'handoff'

def write_state(directory, state):
    path = directory / (STATE_PREFIX + '_state.tmp.json')
    path.write_text(json.dumps(state, indent=2) + '\n')
    path.replace(directory / (STATE_PREFIX + '_state.json'))


def main():
    global STATE_PREFIX
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--extension20-approved', action='store_true')
    args = parser.parse_args()
    extension = args.extension20_approved
    if extension:
        STATE_PREFIX = 'handoff60'
    stage = args.root / 'qgf_v2'
    lock = stage / (STATE_PREFIX + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    marker = 'STANDARD60_EXTENSION_SRUN_PID' if extension else 'STANDARD40_RETRY2_SRUN_PID'
    deadline = (stage / marker).stat().st_mtime + 10800
    starts = (202615100, 202615200, 202615300, 202615400)
    if extension:
        starts += (202616100, 202616200)
    runs = [stage / 'runs' / f'standard_train10_seed{seed}'
            for seed in starts]
    while True:
        failed = [str(run) for run in runs if (run / 'FAILED').exists()]
        if failed:
            write_state(stage, {'status': 'STOP_COLLECTION_FAILED', 'runs': failed})
            return
        complete = [run for run in runs if (run / 'COLLECTION_COMPLETE').exists()]
        if len(complete) == len(runs):
            break
        if time.time() >= deadline:
            write_state(stage, {'status': 'STOP_COLLECTION_DEADLINE', 'complete_shards': len(complete)})
            return
        write_state(stage, {'status': 'COLLECTING', 'complete_shards': len(complete),
                            'collection_deadline_epoch': deadline})
        time.sleep(30)
    audits = [json.loads((run / 'audit.json').read_text()) for run in runs]
    rows = [row for audit in audits for row in audit['episodes']]
    summary = {'episode_count': len(rows), 'successes': sum(row['success'] for row in rows),
               'failures': sum(not row['success'] for row in rows), 'episodes': rows}
    count = 60 if extension else 40
    (stage / f'standard{count}_combined_audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    dataset = stage / f'dataset{count}_rgbstats_v1'
    python = args.root / 'envs' / 'unitas_retry6' / 'bin' / 'python'
    environment = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '4',
                   'XDG_CACHE_HOME': str(stage / 'cache'), 'CUDA_VISIBLE_DEVICES': ''}
    write_state(stage, {'status': 'AUDITING_AND_EXPORTING', **{key: value for key, value in summary.items() if key != 'episodes'}})
    result = subprocess.run([str(python), str(stage / 'prepare_dataset.py'), '--root', str(args.root),
                             '--output', str(dataset)] + (['--extension20-approved'] if extension else []), env=environment, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, universal_newlines=True, timeout=1800)
    (stage / f'dataset{count}_prepare.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        status = 'STOP_INSUFFICIENT_CLASSES' if 'STOP_INSUFFICIENT_CLASSES' in result.stderr else 'STOP_DATA_AUDIT_FAILED'
        write_state(stage, {'status': status, 'successes': summary['successes'], 'failures': summary['failures']})
        return
    # Slurm, rather than cached node/IP information, allocates the pilot GPU.
    job = subprocess.run(['scontrol', 'show', 'job', args.job], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, universal_newlines=True, check=True).stdout
    if 'JobState=RUNNING' not in job or f'UserId={pwd.getpwuid(os.getuid()).pw_name}(' not in job:
        raise RuntimeError('training allocation no longer belongs to this running task user')
    output = stage / ('training60_v1' if extension else 'training_v1') / 'td099_seed0'
    if output.exists():
        raise FileExistsError('refusing duplicate first training run')
    command = ['srun', f'--jobid={args.job}', '--overlap', '--nodes=1', '--ntasks=1',
               '--gpus=1', '--cpus-per-task=4', 'bash', str(stage / 'run_critic.sh'),
               '--data', str(dataset), '--output', str(output), '--variant', 'td099', '--seed', '0']
    write_state(stage, {'status': 'FIRST_ADMITTED_TRAINING_RUN', 'command': command,
                       'timeout_seconds': 3600, 'gpu_hour_cap': 1,
                       'note': 'measure first1000 steps to budget remaining11 conditions'})
    with (stage / f'first_training{count}_srun.log').open('x') as log:
        pilot_environment = {key: value for key, value in os.environ.items() if key != 'CUDA_VISIBLE_DEVICES'}
        pilot = subprocess.run(['timeout', '3600', *command], stdout=log, stderr=subprocess.STDOUT,
                               env=pilot_environment, timeout=3660)
    write_state(stage, {'status': 'FIRST_TRAINING_COMPLETE' if pilot.returncode == 0 and (output / 'COMPLETE').exists()
                       else 'FIRST_TRAINING_FAILED', 'returncode': pilot.returncode,
                       'remaining_runs': 'not_launched_pending_measured_cost_review'})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        parser_root = Path(__file__).resolve().parent
        write_state(parser_root, {'status': 'HANDOFF_FAILED', 'error': repr(exc)})
        raise
