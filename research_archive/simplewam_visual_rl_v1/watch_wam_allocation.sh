#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
JOB=1677369
while true; do
  STATE=$(squeue -h -j "$JOB" -o %T || true)
  case "$STATE" in
    RUNNING) break ;;
    PENDING|CONFIGURING) sleep 60 ;;
    "") echo "job $JOB disappeared before compatibility gate" >&2; exit 2 ;;
    *) echo "job $JOB entered unexpected state $STATE" >&2; exit 3 ;;
  esac
done
test ! -e "$R/wam_compatibility_v1"
# The Sothis allocation reports RUNNING while its container image may still be
# extracting. Wait until the batch prolog has no active pull before creating a
# scientific step, otherwise Slurm can strand a pre-prolog step.
while ! scontrol show job "$JOB" -o | grep -q 'JobState=RUNNING Reason=None'; do sleep 30; done
set +e
srun --jobid="$JOB" --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=8 --mem=45G \
  bash "$R/run_wam_compatibility_gate.sh" \
  >"$R/wam_compatibility_srun.log" 2>&1
CODE=$?
set -e
printf '%s\n' "$CODE" >"$R/wam_compatibility_exit_code"
if test "$CODE" -ne 0; then exit "$CODE"; fi
for LANE in 0 1 2 3; do
  srun --jobid="$JOB" --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=4 --mem=45G \
    bash "$R/run_online_lane.sh" "$LANE" \
    >"$R/online_lane_${LANE}_srun.log" 2>&1 &
  echo $! >"$R/online_lane_${LANE}_launcher.pid"
done
wait
