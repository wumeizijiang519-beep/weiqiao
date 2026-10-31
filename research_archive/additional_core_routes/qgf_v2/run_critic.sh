#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
export XDG_CACHE_HOME="$ROOT/qgf_v2/cache"
export CUDA_CACHE_PATH="$ROOT/qgf_v2/cache/cuda"
export TRITON_CACHE_DIR="$ROOT/qgf_v2/cache/triton"
export MPLCONFIGDIR="$ROOT/qgf_v2/cache/matplotlib"
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
mkdir -p "$XDG_CACHE_HOME" "$CUDA_CACHE_PATH" "$TRITON_CACHE_DIR" "$MPLCONFIGDIR"
exec "$ROOT/envs/unitas_retry6/bin/python" -u "$ROOT/qgf_v2/train_critic.py" "$@"
