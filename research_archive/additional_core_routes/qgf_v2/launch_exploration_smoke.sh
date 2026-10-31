#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
NAME="${3:-exploration_smoke_seed202619000_v1}"
START="${4:-202619000}"
STOP="${5:-202619001}"
[[ "$NAME" =~ ^[a-zA-Z0-9_]+$ && "$START" =~ ^[0-9]+$ && "$STOP" =~ ^[0-9]+$ ]]
[[ "$STOP" -gt "$START" && "$((STOP - START))" -le 20 ]]
RUN="$STAGE/runs/$NAME"
mkdir "$RUN"
printf '{"task":"stack_bowls_three","task_config":"demo_randomized","seed_start":%s,"candidate_stop_exclusive":%s,"episodes":1,"behavior":"uniform_random_WAM_N4_training_only","engineering_only":true,"wall_cap_seconds":2700,"gpu_hour_cap":2.25,"new_task_gpu_hour_cap":1.5}\n' "$START" "$STOP" >"$RUN/provenance.json"
sha256sum "$STAGE"/{exploration_contract.py,exploration_collector.py,audit_exploration.py,dispatch_exploration_smoke.sh,launch_exploration_smoke.sh,EXPLORATION_REPLAN_V1.md} "$ROOT/unitas_candidate_server.py" >"$RUN/checksums.sha256"
nohup timeout --signal=TERM --kill-after=30 2700 srun --jobid=1581551 --overlap --nodes=1 --ntasks=2 --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_exploration_smoke.sh" "${1:?fresh gpu4 host}" "${2:?fresh gpu1 host}" "$NAME" "$START" "$STOP" >"$RUN/srun.log" 2>&1 < /dev/null &
echo "$!" >"$RUN/SRUN_PID"
