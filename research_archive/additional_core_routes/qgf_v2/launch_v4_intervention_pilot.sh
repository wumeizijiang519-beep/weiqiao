#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
for pair in 0 1; do
  run="$STAGE/runs/v4_intervention_pilot_shard$pair"
  [[ ! -e "$run" ]] || { echo "refusing existing $run" >&2; exit 1; }
done
mkdir -p "$STAGE/v4_intervention_pilot_v1"
sha256sum "$STAGE"/{QGF_V4_RANDOMIZED_INTERVENTION_PROTOCOL.md,exploration_bulk_collector.py,audit_exploration_bulk.py,dispatch_v4_pilot_pair.sh,launch_v4_intervention_pilot.sh} >"$STAGE/v4_intervention_pilot_v1/code.sha256"
timeout --signal=TERM --kill-after=30 7200 srun --jobid=1581551 --overlap --nodes=1 --ntasks=4 \
  --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_v4_pilot_pair.sh" >"$STAGE/v4_intervention_pilot_v1/srun.log" 2>&1
/public/home/wangsenbao221/.conda/envs/pi05_new/bin/python - <<'PY'
import json
from pathlib import Path
root=Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2')
rows=[json.loads((root/'runs'/f'v4_intervention_pilot_shard{i}'/'audit.json').read_text()) for i in range(2)]
result={'schema':'qgf_v4_intervention_pilot_v1','valid':all(r['valid'] for r in rows),
        'episodes':sum((r['episodes'] for r in rows), []),
        'successes':sum(r['successes'] for r in rows),'failures':sum(r['failures'] for r in rows),
        'shards':rows}
result['admits_bounded_collection']=result['valid'] and result['successes']>=1 and result['failures']>=1
path=root/'v4_intervention_pilot_v1'/'summary.json'
path.write_text(json.dumps(result,indent=2)+'\n')
(path.parent/'COMPLETE').touch()
print(json.dumps(result))
PY
