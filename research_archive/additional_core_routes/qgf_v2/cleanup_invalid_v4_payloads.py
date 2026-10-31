"""Remove data payloads only from the already-invalid missing-gripper-gain run."""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path('/public/wangsenbao221/pqr/qgf_cvpr_20261018/qgf_multitask_officialconfig_v4_20261020/protocol_invalid_missing_gripper_gain')
REPORT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/invalid_v4_payload_cleanup_20261023.json')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def save(value):
    temporary = REPORT.with_suffix('.tmp.json')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(REPORT)


parser = argparse.ArgumentParser()
parser.add_argument('--delete-invalid-payloads', action='store_true')
args = parser.parse_args()
if ROOT.resolve(strict=True) != ROOT or ROOT.is_symlink() or REPORT.exists():
    raise ValueError('need exact invalid root and fresh cleanup report')
paths = []
for path in sorted(ROOT.rglob('*')):
    if path.is_file() and path.suffix.lower() in ('.npz', '.npy', '.mp4'):
        if path.is_symlink() or ROOT not in path.resolve().parents or not os.access(str(path.parent), os.W_OK):
            raise ValueError('unsafe or unwritable payload: ' + str(path))
        paths.append(path)
records = [{'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path)} for path in paths]
state = {'status': 'VERIFIED_INVALID_PAYLOAD_ALLOWLIST',
         'reason': 'previously marked INVALID_PROTOCOL: missing required gripper gain',
         'preserved': 'all JSON, logs, configuration, code, seeds, summaries and failure markers',
         'files': records, 'logical_bytes': sum(row['bytes'] for row in records), 'deleted': []}
save(state)
if args.delete_invalid_payloads:
    for path in paths:
        path.unlink()
        state['deleted'].append(str(path))
        save(state)
    state['status'] = 'DELETED_INVALID_PAYLOADS'
    save(state)
print(json.dumps({'status': state['status'], 'file_count': len(paths), 'logical_bytes': state['logical_bytes']}))
