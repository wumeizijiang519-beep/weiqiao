#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
LANE=${1:?lane required}
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$ROOT/simplewam_visual_rl_v1${PYTHONPATH:+:$PYTHONPATH}"
mapfile -t WORKERS < <(find "$ROOT/simplewam_visual_rl_v1/iql_registrations_v1" -maxdepth 1 -name 'seed_*_fold_*.json' | sort)
for INDEX in "${!WORKERS[@]}"; do
  if (( INDEX % 2 != LANE )); then continue; fi
  REG=${WORKERS[$INDEX]}
  NAME=$(basename "$REG" .json)
  OUT="$ROOT/simplewam_visual_rl_v1/iql_execution_v1/$NAME"
  LOG="$ROOT/simplewam_visual_rl_v1/iql_execution_v1/${NAME}.log"
  test ! -e "$OUT"
  "$ROOT/runtime/simplewam_inference_py310_v2/bin/python" -u \
    "$ROOT/simplewam_visual_rl_v1/train_visual_iql_fold.py" \
    --registration "$REG" --output "$OUT" >"$LOG" 2>&1
done
