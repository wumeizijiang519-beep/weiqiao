#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
test "$SLURM_JOB_ID" = 1593640
test ! -e "$C/adapter_cpu_v2"
cd "$C"
tr -d '\r' < ADAPTER_CPU_V2_SHA256SUMS | sha256sum -c -
export CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2
timeout 240 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$C/run_adapter_cpu_v2.py"
