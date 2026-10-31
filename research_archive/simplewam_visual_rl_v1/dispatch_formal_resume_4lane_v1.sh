#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
JOB=1581551
GATE=$R/formal_wam_compatibility_gpu4_v1

test -f "$GATE/SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_WAM_COMPATIBILITY_PASS"
test "$(squeue -h -j "$JOB" -o %u)" = "wangsenbao221"
INFO=$(scontrol show job "$JOB" -o)
echo "$INFO" | grep -Eq 'JobState=RUNNING'
echo "$INFO" | grep -Eq 'Reason=None'
echo "$INFO" | grep -Eq 'JobName=[^ ]*WAM[^ ]*'
test "$(find "$R/formal_online_execution_v1" -mindepth 2 -maxdepth 2 -type f -name SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE | wc -l)" -eq 12
test -f "$R/formal_online_execution_v1/GPU22_TO_GPU4_TRANSITION_RECEIPT.txt"
test ! -e "$R/formal_online_execution_v1/task_012"

for LANE in 0 1 2 3; do
  FORMAL_GATE_DIR="$GATE" srun --jobid="$JOB" --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=4 --mem=45G \
    bash "$R/run_formal_online_lane.sh" "$LANE" 4 >"$R/formal_gpu4_lane_${LANE}_srun.log" 2>&1 &
  echo $! >"$R/formal_gpu4_lane_${LANE}_launcher.pid"
done
wait

COMPLETE=$(find "$R/formal_online_execution_v1" -mindepth 2 -maxdepth 2 -type f -name SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE | wc -l)
REPORTS=$(find "$R/formal_online_execution_v1" -mindepth 2 -maxdepth 2 -type f -name REPORT.json | wc -l)
FAILED=$(find "$R/formal_online_execution_v1" -mindepth 2 -maxdepth 2 -type f -name FAILED | wc -l)
test "$COMPLETE" -eq 412
test "$REPORTS" -eq 412
test "$FAILED" -eq 0
test ! -e "$R/formal_online_final_v1"
test ! -e "$R/formal_online_final_audit_v1"
"$PY" -u "$R/finalize_formal_online.py" --root "$ROOT" --output "$R/formal_online_final_v1" \
  >"$R/formal_online_final_v1.log" 2>&1
"$PY" -u "$R/audit_formal_online_final.py" --root "$ROOT" --final "$R/formal_online_final_v1" --output "$R/formal_online_final_audit_v1" \
  >"$R/formal_online_final_audit_v1.log" 2>&1
test -f "$R/formal_online_final_audit_v1/SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_AUDIT_PASS"
sha256sum "$R/formal_online_final_v1/REPORT.json" "$R/formal_online_final_audit_v1/REPORT.json" >"$R/FORMAL_ONLINE_FINAL_SHA256SUMS"
