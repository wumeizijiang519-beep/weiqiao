"""One-shot fixed feature-cost pilot after clean real encoder audit; no retries."""

import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
CONTROL = CODE / 'feature_pilot_continuation_v1_retry1'
ENCODER = ROOT / 'runs/qgf_gradient_encoder_audit_v1_retry1'
DATASET_SHA = 'baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87'
REQUIRED = ('extract_feature_blocks.py', 'feature_corpus.py', 'corpus_reader.py',
            'rl_corpus.py', 'training_data.py', 'features.py', 'wam_runtime.py',
            'core.py', 'data_contract.py', 'audit_current_features.py')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources():
    for line in (CODE / 'FEATURE_PILOT_CONTINUATION_RETRY1_SOURCE_SHA256SUMS').read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        if sha(Path(name.strip())) != digest:
            raise RuntimeError('Feature pilot registered dependency changed')


def main():
    CONTROL.mkdir()
    started, exit_code = time.time(), 1
    try:
        verify_sources()
        print('WAITING_FOR_CLEAN_ENCODER_STEP338', flush=True)
        while time.time() - started < 1800:
            path = ENCODER / 'process_exit_code'
            if path.exists():
                if path.read_text().strip() != '0':
                    raise RuntimeError('Encoder failed; no feature pilot or automatic retry')
                rows = subprocess.check_output(['sacct', '-j', '1593640.338', '-n', '-P',
                    '--format=JobID,State,ExitCode,ElapsedRaw'], text=True).strip().splitlines()
                fields = next(line.split('|') for line in rows if line.startswith('1593640.338|'))
                if fields[1:3] == ['COMPLETED', '0:0']:
                    encoder_seconds = 439 + int(fields[3])
                    break
                if fields[1] not in ('RUNNING', 'COMPLETING'):
                    raise RuntimeError('Encoder Slurm status nonclean; no pilot')
            time.sleep(10)
        else:
            raise RuntimeError('Encoder continuation wait expired; no pilot')
        report_path = ENCODER / 'audit/REPORT.json'
        report = json.loads(report_path.read_text())
        if (report['status'] != 'CURRENT_FEATURE_ENCODER_AUDIT_PASS'
                or report['dataset_result_sha256'] != DATASET_SHA
                or not (ENCODER / 'audit/ENCODER_AUDIT_PASS').exists()):
            raise RuntimeError('Encoder report or dataset qualification missing')
        verify_sources()
        dataset = CODE / 'training288_v2_remaining/DATASET_RESULT.json'
        if sha(dataset) != DATASET_SHA:
            raise RuntimeError('Qualified dataset changed')
        supplement = CODE / 'RESOURCE_COST_SUPPLEMENT.json'
        if sha(supplement) != '0defbb9a0a5eaa01ad076b8abe19fbaf0a563665fb8de9dd2c63f4fa25594c65':
            raise RuntimeError('Resource failure accounting changed')
        registration = dict(stage='FIRST_TWO_FIXED_EPISODES_FEATURE_COST_PILOT',
            dataset_result=str(dataset), dataset_sha256=DATASET_SHA,
            encoder_report=str(report_path), encoder_report_sha256=sha(report_path),
            resource_cost_supplement=str(supplement), resource_cost_sha256=sha(supplement),
            source_sha256={name: sha(CODE / name) for name in REQUIRED},
            episode_ids=['train_0000', 'train_0001'], hard_gpu_seconds=1200,
            critic_phase_gpu_seconds_spent=encoder_seconds,
            cumulative_gpu_seconds_before_pilot=34710 + encoder_seconds,
            run_directory=str(ROOT / 'runs/qgf_gradient_feature_cost_pilot_v1'),
            model_load_forecast_seconds=600, measured_feature_p90=None,
            no_scientific_rollout=True, no_critic_fit=True)
        if encoder_seconds + 1320 > .8 * 8 * 3600:
            raise RuntimeError('Feature/critic budget reserve insufficient')
        reg_path = CODE / 'FEATURE_COST_PILOT_REGISTRATION.json'
        with reg_path.open('x') as output:
            json.dump(registration, output, indent=2)
        command = ['srun', '--jobid=1593640', '--overlap', '--ntasks=1', '--cpus-per-task=8',
            '--mem=45G', '--gres=gpu:1', '--time=00:22:00',
            'bash', str(CODE / 'run_feature_cost_pilot.sh'), str(reg_path)]
        (CONTROL / 'command.json').write_text(json.dumps(command))
        print('REGISTERED_AND_DISPATCHING_FIXED_TWO_EPISODE_FEATURE_COST_PILOT', flush=True)
        with (CONTROL / 'srun.log').open('x') as log:
            exit_code = subprocess.call(command, stdout=log, stderr=subprocess.STDOUT)
        if exit_code:
            raise RuntimeError('Feature pilot nonclean; preserve data and stop')
    finally:
        (CONTROL / 'controller_exit_code').write_text(str(exit_code))
        (CONTROL / 'end_epoch').write_text(str(time.time()))


if __name__ == '__main__':
    main()
