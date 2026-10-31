"""Run exact unused OOF registrations on verified owned extern GPU UUID slots."""

import json
from pathlib import Path
import subprocess
import time

from corpus_reader import sha


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
RUN = CODE / 'rl_oof_owned_extern_v1'


def first_active():
    text = subprocess.check_output(['sacct', '-j', '1598338.21', '-P', '-n',
        '--format=JobID,State,ExitCode'], text=True)
    fields = next(line.split('|') for line in text.splitlines() if line.startswith('1598338.21|'))
    if fields[1:3] == ['COMPLETED', '0:0']:
        return False
    if fields[1] in ('RUNNING', 'COMPLETING'):
        return True
    raise RuntimeError('Original actual first fit failed; no alternate winner')


def verify_sources():
    for line in (CODE / 'RL_OWNED_EXTERN_SOURCE_SHA256SUMS').read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        if sha(Path(path.strip())) != digest:
            raise RuntimeError('Owned extern source/registration changed')


def main():
    RUN.mkdir()
    active, result = {}, 1
    try:
        verify_sources()
        pending = []
        for seed in (202640101, 202640102, 202640103):
            for fold in (0, 1, 2):
                if (seed, fold) == (202640101, 0):
                    continue
                name = f'qgf_rl_oof_seed{seed}_fold{fold}_v1'
                path = CODE / 'rl_oof_remaining_v1_retry1' / (name + '.json')
                reg = json.loads(path.read_text())
                if Path(reg['run_directory']).exists():
                    raise RuntimeError('Unused fit unexpectedly exists; never overwrite/retrain')
                pending.append((name, path))
        (RUN / 'REGISTRATION.json').write_text(json.dumps(dict(
            exact_reused_registrations=[str(path) for _, path in pending],
            original_first_step='1598338.21', max_total_workers=2,
            transport='verified_owned_step_extern_not_exclusive_Slurm_steps',
            parent_allocation_reservation_hours_separate_from_worker_hours=True), indent=2))
        while pending or active:
            for gpu, (name, process_dir) in list(active.items()):
                path = process_dir / 'process_exit_code'
                if path.exists():
                    if path.read_text().strip() != '0':
                        raise RuntimeError('Owned extern fit failed; no further automatic retry')
                    del active[gpu]
            occupied = set(active)
            if first_active():
                occupied.add(0)
            for gpu in (0, 1):
                if pending and gpu not in occupied:
                    verify_sources()
                    name, reg = pending.pop(0)
                    process_dir = ROOT / 'runs' / (name + '_extern_process')
                    log = RUN / (name + '.log')
                    remote = f'nohup timeout 1320 bash {CODE}/run_rl_owned_extern.sh {reg} {gpu} {process_dir} > {log} 2>&1 < /dev/null & echo $!'
                    launch = subprocess.run(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                        'gpu22', remote], text=True, capture_output=True, timeout=20)
                    (RUN / (name + '.launch.json')).write_text(json.dumps(dict(
                        ssh_exit=launch.returncode, stdout=launch.stdout, stderr=launch.stderr,
                        requested_gpu=gpu, parent_job=1598338)))
                    if not launch.stdout.strip().isdigit():
                        raise RuntimeError('Worker PID launch not confirmed; no blind retry')
                    active[gpu] = (name, process_dir)
                    print('LAUNCHED_OWNED_EXTERN', name, 'GPU', gpu, 'timeoutPID', launch.stdout.strip(), flush=True)
                    # Fail fast on guard failure before a process directory exists.
                    time.sleep(2)
                    if not process_dir.exists():
                        raise RuntimeError('Ownership/idle/UUID guard failed; stop this route')
            if pending or active:
                time.sleep(10)
        if first_active():
            raise RuntimeError('Original first fit still active at final cohort join')
        (RUN / 'ALL_NINE_WORKERS_RETURNED').touch()
        result = 0
    finally:
        # On infrastructure failure do not signal any other worker/user process.
        (RUN / 'dispatcher_exit_code').write_text(str(result))


if __name__ == '__main__':
    main()
