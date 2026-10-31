#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022; R=$ROOT/ensemble_disagreement_qgf_v1; PROCESS=$R/remaining_v1_process
mkdir "$PROCESS"; date -Is > "$PROCESS/launch_time"; set +e
srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 --mem=45G --gres=gpu:1 --time=03:50:00 timeout 13700 bash "$R/run_remaining.sh" > "$R/remaining_v1_srun.log" 2>&1
code=$?; set -e; echo "$code" > "$PROCESS/exit_code"; date -Is > "$PROCESS/end_time"; exit "$code"
