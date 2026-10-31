#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
RUN="$STAGE/runs/exploration_parity_probe_seed202619100_v1"
mkdir "$RUN"
printf '%s\n' '{"task":"stack_bowls_three","task_config":"demo_randomized","seed":202619100,"engineering_only":true,"executed_policy_action_cap":0,"wall_cap_seconds":1200,"new_task_gpu_hour_cap":1,"conservative_gpu_hour_cap":1.34}' >"$RUN/provenance.json"
sha256sum "$STAGE"/{parity_probe_collector.py,dispatch_parity_probe.sh,robotwin_runtime_env.sh,launch_parity_probe.sh,PARITY_PROBE_V1.md} "$ROOT/unitas_candidate_server.py" >"$RUN/checksums.sha256"
nohup timeout --signal=TERM --kill-after=30 1200 srun --jobid=1581551 --overlap --nodes=1 --ntasks=3 --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_parity_probe.sh" "${1:?fresh gpu4 host}" "${2:?fresh gpu1 host}" >"$RUN/srun.log" 2>&1 < /dev/null &
echo "$!" >"$RUN/SRUN_PID"
