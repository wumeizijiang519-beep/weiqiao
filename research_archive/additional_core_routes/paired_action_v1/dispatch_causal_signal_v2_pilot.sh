#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
P=$C/causal_signal_v2_pilot_process
mkdir "$P"
date --iso-8601=seconds > "$P/launch_time"
srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
  --mem=45G --gres=gpu:1 --time=00:30:00 \
  bash "$C/run_causal_signal_v2_pilot.sh" \
  > "$C/causal_signal_v2_pilot_srun.log" 2>&1
code=$?
printf '%s\n' "$code" > "$P/exit_code"
date --iso-8601=seconds > "$P/end_time"
exit "$code"
