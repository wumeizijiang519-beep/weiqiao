"""Dispatch the nine frozen auxiliary workers over two owned idle GPUs."""

import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
RUN = CODE / 'action_dynamics_aux_dispatch_v1'


def main():
    RUN.mkdir()
    registrations = sorted((CODE / 'action_dynamics_aux_reg_v1').glob(
        'qgf_action_dynamics_seed*_fold*_v1.json'))
    if len(registrations) != 9:
        raise RuntimeError('Expected exactly nine frozen registrations')
    pending = list(registrations)
    active = {}
    result = 1
    try:
        while pending or active:
            for gpu, (_, process_dir) in list(active.items()):
                exit_path = process_dir / 'process_exit_code'
                if exit_path.exists():
                    if exit_path.read_text().strip() != '0':
                        raise RuntimeError('Auxiliary worker failed; no automatic retry')
                    del active[gpu]
            for gpu in (0, 1):
                if pending and gpu not in active:
                    reg = pending.pop(0)
                    name = reg.stem
                    process_dir = ROOT / 'runs' / (name + '_process')
                    log = RUN / (name + '.log')
                    remote = (f'nohup timeout 960 bash {CODE}/run_action_dynamics_owned_extern.sh '
                              f'{reg} {gpu} {process_dir} > {log} 2>&1 < /dev/null & echo $!')
                    launch = subprocess.run(['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
                        'gpu22', remote], text=True, capture_output=True, timeout=20)
                    (RUN / (name + '.launch.json')).write_text(json.dumps(dict(
                        ssh_exit=launch.returncode, stdout=launch.stdout, stderr=launch.stderr,
                        requested_gpu=gpu, parent_job=1598338), indent=2))
                    if launch.returncode or not launch.stdout.strip().isdigit():
                        raise RuntimeError('Owned worker launch not confirmed')
                    active[gpu] = (reg, process_dir)
                    print('LAUNCHED', name, 'GPU', gpu, launch.stdout.strip(), flush=True)
                    time.sleep(2)
                    if not process_dir.exists():
                        raise RuntimeError('Ownership/idle/UUID guard failed')
            if pending or active:
                time.sleep(10)
        (RUN / 'ALL_WORKERS_RETURNED').touch()
        result = 0
    finally:
        (RUN / 'dispatcher_exit_code').write_text(str(result))


if __name__ == '__main__':
    main()

