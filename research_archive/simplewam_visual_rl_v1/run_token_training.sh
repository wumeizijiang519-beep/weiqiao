#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
RUN="$ROOT/simplewam_visual_rl_v1/token_training_v1"
LOG="$ROOT/simplewam_visual_rl_v1/token_training_v1.log"

test ! -e "$RUN"
export PYTHONPATH="$ROOT/simplewam_visual_rl_v1${PYTHONPATH:+:$PYTHONPATH}"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export CUDA_VISIBLE_DEVICES=0

cd "$ROOT"
runtime/simplewam_inference_py310_v2/bin/python -u \
  simplewam_visual_rl_v1/train_token.py \
  --registration simplewam_visual_rl_v1/TOKEN_TRAINING_REGISTRATION.json \
  --output "$RUN" >"$LOG" 2>&1
