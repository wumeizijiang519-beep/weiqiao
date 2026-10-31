"""Bounded CPU orchestrator: prepare, measure one real pilot, then fixed GPU grid."""
import argparse
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--job', required=True)
    args = parser.parse_args()
    stage = args.root / 'qgf_v2'
    suite = stage / 'small_data_cv_v1'
    python = args.root / 'envs' / 'unitas_retry6' / 'bin' / 'python'
    suite.mkdir(exist_ok=True)
    lock = suite / 'orchestrator.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    (suite / 'logs').mkdir()

    def state(status, **extra):
        path = suite / 'STATE.tmp.json'
        path.write_text(json.dumps({'status': status, 'updated_epoch': time.time(), **extra}, indent=2) + '\n')
        path.replace(suite / 'STATE.json')

    def allocation():
        job = subprocess.check_output(['scontrol', 'show', 'job', args.job], universal_newlines=True)
        if 'JobState=RUNNING' not in job or 'UserId=' + pwd.getpwuid(os.getuid()).pw_name + '(' not in job:
            raise RuntimeError('allocation inactive or wrong owner')
        match = re.search(r'\bNodeList=(\S+)', job)
        if not match or ',' in match.group(1) or '[' in match.group(1):
            raise RuntimeError('expected one allocated node')
        processes = subprocess.check_output(['ssh', '-o', 'ConnectTimeout=10', match.group(1),
            'nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv,noheader'],
            universal_newlines=True, timeout=30).strip()
        if processes:
            raise RuntimeError('GPU inventory not idle before dispatch: ' + processes)

    def run(command, name, timeout, environment=None):
        with (suite / 'logs' / name).open('x') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=timeout, env=environment)
        if result.returncode:
            raise RuntimeError(name + ' returned ' + str(result.returncode))

    try:
        state('PREPARING_FOLD_DATA')
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='4')
        run([str(python), str(stage / 'prepare_small_data_cv.py'), '--root', str(args.root)], 'prepare.log', 1800, env)
        allocation()
        state('PILOT_TRAINING', fold=0, variant='td099', seed=0, hard_gpu_hours=1)
        pilot = suite / 'training' / 'fold0_td099_seed0'
        command = ['srun', '--jobid=' + args.job, '--overlap', '--nodes=1', '--ntasks=1',
                   '--gpus=1', '--cpus-per-task=4', 'bash', str(stage / 'run_critic.sh'),
                   '--data', str(suite / 'data' / 'fold0'), '--output', str(pilot),
                   '--variant', 'td099', '--seed', '0', '--small-data-cv']
        pilot_started = time.monotonic()
        run(['timeout', '--kill-after=30', '3600'] + command, 'pilot_srun.log', 3660)
        if not (pilot / 'COMPLETE').exists():
            raise RuntimeError('pilot completion artifact absent')
        measured_wall = time.monotonic() - pilot_started
        metrics = [json.loads(line) for line in (pilot / 'metrics.jsonl').read_text().splitlines()]
        if metrics[-1]['step'] != 10000:
            raise RuntimeError('pilot did not reach fixed step count')
        first1000 = next(row['elapsed_seconds'] for row in metrics if row['step'] == 1000)
        estimate_hours = 35 * measured_wall * 1.5 / 3600
        budget = {'pilot_wall_seconds': measured_wall, 'first1000_seconds': first1000,
                  'remaining_runs': 35, 'forecast_gpu_hours': estimate_hours,
                  'workers': 4, 'forecast_wall_seconds': 9 * measured_wall * 1.5,
                  'parallel_stage_hard_wall_seconds': 10800, 'parallel_stage_hard_gpu_hours': 12}
        (suite / 'measured_budget.json').write_text(json.dumps(budget, indent=2) + '\n')
        if estimate_hours > 8:
            state('STOP_BUDGET_REVIEW', **budget)
            return
        allocation()
        state('PARALLEL_TRAINING', **budget)
        parallel = ['srun', '--jobid=' + args.job, '--overlap', '--nodes=1', '--ntasks=4',
                    '--gpus-per-task=1', '--gpu-bind=single:1', '--cpus-per-task=4',
                    '--kill-on-bad-exit=1', str(python), '-u', str(stage / 'cv_worker.py')]
        run(['timeout', '--kill-after=30', '10800'] + parallel, 'parallel_srun.log', 10860)
        state('SUMMARIZING_FINAL_STEP_RESULTS')
        run([str(python), str(stage / 'summarize_small_data_cv.py')], 'summary.log', 600)
        conclusion = json.loads((suite / 'summary.json').read_text())
        state('METHOD_DIAGNOSTIC_COMPLETE', conclusion=conclusion['status'],
              note='not online robotic efficacy; only four independent failures')
    except Exception as exc:
        state('FAILED', error=repr(exc))
        (suite / 'FAILED.json').write_text(json.dumps({'error': repr(exc)}, indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
