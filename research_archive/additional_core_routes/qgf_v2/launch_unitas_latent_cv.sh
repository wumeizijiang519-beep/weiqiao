#!/usr/bin/env bash
set -euo pipefail
STAGE=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2
SUITE=$STAGE/unitas_latent_cv_v1
mkdir -p "$SUITE/logs" "$SUITE/training"
srun --jobid=1581551 --overlap --nodes=1 --ntasks=4 --gpus-per-task=1 --cpus-per-task=4 \
  --gpu-bind=single:1 --kill-on-bad-exit=1 bash -lc \
  'export XDG_CACHE_HOME=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/cache CUDA_CACHE_PATH=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/cache/cuda TRITON_CACHE_DIR=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/cache/triton PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4; cd /public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2; /public/wangsenbao221/pqr/qgf_mainstream_20261022/envs/unitas_retry6/bin/python v3_worker.py' \
  >"$SUITE/worker.log" 2>&1
"/public/wangsenbao221/pqr/qgf_mainstream_20261022/envs/unitas_retry6/bin/python" "$STAGE/summarize_unitas_latent_cv.py" | tee "$SUITE/summary.log"
