#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
test "$SLURM_JOB_ID" = 1598338
test "$(id -u)" = 2292
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
test "$(nvidia-smi -i 0 --query-gpu=uuid --format=csv,noheader)" = GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
CONTROL=$R/runs/qgf_rl_first_fit_v1_process
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
printf 'job=%s step=%s host=%s physical_gpu=0 uuid=GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" > "$CONTROL/allocation.txt"
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R/qgf_gradient_v1"
export LD_LIBRARY_PATH="$R/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
timeout 1200 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$R/qgf_gradient_v1/train_rl_fold.py" --registration "$1"
