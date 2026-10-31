"""One predetermined actual fit after independent clean full feature audit341."""

import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
CONTROL = CODE / 'first_rl_fit_continuation_v1'
AUDIT = ROOT / 'runs/qgf_gradient_full_feature_cpu_audit_v1'
DATASET_SHA = 'baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87'
NAMES = ('train_rl_fold.py', 'critic.py', 'matched_iql.py', 'core.py', 'features.py',
         'training_data.py', 'rl_corpus.py', 'rl_batches.py', 'critic_metrics.py', 'corpus_reader.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources():
    for line in (CODE / 'FIRST_RL_FIT_CONTINUATION_SHA256SUMS').read_text().splitlines():
        expected, path = line.split(maxsplit=1)
        if sha(Path(path.strip())) != expected:
            raise RuntimeError('First-fit registered source changed')


def main():
    CONTROL.mkdir()
    started, result = time.time(), 1
    try:
        verify_sources()
        print('WAITING_FOR_CLEAN_FULL_FEATURE_CPU_STEP341', flush=True)
        while time.time() - started < 6000:
            if (AUDIT / 'FAILED.txt').exists():
                raise RuntimeError('Independent feature audit failed; no actual fit')
            if (AUDIT / 'FEATURE_CORPUS_AUDIT_PASS').exists():
                lines = subprocess.check_output(['sacct', '-j', '1593640.341', '-P', '-n',
                    '--format=JobID,State,ExitCode'], text=True).splitlines()
                fields = next(line.split('|') for line in lines if line.startswith('1593640.341|'))
                if fields[1:3] == ['COMPLETED', '0:0']:
                    break
                if fields[1] not in ('RUNNING', 'COMPLETING'):
                    raise RuntimeError('Independent feature audit Slurm nonclean')
            time.sleep(15)
        else:
            raise RuntimeError('First fit wait expired; no retry')
        verify_sources()
        report = json.loads((AUDIT / 'REPORT.json').read_text())
        if (report['status'] != 'FULL_FEATURE_CORPUS_INDEPENDENT_AUDIT_PASS'
                or report['dataset_result_sha256'] != DATASET_SHA
                or report['registration_sha256'] != sha(CODE / 'FULL_FEATURE_CPU_AUDIT_REGISTRATION.json')):
            raise RuntimeError('Independent feature certificate mismatch')
        registration = dict(seed=202640101, held_fold=0, updates=20000, batch_size=128,
            learning_rate=3e-4, gamma=1., expectile=.7, target_ema=.005, width=256,
            hard_gpu_seconds=1200, source_sha256={name: sha(CODE / name) for name in NAMES},
            corpus_report=str(AUDIT / 'REPORT.json'), corpus_report_sha256=sha(AUDIT / 'REPORT.json'),
            dataset_sha256=DATASET_SHA, phase_gpu_seconds_before_qualification=3526,
            cumulative_gpu_seconds_before_first_fit=38236,
            run_directory=str(ROOT / 'runs/qgf_rl_oof_seed202640101_fold0_v1'),
            no_actor_loaded=True, timing_prefix_updates_count_toward_final=200,
            max_total_fits_for_cost_forecast=12, conditional_full_refits_require_oof_pass=True)
        from train_rl_fold import validate_registration
        validate_registration(registration)
        reg_path = CODE / 'FIRST_RL_FIT_REGISTRATION.json'
        with reg_path.open('x') as output:
            json.dump(registration, output, indent=2)
        # Scheduler verifies the owned parent allocation; worker additionally
        # rejects a busy/wrong UUID before exposing its sole CUDA device.
        command = ['srun', '--jobid=1598338', '--overlap', '--ntasks=1', '--cpus-per-task=4',
            '--mem=20G', '--gres=gpu:1', '--time=00:22:00',
            'bash', str(CODE / 'run_rl_first_fit.sh'), str(reg_path)]
        (CONTROL / 'command.json').write_text(json.dumps(command))
        print('DISPATCHING_FIXED_FIRST_REAL_RL_FIT_SEED202640101_FOLD0', flush=True)
        with (CONTROL / 'srun.log').open('x') as log:
            result = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        if result:
            raise RuntimeError('First actual fit failed; no automatic retry or other fits')
    finally:
        (CONTROL / 'controller_exit_code').write_text(str(result))
        (CONTROL / 'end_epoch').write_text(str(time.time()))


if __name__ == '__main__':
    main()
