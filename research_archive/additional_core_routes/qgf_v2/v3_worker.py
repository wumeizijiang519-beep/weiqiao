"""One fixed four-GPU worker queue for the QGF-v3 diagnostic."""
import json
import os
from pathlib import Path
import subprocess
from v3_conditions import conditions


def main():
    stage = Path(__file__).resolve().parent
    suite = stage / 'unitas_latent_cv_v1'
    rank = int(os.environ['SLURM_PROCID'])
    for index, row in enumerate(conditions()):
        if index % 4 != rank:
            continue
        output = suite / 'training' / row['name']
        if output.exists():
            raise FileExistsError(output)
        python = '/public/wangsenbao221/pqr/qgf_mainstream_20261022/envs/unitas_retry6/bin/python'
        command = [python, str(stage / 'train_unitas_latent_critic.py'),
                   '--data', str(suite / 'data' / f"fold{row['fold']}"), '--output', str(output),
                   '--seed', str(row['seed']), '--device', 'cuda', '--steps', '10000']
        if row['state_only']:
            command.append('--state-only')
        try:
            with (suite / 'logs' / (row['name'] + '.log')).open('x') as log:
                result = subprocess.run(['timeout', '3600', *command], stdout=log, stderr=subprocess.STDOUT)
            if result.returncode or not (output / 'COMPLETE').exists():
                raise RuntimeError(f"{row['name']} failed: {result.returncode}")
        except Exception as exc:
            (suite / ('FAILED_' + row['name'] + '.json')).write_text(json.dumps({'error': repr(exc), 'condition': row}) + '\n')
            raise


if __name__ == '__main__':
    main()
