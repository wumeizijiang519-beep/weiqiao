#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
RUN="$STAGE/runs/exploration_smoke_matched_seed202619100_retry3"
mkdir "$RUN"
printf '%s\n' '{"task":"stack_bowls_three","task_config":"demo_randomized","seed_start":202619100,"candidate_stop_exclusive":202619101,"episodes":1,"engineering_only":true,"behavior":"uniform_random_WAM_N4_training_only","native_reference":"fresh_same_node_original_entrypoint","wall_cap_seconds":2700,"gpu_hour_cap":2.25}' >"$RUN/provenance.json"
sha256sum "$STAGE"/{dispatch_parity_probe.sh,exploration_collector.py,audit_exploration.py,robotwin_runtime_env.sh,launch_exploration_matched.sh,MATCHED_REFERENCE_RETRY3.md} >"$RUN/checksums.sha256"
nohup timeout --signal=TERM --kill-after=30 2700 srun --jobid=1581551 --overlap --nodes=1 --ntasks=3 --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  bash "$STAGE/dispatch_parity_probe.sh" "${1:?fresh gpu4 host}" "${2:?legacy host for provenance}" matched_rollout >"$RUN/srun.log" 2>&1 < /dev/null &
echo "$!" >"$RUN/SRUN_PID"
