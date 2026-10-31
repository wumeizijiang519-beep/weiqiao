#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
DEV=$1
SEED=$2
OUT=$3
CONTROL=$4
test "$(id -u)" = 2292
test "$(hostname -s)" = gpu22
test "$SLURM_JOB_ID" = 1598338
grep -q /job_1598338/step_extern /proc/self/cgroup
case "$DEV" in
  0) UUID=GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db ;;
  1) UUID=GPU-2efca5c1-71db-641d-deb5-617c3e0f4fed ;;
  *) exit 41 ;;
esac
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
printf 'job=1598338 host=gpu22 physical_gpu=%s uuid=%s seed=%s\n' "$DEV" "$UUID" "$SEED" > "$CONTROL/allocation.txt"
export CUDA_VISIBLE_DEVICES="$UUID" OMP_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
timeout 2400 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$R/action_prefix_pretrain_v1/train.py" --corpus "$R/action_prefix_pretrain_v1/corpus/CORPUS.npz" \
  --output "$OUT" --seed "$SEED" --updates 5000

