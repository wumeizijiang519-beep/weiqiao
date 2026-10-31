#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
test "$SLURM_JOB_ID" = 1593640
printf 'job=%s step=%s host=%s scope=ZERO_GPU_INDEPENDENT_OOF\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)"
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R/qgf_gradient_v1"
exec "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$R/qgf_gradient_v1/qualify_rl_oof.py" --registration "$1"
