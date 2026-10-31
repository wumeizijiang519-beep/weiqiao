"""Single CPU-only continuation after all frozen collection/audit steps finish."""

import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
PLAN = CODE / 'training288_v2_remaining'
RUN = CODE / 'post_collection_cpu_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # Atomic mkdir prevents a second watcher from taking the same continuation.
    RUN.mkdir()
    start = time.time()
    (RUN / 'start_epoch').write_text(str(start))
    code = 1
    try:
        source = json.loads((CODE / 'AGGREGATION_V2_REGISTRATION.json').read_text())
        print('WAITING_FOR_ORIGINAL_DISPATCHER', flush=True)
        while time.time() - start < 21600:
            exit_path = PLAN / 'dispatcher_exit_code'
            if exit_path.exists():
                if exit_path.read_text().strip() != '0':
                    raise RuntimeError('Original collection dispatcher failed; no aggregation')
                if not (PLAN / 'ALL_SHARDS_AUDITED').exists():
                    raise RuntimeError('Clean dispatcher missing all-audited marker')
                break
            time.sleep(15)
        else:
            raise RuntimeError('CPU continuation wait timed out; no scientific settings changed')
        if (PLAN / 'DATASET_RESULT.json').exists():
            (RUN / 'ALREADY_EXISTS_REQUIRES_AUDIT').touch()
            code = 0
            return
        # Verify exact schema below against frozen registration before deployment.
        for name, expected in source['source_sha256'].items():
            if sha(CODE / name) != expected:
                raise RuntimeError('Registered aggregation source changed: ' + name)
        command = ['srun', '--jobid=1593640', '--overlap', '--ntasks=1', '--cpus-per-task=2',
                   '--mem=8G', '--gres=gpu:0', '--time=01:30:00',
                   'bash', str(CODE / 'run_post_collection_cpu.sh')]
        (RUN / 'command.json').write_text(json.dumps(command))
        print('DISPATCHING_ZERO_GPU_AGGREGATION', flush=True)
        with (RUN / 'srun.log').open('x') as output:
            code = subprocess.call(command, stdout=output, stderr=subprocess.STDOUT)
        if code:
            raise RuntimeError('CPU aggregation returned nonzero; preserve all evidence')
        (RUN / 'CPU_AGGREGATION_RETURNED').touch()
    finally:
        (RUN / 'controller_exit_code').write_text(str(code))
        (RUN / 'end_epoch').write_text(str(time.time()))


if __name__ == '__main__':
    main()
