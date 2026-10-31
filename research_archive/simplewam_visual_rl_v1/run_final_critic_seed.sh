#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
SEED=${1:?seed required}
R="$ROOT/simplewam_visual_rl_v1"
REG="$R/final_critic_registrations_v1/seed_${SEED}.json"
OUT="$R/final_critic_execution_v1/seed_${SEED}"
LOG="$R/final_critic_execution_v1/seed_${SEED}.log"
test -f "$R/final_critic_source_audit_v1/SIMPLEWAM_VISUAL_IQL_FINAL_SOURCE_AUDIT_PASS"
test ! -e "$OUT"
mkdir -p "$R/final_critic_execution_v1"
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$R${PYTHONPATH:+:$PYTHONPATH}"
"$ROOT/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$R/train_visual_iql_final.py" --registration "$REG" --output "$OUT" \
  >"$LOG" 2>&1

