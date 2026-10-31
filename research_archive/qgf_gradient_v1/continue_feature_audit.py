"""One zero-GPU corpus audit after clean registered extraction340, never training."""

import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
RUN = CODE / 'full_feature_cpu_continuation_v1'
FEATURES = ROOT / 'runs/qgf_gradient_feature_remaining286_v1'
PROCESS = ROOT / 'runs/qgf_gradient_feature_remaining286_v1_process'
NAMES = ('audit_full_feature_corpus.py', 'corpus_reader.py', 'rl_corpus.py',
         'training_data.py', 'features.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources():
    for line in (CODE / 'FULL_FEATURE_CPU_CONTINUATION_SHA256SUMS').read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        if sha(Path(name.strip())) != expected:
            raise RuntimeError('Full feature audit registered source changed')


def main():
    RUN.mkdir()
    start, code = time.time(), 1
    try:
        verify_sources()
        print('WAITING_FOR_CLEAN_FEATURE_STEP340', flush=True)
        while time.time() - start < 7200:
            path = PROCESS / 'process_exit_code'
            if path.exists():
                if path.read_text().strip() != '0':
                    raise RuntimeError('Extraction failed; no CPU audit/automatic retry')
                rows = subprocess.check_output(['sacct', '-j', '1593640.340', '-P', '-n',
                    '--format=JobID,State,ExitCode'], text=True).splitlines()
                fields = next(line.split('|') for line in rows if line.startswith('1593640.340|'))
                if fields[1:3] == ['COMPLETED', '0:0']:
                    break
                if fields[1] not in ('RUNNING', 'COMPLETING'):
                    raise RuntimeError('Extraction step nonclean')
            time.sleep(15)
        else:
            raise RuntimeError('CPU audit wait budget exhausted')
        verify_sources()
        if not (FEATURES / 'FEATURE_EXTRACTION_COMPLETE').exists():
            raise RuntimeError('Full extraction completion marker missing')
        if sha(FEATURES / 'INDEX.json') != (FEATURES / 'INDEX_SHA256.txt').read_text().strip():
            raise RuntimeError('Full index hash mismatch')
        registration = dict(dataset=str(CODE / 'training288_v2_remaining/DATASET_RESULT.json'),
            dataset_sha256='baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87',
            feature_root=str(FEATURES), index_sha256=sha(FEATURES / 'INDEX.json'),
            source_sha256={name: sha(CODE / name) for name in NAMES},
            run_directory=str(ROOT / 'runs/qgf_gradient_full_feature_cpu_audit_v1'),
            gpu_count=0, cpus=2, mem_gib=8, hard_seconds=5400, no_critic_fit=True)
        reg = CODE / 'FULL_FEATURE_CPU_AUDIT_REGISTRATION.json'
        with reg.open('x') as output:
            json.dump(registration, output, indent=2)
        command = ['srun', '--jobid=1593640', '--overlap', '--ntasks=1', '--cpus-per-task=2',
            '--mem=8G', '--gres=gpu:0', '--time=01:30:00',
            'bash', str(CODE / 'run_full_feature_cpu_audit.sh'), str(reg)]
        (RUN / 'command.json').write_text(json.dumps(command))
        print('DISPATCHING_ONE_ZERO_GPU_FULL_FEATURE_AUDIT', flush=True)
        with (RUN / 'srun.log').open('x') as log:
            code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        if code:
            raise RuntimeError('Full feature CPU audit failed; no automatic retry/fit')
    finally:
        (RUN / 'controller_exit_code').write_text(str(code))
        (RUN / 'end_epoch').write_text(str(time.time()))


if __name__ == '__main__':
    main()
