#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE="$ROOT/runtime_anchored_qgf_v1"
PROCESS="$CODE/resume_entry11_v1_process"
test ! -e "$PROCESS"
mkdir "$PROCESS"
date --iso-8601=seconds > "$PROCESS/launch_time"
set +e
srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
  --mem=45G --gres=gpu:1 --time=01:40:00 \
  timeout 6000 bash "$CODE/run_resume_entry11_v1.sh" > "$CODE/resume_entry11_v1_srun.log" 2>&1
code=$?
set -e
printf '%s\n' "$code" > "$PROCESS/exit_code"
date --iso-8601=seconds > "$PROCESS/end_time"
exit "$code"
