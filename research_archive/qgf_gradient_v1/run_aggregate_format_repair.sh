#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
RUN=$R/qgf_gradient_v1/aggregation_format_repair_v1
test "$SLURM_JOB_ID" = 1593640
mkdir "$RUN"
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$RUN/process_exit_code"
  date -Is > "$RUN/end_time"
}
trap finish EXIT
date -Is > "$RUN/start_time"
printf 'job=%s step=%s host=%s scope=CPU_ONLY_ZERO_GPU\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" > "$RUN/allocation.txt"
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R/qgf_gradient_v1"
export LD_LIBRARY_PATH="$R/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$R/qgf_gradient_v1/aggregate_training_v2_format_repair.py"
