"""Read-only CPU audit liveness evidence; never certify data or signal a process."""

import argparse
import json
import os
from pathlib import Path
import time


def snapshot(pid, expected_run):
    proc = Path('/proc') / str(pid)
    if proc.stat().st_uid != os.getuid():
        raise RuntimeError('Audit process is not owned by the calling user')
    arguments = proc.joinpath('cmdline').read_bytes().decode().strip('\0').split('\0')
    if (not any(Path(value).name == 'audit_collection_v2.py' for value in arguments)
            or '--run' not in arguments
            or arguments[arguments.index('--run') + 1] != str(expected_run)):
        raise RuntimeError('PID is not the exact expected independent auditor')
    raw_stat = proc.joinpath('stat').read_text()
    fields = raw_stat[raw_stat.rfind(')') + 2:].split()
    io = {key: int(value) for key, value in (line.split(':') for line in proc.joinpath('io').read_text().splitlines())}
    files = []
    for descriptor in proc.joinpath('fd').iterdir():
        try:
            target = os.readlink(descriptor)
        except OSError:
            continue
        if target.startswith(str(expected_run) + '/'):
            files.append(target)
    return {'monotonic_seconds': time.monotonic(), 'pid': pid, 'uid': proc.stat().st_uid,
            'process_state': fields[0], 'process_start_ticks': int(fields[19]),
            'cpu_user_ticks': int(fields[11]), 'cpu_system_ticks': int(fields[12]),
            'io': io, 'open_corpus_files': sorted(files)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    first = snapshot(args.pid, args.run)
    time.sleep(5)
    second = snapshot(args.pid, args.run)
    if first['process_start_ticks'] != second['process_start_ticks']:
        raise RuntimeError('Process identity changed between samples')
    deltas = {key: second['io'][key] - first['io'][key] for key in first['io']}
    cpu_delta = (second['cpu_user_ticks'] + second['cpu_system_ticks']
                 - first['cpu_user_ticks'] - first['cpu_system_ticks'])
    record = {'scope': 'Read-only liveness telemetry, not audit PASS or dataset admission',
              'first': first, 'second': second, 'io_delta': deltas,
              'cpu_tick_delta': cpu_delta, 'activity_observed': bool(cpu_delta > 0 or deltas['rchar'] > 0),
              'process_signalled': False, 'gpu_used': False}
    with args.output.open('x') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    main()
