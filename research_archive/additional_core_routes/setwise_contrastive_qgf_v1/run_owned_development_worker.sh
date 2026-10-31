#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
HOST=$1
JOB=$2
DEV=$3
UUID=$4
REG=$5
CONTROL=$6
LOG=$7
test "$(id -u)" = 2292
test "$(hostname -s)" = "$HOST"
test "$SLURM_JOB_ID" = "$JOB"
grep -q "/job_${JOB}/step_extern" /proc/self/cgroup
test "$(nvidia-smi -i "$DEV" --query-gpu=uuid --format=csv,noheader)" = "$UUID"
test -z "$(nvidia-smi -i "$DEV" --query-compute-apps=pid --format=csv,noheader)"
mkdir "$CONTROL"
START=$(date +%s)
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$CONTROL/process_exit_code"
  printf '%s\n' "$(($(date +%s)-START))" > "$CONTROL/charged_gpu_seconds"
  date -Is > "$CONTROL/end_time"
}
trap finish EXIT
date -Is > "$CONTROL/start_time"
cat /proc/self/cgroup > "$CONTROL/cgroup.txt"
printf 'job=%s host=%s physical_gpu=%s uuid=%s registration=%s\n' "$JOB" "$HOST" "$DEV" "$UUID" "$REG" > "$CONTROL/allocation.txt"
export CUDA_VISIBLE_DEVICES="$UUID" OMP_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
timeout 900 "$ROOT/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$ROOT/setwise_contrastive_qgf_v1/train_development_fold.py" --registration "$REG" > "$LOG" 2>&1
