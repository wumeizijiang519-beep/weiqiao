"""Freeze the nine action-dynamics auxiliary worker registrations."""

import hashlib
import json
from pathlib import Path


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
CODE = ROOT / 'qgf_gradient_v1'
CORPUS_DIR = ROOT / 'runs/qgf_gradient_full_feature_cpu_audit_v1'


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    destination = CODE / 'action_dynamics_aux_reg_v1'
    destination.mkdir()
    report = json.loads((CORPUS_DIR / 'REPORT.json').read_text())
    if (report['status'] != 'FULL_FEATURE_CORPUS_INDEPENDENT_AUDIT_PASS'
            or not (CORPUS_DIR / 'FEATURE_CORPUS_AUDIT_PASS').exists()
            or sha(CORPUS_DIR / 'CORPUS.npz') != report['corpus_sha256']
            or sha(CORPUS_DIR / 'CORPUS_METADATA.json') != report['metadata_sha256']):
        raise RuntimeError('Frozen full corpus gate is not intact')
    worker = CODE / 'train_action_dynamics_fold.py'
    protocol = CODE / 'ACTION_DYNAMICS_AUX_V1.md'
    shared = dict(
        protocol=str(protocol), protocol_sha256=sha(protocol),
        worker_sha256=sha(worker), corpus=str(CORPUS_DIR / 'CORPUS.npz'),
        corpus_sha256=report['corpus_sha256'], metadata=str(CORPUS_DIR / 'CORPUS_METADATA.json'),
        metadata_sha256=report['metadata_sha256'], corpus_report_sha256=sha(CORPUS_DIR / 'REPORT.json'),
        updates=5000, batch_size=256, hard_gpu_seconds=900,
        causal_signal_v2_inputs_forbidden=True, online_efficacy=None)
    paths = []
    for seed in (202641201, 202641202, 202641203):
        for fold in (0, 1, 2):
            name = f'qgf_action_dynamics_seed{seed}_fold{fold}_v1'
            payload = dict(shared, seed=seed, held_fold=fold,
                           run_directory=str(ROOT / 'runs' / name))
            path = destination / (name + '.json')
            path.write_text(json.dumps(payload, indent=2))
            paths.append(dict(path=str(path), sha256=sha(path)))
    manifest = dict(status='ACTION_DYNAMICS_AUX_V1_PREREGISTERED', workers=paths,
        worker_count=9, seeds=[202641201, 202641202, 202641203], folds=[0, 1, 2],
        max_parallel_workers=2, parent_job=1598338, total_gpu_seconds_cap=8100,
        source_sha256={name: sha(CODE / name) for name in (
            'ACTION_DYNAMICS_AUX_V1.md', 'train_action_dynamics_fold.py',
            'run_action_dynamics_owned_extern.sh', 'dispatch_action_dynamics_aux.py',
            'ACTION_DYNAMICS_AUX_V1_DISPATCH_REPAIR.md')})
    (destination / 'REGISTRATION_MANIFEST.json').write_text(json.dumps(manifest, indent=2))
    (destination / 'REGISTRATION_COMPLETE').touch()
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()

