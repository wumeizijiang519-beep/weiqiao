"""One bounded CPU archive retry only if the original terminal archive failed."""

import hashlib
import json
from pathlib import Path
import subprocess
import time


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT/'qgf_gradient_v1'
RUN = CODE/'backup_io_continuation_v1'


def main():
    RUN.mkdir()
    result, started = 1, time.time()
    try:
        while time.time()-started < 2400:
            text = subprocess.check_output(['sacct','-j','1593640.342','-P','-n',
                '--format=JobID,State,ExitCode'], text=True)
            fields = next(line.split('|') for line in text.splitlines() if line.startswith('1593640.342|'))
            if fields[1:3] == ['COMPLETED','0:0']:
                (RUN/'ORIGINAL_ARCHIVE_COMPLETED_NO_RETRY').touch()
                result = 0
                return
            if fields[1] not in ('RUNNING','COMPLETING','PENDING'):
                break
            time.sleep(15)
        else:
            raise RuntimeError('Archive wait expired; no duplicate archive')
        for line in (CODE/'BACKUP_IO_RETRY_SOURCE_SHA256SUMS').read_text().splitlines():
            digest, path = line.split(maxsplit=1)
            if hashlib.sha256(Path(path.strip()).read_bytes()).hexdigest() != digest:
                raise RuntimeError('Registered CPU backup source changed')
        (RUN/'original_terminal_status.json').write_text(json.dumps(fields))
        command = ['srun','--jobid=1593640','--overlap','--ntasks=1','--cpus-per-task=2',
            '--mem=16G','--gres=gpu:0','--time=02:00:00','bash',
            str(CODE/'archive_training_evidence_retry1.sh')]
        (RUN/'command.json').write_text(json.dumps(command))
        print('ONE_CPU_BACKUP_RETRY_PRESERVING_ORIGINAL_PARTIAL',flush=True)
        with (RUN/'srun.log').open('x') as output:
            result = subprocess.call(command,stdout=output,stderr=subprocess.STDOUT)
        if result:
            raise RuntimeError('Bounded backup retry failed; no automatic further retry')
    finally:
        (RUN/'controller_exit_code').write_text(str(result))


if __name__ == '__main__':
    main()
