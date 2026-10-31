"""Fixed eight remaining OOF fits, two owned GPUs, no model selection or refits."""

import json
from pathlib import Path
import subprocess
import time

from corpus_reader import sha
from train_rl_fold import validate_registration


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
RUN = CODE / 'rl_oof_remaining_v1'
FIRST = ROOT / 'runs/qgf_rl_oof_seed202640101_fold0_v1'


def verify_sources():
    for line in (CODE / 'RL_OOF_REMAINING_SOURCE_SHA256SUMS').read_text().splitlines():
        expected, path = line.split(maxsplit=1)
        if sha(Path(path.strip())) != expected:
            raise RuntimeError('OOF registered dependency changed')


def first_state():
    text = subprocess.check_output(['sacct', '-j', '1598338.21', '-n', '-P',
        '--format=JobID,State,ExitCode'], text=True)
    fields = next(line.split('|') for line in text.splitlines() if line.startswith('1598338.21|'))
    if fields[1:3] == ['COMPLETED', '0:0']:
        return 'complete'
    if fields[1] in ('RUNNING', 'COMPLETING'):
        return 'active'
    raise RuntimeError('First fixed fit nonclean; never select other seeds')


def main():
    RUN.mkdir()
    result, active = 1, {}
    try:
        verify_sources()
        forecast = json.loads((FIRST / 'COST_FORECAST.json').read_text())
        if not (FIRST / 'COST_GATE_PASS').exists() or not forecast['cost_gate_pass']:
            raise RuntimeError('Actual first-fit measured cost gate missing')
        if forecast['predicted_each_gpu_seconds'] > 1200:
            raise RuntimeError('Measured fit forecast exceeds perworker hard limit')
        first_state()
        base = json.loads((CODE / 'FIRST_RL_FIT_REGISTRATION.json').read_text())
        pending = []
        for seed in (202640101, 202640102, 202640103):
            for fold in (0, 1, 2):
                if (seed, fold) == (202640101, 0):
                    continue
                name = f'qgf_rl_oof_seed{seed}_fold{fold}_v1'
                reg = {**base, 'seed': seed, 'held_fold': fold,
                       'run_directory': str(ROOT / 'runs' / name)}
                validate_registration(reg)
                path = RUN / (name + '.json')
                with path.open('x') as output:
                    json.dump(reg, output, indent=2)
                pending.append((name, path))
        (RUN / 'REGISTRATION.json').write_text(json.dumps(dict(
            remaining_fits=8, first_step='1598338.21', first_forecast_sha256=sha(FIRST / 'COST_FORECAST.json'),
            predetermined_jobs=[name for name, _ in pending], max_simultaneous_gpu_workers=2,
            total_oof_fits=9, automatic_all_training_refits=False,
            joint_max12_fit_gpu_seconds_including_features=3526+12*1320), indent=2))
        while pending or active:
            for name, (process, log) in list(active.items()):
                status = process.poll()
                if status is not None:
                    log.close()
                    (RUN / (name + '.srun_exit')).write_text(str(status))
                    del active[name]
                    if status:
                        raise RuntimeError('OOF worker nonclean; no automatic retry or replacement')
            occupied = len(active) + (first_state() == 'active')
            while pending and occupied < 2:
                verify_sources()
                name, registration = pending.pop(0)
                command = ['srun', '--jobid=1598338', '--overlap', '--ntasks=1', '--cpus-per-task=4',
                    '--mem=20G', '--gres=gpu:1', '--time=00:22:00', 'bash',
                    str(CODE / 'run_rl_oof_worker.sh'), str(registration),
                    str(ROOT / 'runs' / (name + '_process'))]
                log = (RUN / (name + '.log')).open('x')
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                active[name] = (process, log)
                occupied += 1
                print('LAUNCHED_FIXED_OOF', name, 'owned_srun_pid', process.pid, flush=True)
            if pending or active:
                time.sleep(10)
        if first_state() != 'complete':
            raise RuntimeError('First fixed worker not clean at cohort completion')
        (RUN / 'ALL_NINE_OOF_PROCESSES_RETURNED').touch()
        result = 0
    finally:
        # Never send signals to unrelated processes or replace a failed fold.
        for name, (process, log) in active.items():
            status = process.wait()
            log.close()
            (RUN / (name + '.srun_exit')).write_text(str(status))
        (RUN / 'dispatcher_exit_code').write_text(str(result))


if __name__ == '__main__':
    main()
