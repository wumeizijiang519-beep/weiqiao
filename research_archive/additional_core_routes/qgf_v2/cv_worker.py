"""One Slurm GPU worker, one fixed queue; never overwrite or duplicate runs."""
import json
import os
from pathlib import Path
import subprocess
from cv_conditions import conditions


def main():
    stage = Path(__file__).resolve().parent
    suite = stage / 'small_data_cv_v1'
    rank = int(os.environ['SLURM_PROCID'])
    for index, row in enumerate(conditions()[1:]):
        if index % 4 != rank:
            continue
        output = suite / 'training' / row['name']
        if output.exists():
            raise FileExistsError('refusing duplicate training directory')
        command = ['bash', str(stage / 'run_critic.sh'), '--data', str(suite / 'data' / f"fold{row['fold']}"),
                   '--output', str(output), '--variant', row['variant'], '--seed', str(row['seed']), '--small-data-cv']
        if row['state_only']:
            command.append('--state-only')
        try:
            with (suite / 'logs' / (row['name'] + '.log')).open('x') as log:
                result = subprocess.run(['timeout', '3600', *command], stdout=log, stderr=subprocess.STDOUT, timeout=3660)
            if result.returncode or not (output / 'COMPLETE').exists():
                raise RuntimeError(f"{row['name']} failed: {result.returncode}")
        except Exception as exc:
            (suite / ('FAILED_' + row['name'] + '.json')).write_text(json.dumps({'error': repr(exc), 'condition': row}) + '\n')
            raise


if __name__ == '__main__':
    main()
