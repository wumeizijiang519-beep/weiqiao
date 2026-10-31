#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
JOB=${1:?new explicit WAM job id required}
case "$JOB" in
  1581551|1598338) ;;
  *) test "$JOB" -gt 1677369 ;;
esac
test -f "$R/final_critic_deployment_independent_audit_v1/SIMPLEWAM_VISUAL_QGF_FINAL_CRITIC_DEPLOYMENT_AUDIT_PASS"
INFO=$(scontrol show job "$JOB" -o)
test "$(squeue -h -j "$JOB" -o %u)" = "wangsenbao221"
echo "$INFO" | grep -Eq 'JobState=RUNNING'
echo "$INFO" | grep -Eq 'Reason=None'
if test "$JOB" != 1598338; then
  echo "$INFO" | grep -Eq 'JobName=[^ ]*WAM[^ ]*'
fi
GPUS=$(echo "$INFO" | tr ' ' '\n' | sed -n 's/^TRES=.*gres\/gpu=\([0-9][0-9]*\).*/\1/p')
test -n "$GPUS" -a "$GPUS" -ge 1
LANES=$GPUS
if test "$LANES" -gt 4; then LANES=4; fi
if test "$JOB" = 1598338; then LANES=1; fi
test ! -e "$R/formal_wam_compatibility_v1"
test ! -e "$R/formal_online_execution_v1"
printf '%s\n' "$JOB" >"$R/formal_authorized_wam_job_id"
printf '%s\n' "$INFO" >"$R/formal_authorized_wam_job_scontrol.txt"
set +e
FORMAL_WAM_JOB_ID=$JOB srun --jobid="$JOB" --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=8 --mem=45G \
  bash "$R/run_formal_wam_compatibility_gate.sh" >"$R/formal_wam_compatibility_srun.log" 2>&1
CODE=$?
set -e
printf '%s\n' "$CODE" >"$R/formal_wam_compatibility_exit_code"
test "$CODE" -eq 0
test -f "$R/formal_wam_compatibility_v1/SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_WAM_COMPATIBILITY_PASS"
for LANE in $(seq 0 $((LANES - 1))); do
  FORMAL_GATE_DIR="$R/formal_wam_compatibility_v1" srun --jobid="$JOB" --exclusive -N1 -n1 --gres=gpu:1 --cpus-per-task=8 --mem=45G \
    bash "$R/run_formal_online_lane.sh" "$LANE" "$LANES" >"$R/formal_lane_${LANE}_srun.log" 2>&1 &
  echo $! >"$R/formal_lane_${LANE}_launcher.pid"
done
wait
COMPLETE=$(find "$R/formal_online_execution_v1" -mindepth 2 -maxdepth 2 -type f -name SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE | wc -l)
REPORTS=$(find "$R/formal_online_execution_v1" -mindepth 2 -maxdepth 2 -type f -name REPORT.json | wc -l)
test "$COMPLETE" -eq 412
test "$REPORTS" -eq 412
test ! -e "$R/formal_online_final_v1"
test ! -e "$R/formal_online_final_audit_v1"
"$PY" -u "$R/finalize_formal_online.py" --root "$ROOT" --output "$R/formal_online_final_v1" \
  >"$R/formal_online_final_v1.log" 2>&1
"$PY" -u "$R/audit_formal_online_final.py" --root "$ROOT" --final "$R/formal_online_final_v1" --output "$R/formal_online_final_audit_v1" \
  >"$R/formal_online_final_audit_v1.log" 2>&1
test -f "$R/formal_online_final_audit_v1/SIMPLEWAM_VISUAL_QGF_FINAL_FORMAL_AUDIT_PASS"
sha256sum "$R/formal_online_final_v1/REPORT.json" "$R/formal_online_final_audit_v1/REPORT.json" >"$R/FORMAL_ONLINE_FINAL_SHA256SUMS"
