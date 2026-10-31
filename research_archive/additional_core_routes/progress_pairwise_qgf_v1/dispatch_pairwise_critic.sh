#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022/progress_pairwise_qgf_v1
PY=/public/wangsenbao221/pqr/qgf_mainstream_20261022/runtime/simplewam_inference_py310_v2/bin/python
REG="$ROOT/pairwise_critic_execution_v1/registrations"
RUNS="$ROOT/pairwise_critic_execution_v1/runs"
mkdir -p "$RUNS"

mapfile -t JOBS < <(find "$REG" -name '*.json' -type f | sort)
if [[ ${#JOBS[@]} -ne 12 ]]; then
  echo "Expected12 frozen workers" >&2
  exit 2
fi

worker() {
  local gpu=$1
  shift
  for registration in "$@"; do
    local stem
    stem=$(basename "$registration" .json)
    CUDA_VISIBLE_DEVICES="$gpu" timeout 900 "$PY" "$ROOT/train_pairwise_fold.py" \
      --registration "$registration" >"$RUNS/${stem}.log" 2>&1
    echo "$stem" >>"$RUNS/COMPLETED_WORKERS"
  done
}

left=(); right=()
for index in "${!JOBS[@]}"; do
  if (( index % 2 == 0 )); then left+=("${JOBS[$index]}"); else right+=("${JOBS[$index]}"); fi
done
worker 0 "${left[@]}" & p0=$!
worker 1 "${right[@]}" & p1=$!
wait "$p0"
wait "$p1"
touch "$RUNS/ALL_WORKERS_RETURNED"
