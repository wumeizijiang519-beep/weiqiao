#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
RUN="$ROOT/runs/kairos_intervention_pilot_v1_retry1/shard0"
mkdir -p "$RUN"
nohup srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=16 --gres=gpu:2 timeout 60m \
  env KAIROS_INTERVENTION_RUN="$RUN" KAIROS_INTERVENTION_SHARD=0 KAIROS_SERVER_GPU=0 KAIROS_EVAL_GPU=1 KAIROS_PORT=18017 \
  bash "$ROOT/run_kairos_intervention_pilot_v1.sh" > "$RUN/srun.log" 2>&1 < /dev/null &
printf '%s\n' "$!" | tee "$RUN/SRUN_PID"
