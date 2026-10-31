#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
RUN="$STAGE/runs/v4_intervention_pilot_shard0_retry2"
META="$STAGE/v4_intervention_pilot_v1"

[[ ! -e "$RUN" ]] || { echo "refusing existing $RUN" >&2; exit 1; }
sha256sum "$STAGE"/{QGF_V4_RANDOMIZED_INTERVENTION_PROTOCOL.md,exploration_bulk_collector.py,audit_exploration_bulk.py,dispatch_v4_pilot_shard0_retry2.sh,launch_v4_pilot_shard0_retry2.sh} >"$META/retry2_code.sha256"

timeout --signal=TERM --kill-after=30 7200 srun --jobid=1581551 --overlap --nodes=1 --ntasks=2 \
  --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_v4_pilot_shard0_retry2.sh" >"$META/retry2_srun.log" 2>&1

/public/home/wangsenbao221/.conda/envs/pi05_new/bin/python - <<'PY'
import json
from pathlib import Path

stage = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2')
paths = [stage / 'runs/v4_intervention_pilot_shard0_retry2/audit.json',
         stage / 'runs/v4_intervention_pilot_shard1/audit.json']
rows = [json.loads(path.read_text()) for path in paths]
result = {
    'schema': 'qgf_v4_intervention_pilot_v1_retry2_aggregate',
    'valid': all(row['valid'] for row in rows),
    'episodes': sum((row['episodes'] for row in rows), []),
    'successes': sum(row['successes'] for row in rows),
    'failures': sum(row['failures'] for row in rows),
    'shards': rows,
    'preserved_failed_attempts': ['v4_intervention_pilot_shard0', 'v4_intervention_pilot_shard1/FAILED'],
}
result['admits_bounded_collection'] = (
    result['valid'] and len(result['episodes']) == 4
    and result['successes'] >= 1 and result['failures'] >= 1
)
path = stage / 'v4_intervention_pilot_v1/summary.json'
if path.exists():
    raise FileExistsError(path)
path.write_text(json.dumps(result, indent=2) + '\n')
(path.parent / 'COMPLETE').touch()
print(json.dumps(result))
PY
