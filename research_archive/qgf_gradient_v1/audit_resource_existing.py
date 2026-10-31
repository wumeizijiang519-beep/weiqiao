"""CPU-only completion audit: repair reference location, never repeat inference."""

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
RUN = ROOT / 'runs/qgf_resource_v1_gpu4_gpu3_retry1'
REFERENCE = ROOT / 'runs/qgf_gradient_zero_action_v1_retry2/arrays.npz'
REFERENCE_SHA = '024cb78cbc5610a45bd2432317323ae96520ba483f72d36512998a27d6feb3cb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = RUN / 'CPU_PORTABILITY_AUDIT.json'
    if output.exists():
        raise RuntimeError('Audit result already frozen; do not repeat')
    if sha(REFERENCE) != REFERENCE_SHA:
        raise RuntimeError('Frozen Stage0 reference changed')
    report = json.loads((RUN / 'report.json').read_text())
    if report['status'] != 'ENGINEERING_PASS' or not all(report['checks'].values()):
        raise RuntimeError('Actual WAM integration did not pass')
    egl = json.loads((RUN / 'egl_report.json').read_text())
    if egl['status'] != 'EGL_RESOURCE_PASS':
        raise RuntimeError('Missing empty-scene render evidence')
    errors = {}
    with np.load(REFERENCE, allow_pickle=False) as expected:
        with np.load(RUN / 'arrays.npz', allow_pickle=False) as actual:
            if set(expected.files) != set(actual.files):
                raise RuntimeError('Array inventory mismatch')
            for key in expected.files:
                a, b = actual[key], expected[key]
                if a.shape != b.shape or not np.isfinite(a).all():
                    raise RuntimeError('Array contract mismatch: ' + key)
                errors[key] = float(np.max(np.abs(a - b)))
    status = 'NUMERIC_PORTABILITY_PASS_WRAPPER_FAILED' if max(errors.values()) <= 1e-6 else 'NUMERIC_PORTABILITY_FAILED'
    result = dict(status=status, errors=errors, tolerance=1e-6,
                  reference=str(REFERENCE), reference_sha256=REFERENCE_SHA,
                  actual_sha256=sha(RUN / 'arrays.npz'),
                  original_wrapper_exit=int((RUN / 'process_exit_code').read_text()),
                  original_failure_preserved=(RUN / 'PROCESS_FAILED').exists(),
                  cpu_auditor_clean_exit=True, robot_actions=0, new_gpu_seconds=0,
                  scope='Existing zero-action arrays only; not RL or efficacy evidence',
                  audit_source_sha256=sha(Path(__file__)))
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    if max(errors.values()) > 1e-6:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
