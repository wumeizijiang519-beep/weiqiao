#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
P=$C/failure_critical_boundary_v1_remaining_process
mkdir "$P"
date --iso-8601=seconds > "$P/launch_time"
set +e
srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
  --mem=45G --gres=gpu:1 --time=03:46:17 \
  bash "$C/run_failure_critical_remaining_v1.sh" \
  > "$C/failure_critical_boundary_v1_remaining_srun.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$P/exit_code"
date --iso-8601=seconds > "$P/end_time"
exit "$code"
