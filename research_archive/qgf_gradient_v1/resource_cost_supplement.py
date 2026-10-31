"""Account owned step_extern workers separately from Slurm collection costs."""

import hashlib
import json
from pathlib import Path


ROOT = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022')
ATTEMPTS = (
    ('qgf_resource_v1_gpu22_gpu0', 0, 7),
    ('qgf_resource_v1_gpu22_gpu1', 0, 3),
    ('qgf_resource_v1_gpu4_gpu3', 1, 55),
    ('qgf_resource_v1_gpu4_gpu3_retry1', 1, 673),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root=ROOT):
    rows = []
    for name, expected_exit, expected_seconds in ATTEMPTS:
        run = root / 'runs' / name
        code = int((run / 'process_exit_code').read_text())
        seconds = int((run / 'charged_gpu_seconds').read_text())
        if (code, seconds) != (expected_exit, expected_seconds):
            raise RuntimeError('Frozen resource cost evidence changed: ' + name)
        files = ['process_exit_code', 'charged_gpu_seconds', 'start_time',
                 'end_time', 'owner.txt', 'cgroup.txt', 'SOURCE_SHA256SUMS']
        marker = 'RESOURCE_COMPLETE' if code == 0 else 'PROCESS_FAILED'
        if not (run / marker).exists():
            raise RuntimeError('Resource exit marker missing: ' + name)
        rows.append(dict(run=str(run), exit_code=code, gpu_count=1,
                         charged_gpu_seconds=seconds, evidence_sha256={
                             name: sha(run / name) for name in files}))
    resource_seconds = sum(row['charged_gpu_seconds'] for row in rows)
    integration_seconds = 1058 + resource_seconds
    if integration_seconds > .8 * 2 * 3600:
        raise RuntimeError('Integration budget reserve exhausted')
    return dict(status='SUPPLEMENTAL_RESOURCE_COSTS_FROZEN', attempts=rows,
                resource_gpu_seconds=resource_seconds,
                original_stage0_gpu_seconds=1058,
                integration_gpu_seconds_including_resources=integration_seconds,
                integration_gpu_hours=integration_seconds / 3600,
                phase_cap_gpu_hours=2, reserve_fraction=.2,
                accounting_scope='worker elapsed device-hours; not parent reservation hours',
                merge_rule='Add resource_gpu_seconds ONCE to old Slurm-only totals; do not add Stage0 twice',
                cpu_comparison_exit_code=2, cpu_comparison_gpu_seconds=0,
                resource_portability_status='NUMERIC_PORTABILITY_FAILED',
                qualification_override=False)


if __name__ == '__main__':
    result = build()
    output = ROOT / 'qgf_gradient_v1/RESOURCE_COST_SUPPLEMENT.json'
    if output.exists():
        raise RuntimeError('Cost supplement already frozen')
    result['source_sha256'] = sha(Path(__file__))
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
