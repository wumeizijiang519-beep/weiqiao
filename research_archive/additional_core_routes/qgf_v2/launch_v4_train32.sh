#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
META="$STAGE/v4_intervention_train32_v1"
mkdir -p "$META"

for shard in 0 1 2 3; do
  run="$STAGE/runs/v4_intervention_train32_shard$shard"
  [[ ! -e "$run" ]] || { echo "refusing existing $run" >&2; exit 1; }
done

sha256sum "$STAGE"/{QGF_V4_RANDOMIZED_INTERVENTION_PROTOCOL.md,QGF_V4_RANDOMIZED_TRAIN32_PROTOCOL.md,exploration_bulk_collector.py,audit_exploration_bulk.py,dispatch_v4_train32_pair.sh,launch_v4_train32.sh} >"$META/code.sha256"

set +e
QGF_BASE_SHARD=0 timeout --signal=TERM --kill-after=30 12600 srun --jobid=1581551 --overlap --nodes=1 --ntasks=4 \
  --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_v4_train32_pair.sh" >"$META/gpu4.log" 2>&1 &
p0=$!
QGF_BASE_SHARD=2 timeout --signal=TERM --kill-after=30 12600 srun --jobid=1593640 --overlap --nodes=1 --ntasks=2 \
  --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_v4_train32_pair.sh" >"$META/gpu1.log" 2>&1 &
p1=$!
QGF_BASE_SHARD=3 timeout --signal=TERM --kill-after=30 12600 srun --jobid=1598338 --overlap --nodes=1 --ntasks=2 \
  --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_v4_train32_pair.sh" >"$META/gpu22.log" 2>&1 &
p2=$!

wait "$p0"; s0=$?
wait "$p1"; s1=$?
wait "$p2"; s2=$?
set -e
printf 'gpu4=%s\ngpu1=%s\ngpu22=%s\n' "$s0" "$s1" "$s2" >"$META/srun_exit_codes.txt"

/public/home/wangsenbao221/.conda/envs/pi05_new/bin/python - <<'PY'
import json
from pathlib import Path

stage = Path('/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2')
paths = [stage / f'runs/v4_intervention_train32_shard{i}/audit.json' for i in range(4)]
rows = [json.loads(path.read_text()) for path in paths]
episodes = sum((row['episodes'] for row in rows), [])
result = {
    'schema': 'qgf_v4_randomized_intervention_train32',
    'valid': all(row['valid'] for row in rows) and len(episodes) == 32,
    'episodes': episodes,
    'successes': sum(row['successes'] for row in rows),
    'failures': sum(row['failures'] for row in rows),
    'shards': rows,
}
result['admits_critic_training'] = (
    result['valid'] and result['successes'] >= 6 and result['failures'] >= 6
)
path = stage / 'v4_intervention_train32_v1/summary.json'
if path.exists():
    raise FileExistsError(path)
path.write_text(json.dumps(result, indent=2) + '\n')
(path.parent / 'COMPLETE').touch()
print(json.dumps({k: v for k, v in result.items() if k not in ('episodes', 'shards')}))
PY
