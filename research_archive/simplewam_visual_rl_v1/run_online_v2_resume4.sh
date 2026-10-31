#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
JOB=1677369
test -f "$R/wam_compatibility_v1/SIMPLEWAM_VISUAL_QGF_WAM_COMPATIBILITY_PASS"
test -d "$R/online_execution_v2_support_abstention"
for LANE in 0 1 2 3; do
  srun --jobid="$JOB" --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=4 --mem=45G \
    bash "$R/run_online_lane_v2.sh" "$LANE" \
    >"$R/online_v2_resume4_lane_${LANE}_srun.log" 2>&1 &
  echo $! >"$R/online_v2_resume4_lane_${LANE}_launcher.pid"
done
wait
