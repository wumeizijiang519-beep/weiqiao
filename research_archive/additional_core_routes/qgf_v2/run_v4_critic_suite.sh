#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
SUITE="$STAGE/v4_critic_v1"
JOB_ID="${1:?Slurm job id required}"
mkdir -p "$SUITE/logs" "$SUITE/training"
sha256sum "$STAGE/QGF_V4_CRITIC_PROTOCOL.md" "$STAGE/prepare_v4_critic_data.py" \
  "$STAGE/train_v4_critic.py" "$STAGE/v4_worker.py" > "$SUITE/code.sha256"
"$ROOT/envs/unitas_retry6/bin/python" "$STAGE/prepare_v4_critic_data.py" --stage "$STAGE" \
  > "$SUITE/prepare.log" 2>&1
timeout --signal=TERM --kill-after=30 3600 \
  srun --jobid="$JOB_ID" --overlap --nodes=1 --ntasks=4 --gpus-per-task=1 \
  --cpus-per-task=4 --gpu-bind=single:1 --kill-on-bad-exit=1 bash -lc \
  'export XDG_CACHE_HOME=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/cache CUDA_CACHE_PATH=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/cache/cuda TRITON_CACHE_DIR=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2/cache/triton PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4; cd /public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2; /public/wangsenbao221/pqr/qgf_mainstream_20261022/envs/unitas_retry6/bin/python v4_worker.py' \
  > "$SUITE/worker.log" 2>&1

