#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
PLAN=$CODE/training288_v1
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
mkdir "$PLAN/dispatcher_started"
trap 'rc=$?; printf "%s\n" "$rc" > "$PLAN/dispatcher_exit_code"; date -Is > "$PLAN/dispatcher_end_time"' EXIT
date -Is > "$PLAN/dispatcher_start_time"
for shard in 0 1 2 3; do
  REG=$PLAN/shard$shard.json
  RUN=$ROOT/runs/qgf_gradient_training288_v1_shard$shard
  test ! -e "$RUN"
  date -Is > "$PLAN/shard${shard}_dispatch_time"
  srun --jobid=1593640 --overlap --ntasks=1 --cpus-per-task=8 --gres=gpu:1 --mem=45G --time=04:35:00 bash "$CODE/run_training_shard.sh" "$REG" "$RUN" > "$PLAN/shard${shard}_srun.log" 2>&1
  test "$(cat "$RUN/process_exit_code")" = 0
  # No GPU is held while reading/compressing/decoding the independent evidence.
  srun --jobid=1593640 --overlap --ntasks=1 --cpus-per-task=1 --gres=gpu:0 --mem=4G --time=00:30:00 env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$CODE" LD_LIBRARY_PATH="$ROOT/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$PY" -u "$CODE/audit_collection.py" --run "$RUN" > "$RUN/independent_audit.log" 2>&1
  test -e "$RUN/COLLECTOR_AUDIT_PASS"
  sha256sum "$RUN/report.json" "$RUN/INDEPENDENT_AUDIT.json" "$REG" > "$RUN/SHA256SUMS"
done
touch "$PLAN/ALL_SHARDS_AUDITED"
