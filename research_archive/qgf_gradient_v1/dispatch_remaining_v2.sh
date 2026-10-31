#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
PLAN=$CODE/training288_v2_remaining
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
test -e "$ROOT/runs/qgf_gradient_resume_v2_one/RESUME_AUDIT_PASS"
mkdir "$PLAN/dispatcher_started"
trap 'rc=$?; printf "%s\n" "$rc" > "$PLAN/dispatcher_exit_code"; date -Is > "$PLAN/dispatcher_end_time"' EXIT
date -Is > "$PLAN/dispatcher_start_time"
for shard in 0 1 2 3; do
  REG=$PLAN/shard$shard.json
  RUN=$ROOT/runs/qgf_gradient_remaining257_v2_shard$shard
  test ! -e "$RUN"
  srun --jobid=1593640 --overlap --ntasks=1 --cpus-per-task=8 --gres=gpu:1 --mem=45G --time=04:20:00 bash "$CODE/run_remaining_shard_v2.sh" "$REG" "$RUN" > "$PLAN/shard${shard}_srun.log" 2>&1
  test "$(cat "$RUN/process_exit_code")" = 0
  srun --jobid=1593640 --overlap --ntasks=1 --cpus-per-task=1 --gres=gpu:0 --mem=4G --time=00:30:00 env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$CODE" LD_LIBRARY_PATH="$ROOT/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "$PY" -u "$CODE/audit_collection_v2.py" --run "$RUN" > "$RUN/independent_audit.log" 2>&1
  test -e "$RUN/COLLECTOR_AUDIT_PASS"
  sha256sum "$RUN/report.json" "$RUN/INDEPENDENT_AUDIT.json" "$REG" > "$RUN/SHA256SUMS"
done
touch "$PLAN/ALL_SHARDS_AUDITED"
