"""One independent CPU qualification after all nine fixed fit processes finish."""

import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT/'qgf_gradient_v1'
RUN = CODE/'oof_qualification_cpu_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources():
    for line in (CODE/'OOF_QUALIFICATION_SOURCE_SHA256SUMS').read_text().splitlines():
        expected, path = line.split(maxsplit=1)
        if sha(Path(path.strip())) != expected:
            raise RuntimeError('Registered OOF qualification dependency changed')


def main():
    RUN.mkdir()
    started, code = time.time(), 1
    try:
        verify_sources()
        print('WAITING_FOR_ALL_NINE_FIXED_FITS_NO_PARTIAL_SCORES', flush=True)
        while time.time()-started < 10800:
            exit_path = CODE/'rl_oof_owned_extern_v1/dispatcher_exit_code'
            if exit_path.exists():
                if exit_path.read_text().strip() != '0':
                    raise RuntimeError('OOF fit dispatcher failed; incomplete is not scientific negative')
                break
            time.sleep(15)
        else:
            raise RuntimeError('OOF completion wait expired; no resampling/retry')
        verify_sources()
        if (CODE/'OOF_QUALIFICATION_RESULT.json').exists():
            raise RuntimeError('OOF result already exists; never repeat or overwrite')
        corpus = ROOT/'runs/qgf_gradient_full_feature_cpu_audit_v1/REPORT.json'
        if sha(corpus) != 'b0ea11ddd47233e913fa48fe0cd7964d78fda0a5f96d336b2b11c732ef4f1cc0':
            raise RuntimeError('Admitted corpus certificate changed')
        names = ('qualify_rl_oof.py','critic_metrics.py','training_data.py','corpus_reader.py',
                 'rl_corpus.py','train_rl_fold.py')
        reg = CODE/'OOF_QUALIFICATION_REGISTRATION.json'
        with reg.open('x') as output:
            json.dump(dict(source_sha256={name: sha(CODE/name) for name in names},
                corpus_report=str(corpus), corpus_report_sha256=sha(corpus),
                dataset_sha256='baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87',
                bootstrap_seed=202640901,bootstrap_draws=10000,normalizer_atol=1e-7,normalizer_rtol=1e-6,
                source_registration_sha256=sha(CODE/'OOF_QUALIFICATION_SOURCE_SHA256SUMS'),
                zero_gpu=True,hard_cpu_seconds=5400), output, indent=2)
        command = ['srun','--jobid=1593640','--overlap','--ntasks=1','--cpus-per-task=2',
                   '--mem=8G','--gres=gpu:0','--time=01:30:00','bash',
                   str(CODE/'run_oof_qualification.sh'),str(reg)]
        (RUN/'command.json').write_text(json.dumps(command))
        print('DISPATCHING_ONE_CPU_OOF_QUALIFICATION_ALL_SEEDS_FOLDS', flush=True)
        with (RUN/'srun.log').open('x') as output:
            code = subprocess.call(command,stdout=output,stderr=subprocess.STDOUT)
        if code:
            raise RuntimeError('OOF qualification infrastructure audit nonclean; preserve evidence')
    finally:
        (RUN/'controller_exit_code').write_text(str(code))


if __name__ == '__main__':
    main()
