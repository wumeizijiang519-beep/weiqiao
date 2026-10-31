"""Delete only three explicit, inactive staging duplicates authorized by the user.

Persistent pqr copies were independently SHA-verified on login1 before this
container-side cleanup. This script does not traverse or delete directories.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat

ROOT = Path('/public/home/wangsenbao221/qgf_openwam_water_training_rgbpatch_v1/training_retry2')
ARCHIVE = Path('/public/wangsenbao221/pqr/qgf_cvpr_20261018/openwam_qgf_v1_20261022/water_training_rgbpatch_v1/training_retry2')
FILES = {
    'token_step5000.pt': '7fa0ae6c925847199d78f30740ad9ae8ab253c7d23d0e0e115091f2d6b4a151a',
    'critic_seed0_step10000.pt': '544494d8da07d2786c2b22dac289235f8f9641343a6fef087ea5545fe169075a',
    'critic_seed1_step10000.pt': 'ea4837a9e0d719c6b1c13ac812a3ab413d610b181874327871cea3434bf6a6ae',
}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument('--delete-verified', action='store_true')
args = parser.parse_args()
if ROOT.is_symlink() or ROOT.resolve() != ROOT:
    raise ValueError('unexpected staging-directory redirection')
records = []
for name, expected in FILES.items():
    path = ROOT / name
    if path.is_symlink() or path.resolve(strict=True).parent != ROOT:
        raise ValueError('unexpected checkpoint path')
    metadata = path.stat()
    if not stat.S_ISREG(metadata.st_mode) or digest(path) != expected:
        raise ValueError('file type or SHA mismatch: ' + str(path))
    records.append({'source': str(path), 'preserved_archive': str(ARCHIVE / name),
                    'sha256': expected, 'bytes': metadata.st_size})
if args.delete_verified:
    # All three inputs have passed the allowlist/path/hash checks before deletion.
    for record in records:
        Path(record['source']).unlink()
print(json.dumps({'status': 'DELETED_VERIFIED_STAGING_DUPLICATES' if args.delete_verified else 'VERIFIED_DRY_RUN',
                  'files': records, 'logical_bytes': sum(row['bytes'] for row in records),
                  'scope': 'home staging only; persistent checkpoints/data/results untouched'}, indent=2))
