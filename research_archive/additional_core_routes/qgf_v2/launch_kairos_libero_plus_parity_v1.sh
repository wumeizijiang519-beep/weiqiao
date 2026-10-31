#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
RUN="$ROOT/runs/kairos_libero_plus_parity_v1"
mkdir -p "$RUN"
nohup srun --jobid=1593640 --overlap --exclusive --nodes=1 --ntasks=1 \
  --cpus-per-task=16 --gres=gpu:2 timeout 45m \
  bash "$ROOT/run_kairos_libero_plus_parity_v1.sh" \
  > "$RUN/srun.log" 2>&1 < /dev/null &
printf '%s\n' "$!" | tee "$RUN/SRUN_PID"
