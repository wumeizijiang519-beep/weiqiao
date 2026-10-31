#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
MODE="${3:-probe}"
RUN="$STAGE/runs/exploration_parity_probe_seed202619100_v1"
LOOPS=240
if [[ "$MODE" == matched_rollout ]]; then
  RUN="$STAGE/runs/exploration_smoke_matched_seed202619100_retry3"
  LOOPS=540
fi
HOST="${1:?fresh gpu4 host}"
LEGACY="${2:?fresh legacy gpu1 host}"
RANK="${SLURM_PROCID:?Slurm task required}"
printf '%s\n' "job=$SLURM_JOB_ID step=$SLURM_STEP_ID rank=$RANK devices=$CUDA_VISIBLE_DEVICES" >"$RUN/allocation_rank$RANK.txt"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export MPLCONFIGDIR="$ROOT/tmp/mpl-parity-probe" XDG_CACHE_HOME="$STAGE/cache"
mkdir -p "$MPLCONFIGDIR"
if [[ "$RANK" -lt 2 ]]; then
  export PYTHONPATH="$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
  ENTRY="$ROOT/unitas_candidate_server.py"
  PORT=18341
  if [[ "$RANK" == 1 ]]; then ENTRY="$ROOT/backbones/UNITAS/src/unitas/inference/server.py"; PORT=18342; fi
  "$ROOT/envs/unitas_retry6/bin/python" -u "$ENTRY" --domain robotwin \
    --checkpoint "$ROOT/checkpoints_first_tier/unitas_robotwin_retry2/unitas_robotwin_finetuned.pt" \
    --florence-dir "$ROOT/checkpoints_first_tier/unitas/Florence-2-large" --device cuda:0 \
    --steps 10 --execute-steps 10 --seed 20261022 --host 0.0.0.0 --port "$PORT" >"$RUN/server_rank$RANK.log" 2>&1 &
  pid=$!
  trap 'kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT
  for _ in $(seq 1 "$LOOPS"); do
    [[ ! -e "$RUN/PARITY_PROBE_COMPLETE" && ! -e "$RUN/COLLECTION_COMPLETE" && ! -e "$RUN/FAILED" ]] || exit 0
    if ! kill -0 "$pid" 2>/dev/null; then touch "$RUN/FAILED"; exit 1; fi
    sleep 5
  done
  touch "$RUN/FAILED"; exit 1
fi
[[ "$RANK" == 2 ]]
exec >"$RUN/probe_client.log" 2>&1
source "$STAGE/robotwin_runtime_env.sh"
ready=0
for _ in $(seq 1 120); do
  [[ ! -e "$RUN/FAILED" ]] || exit 1
  if curl -fsS --max-time 3 "http://$HOST:18341/health" >"$RUN/candidate_health.json" && curl -fsS --max-time 3 "http://$HOST:18342/health" >"$RUN/native_health.json"; then ready=1; break; fi
  sleep 5
done
[[ "$ready" == 1 ]] || { touch "$RUN/FAILED"; exit 1; }
if [[ "$MODE" == matched_rollout ]]; then
  set +e
  timeout 2100 /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python -u "$STAGE/exploration_collector.py" \
    --exploration-log "$RUN/selection.jsonl" --selection-seed 202619001 --native-host "$HOST" --native-port 18342 \
    --trajectory-dir "$RUN/trajectories" --robotwin-root "$ROOT/RoboTwin_fixed" --host "$HOST" --port 18341 \
    --task-name stack_bowls_three --task-config demo_randomized --num-episodes 1 --seed 20261023 \
    --candidate-seed-start 202619100 --candidate-seed-stop 202619101 --max-candidates-per-episode 1 \
    --save-observation "$RUN/input_observation.json" --output-dir "$RUN/eval"
  status=$?
  set -e
  echo "$status" >"$RUN/client_exit_code.txt"
  if /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python "$STAGE/audit_exploration.py" --run "$RUN"; then
    touch "$RUN/COLLECTION_COMPLETE"; exit 0
  else
    touch "$RUN/FAILED"; exit 1
  fi
fi
set +e
timeout 540 /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python -u "$STAGE/parity_probe_collector.py" \
  --probe-output "$RUN" --fresh-host "$HOST" --legacy-host "$LEGACY" \
  --trajectory-dir "$RUN/trajectories" --robotwin-root "$ROOT/RoboTwin_fixed" --host "$HOST" --port 18341 \
  --task-name stack_bowls_three --task-config demo_randomized --num-episodes 1 --seed 20261023 \
  --candidate-seed-start 202619100 --candidate-seed-stop 202619101 --max-candidates-per-episode 1 \
  --save-observation "$RUN/input_observation.json" --output-dir "$RUN/eval"
status=$?
set -e
echo "$status" >"$RUN/client_exit_code.txt"
[[ -e "$RUN/PARITY_PROBE_COMPLETE" ]] || { touch "$RUN/FAILED"; exit 1; }
