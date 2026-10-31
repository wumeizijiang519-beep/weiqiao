#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/progress_pairwise_qgf_v1
P=$C/pilot_v1_process
mkdir "$P"
date --iso-8601=seconds > "$P/launch_time"
set +e
srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
  --mem=45G --gres=gpu:1 --time=00:30:00 \
  bash "$C/run_pilot.sh" > "$C/pilot_v1_srun.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$P/exit_code"
date --iso-8601=seconds > "$P/end_time"
exit "$code"
