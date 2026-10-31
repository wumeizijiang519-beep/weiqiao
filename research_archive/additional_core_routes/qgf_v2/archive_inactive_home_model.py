"""Relocate one explicitly named inactive legacy asset, preserving its bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

SOURCE = Path('/public/home/wangsenbao221/models/OpenWAM-Alpha-Pretrain-Foundation-Model/checkpoint_step_154000.safetensors')
DIRECTORY = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022/home_cleanup_archive_20261023')
DEST = DIRECTORY / SOURCE.name


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(16 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def report(value):
    temporary = DIRECTORY / 'relocation.tmp.json'
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(DIRECTORY / 'relocation.json')


parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()
if SOURCE.is_symlink() or SOURCE.resolve(strict=True) != SOURCE or not SOURCE.is_file():
    raise ValueError('source must be the exact inactive regular file')
metadata = SOURCE.stat()
if metadata.st_uid != os.getuid() or metadata.st_size != 24813767464:
    raise ValueError('unexpected ownership or file size')
if DEST.exists():
    raise FileExistsError(DEST)
DIRECTORY.mkdir(parents=True, exist_ok=True)
state = {'source': str(SOURCE), 'preserved_archive': str(DEST), 'bytes': metadata.st_size,
         'reason': 'inactive legacy asset relocated; efficacy not judged; no unique result destroyed',
         'status': 'DRY_RUN'}
report(state)
if args.execute:
    temporary = DIRECTORY / (SOURCE.name + '.partial')
    state['status'] = 'COPYING'
    report(state)
    shutil.copy2(str(SOURCE), str(temporary))
    original_sha = digest(SOURCE)
    if digest(temporary) != original_sha:
        raise ValueError('archive copy SHA mismatch; source retained')
    temporary.replace(DEST)
    state.update(status='ARCHIVE_VERIFIED', sha256=original_sha)
    report(state)
    SOURCE.unlink()
    state['source_regular_file_removed'] = True
    try:
        SOURCE.symlink_to(DEST)
        state['host_path_preserved_as_symlink'] = True
    except OSError as exc:
        state['host_symlink_error'] = repr(exc)
    state['status'] = 'RELOCATED_VERIFIED_ASSET'
    state['container_note'] = 'Legacy containers without pqr mounts must restage from archive if reused.'
    report(state)
print(json.dumps(state, indent=2))
