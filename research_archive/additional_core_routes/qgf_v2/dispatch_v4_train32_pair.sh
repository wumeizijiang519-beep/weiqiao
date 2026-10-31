#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
BASE_SHARD=${QGF_BASE_SHARD:?QGF_BASE_SHARD is required}
LOCAL_PAIR=$((SLURM_PROCID / 2))
ROLE=$((SLURM_PROCID % 2))
SHARD=$((BASE_SHARD + LOCAL_PAIR))
START=$((202622300 + SHARD * 100))
STOP=$((START + 50))
SELECT=$((202622601 + SHARD))
PORT=$((18401 + SHARD))
RUN="$STAGE/runs/v4_intervention_train32_shard$SHARD"
HOST=$(hostname -s)

mkdir -p "$RUN"
printf '%s\n' "job=$SLURM_JOB_ID step=$SLURM_STEP_ID rank=$SLURM_PROCID devices=$CUDA_VISIBLE_DEVICES shard=$SHARD" >"$RUN/allocation_rank$SLURM_PROCID.txt"

if [[ "$ROLE" == 0 ]]; then
  export PYTHONPATH="$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
  "$ROOT/envs/unitas_retry6/bin/python" -u "$ROOT/unitas_candidate_server.py" --domain robotwin \
    --checkpoint "$ROOT/checkpoints_first_tier/unitas_robotwin_retry2/unitas_robotwin_finetuned.pt" \
    --florence-dir "$ROOT/checkpoints_first_tier/unitas/Florence-2-large" --device cuda:0 \
    --steps 10 --execute-steps 10 --seed 20261022 --host 0.0.0.0 --port "$PORT" >"$RUN/server.log" 2>&1 &
  pid=$!
  trap 'kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true' EXIT
  for _ in $(seq 1 2520); do
    [[ ! -e "$RUN/COLLECTION_COMPLETE" && ! -e "$RUN/FAILED" ]] || exit 0
    kill -0 "$pid" 2>/dev/null || { touch "$RUN/FAILED"; exit 1; }
    sleep 5
  done
  touch "$RUN/FAILED"
  exit 1
fi

source "$STAGE/robotwin_runtime_env.sh"
for _ in $(seq 1 180); do
  if curl -fsS --max-time 3 "http://$HOST:$PORT/health" >"$RUN/server_health.json"; then break; fi
  sleep 5
done
curl -fsS --max-time 3 "http://$HOST:$PORT/health" >/dev/null || { touch "$RUN/FAILED"; exit 1; }

cat >"$RUN/provenance.json" <<EOF
{
  "schema": "qgf_v4_randomized_intervention_train32",
  "task": "open_microwave",
  "task_config": "demo_randomized",
  "seed_start": $START,
  "seed_stop": $STOP,
  "selection_seed": $SELECT,
  "episodes": 8,
  "shard": $SHARD
}
EOF

set +e
timeout 12000 /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python -u "$STAGE/exploration_bulk_collector.py" \
  --exploration-log "$RUN/selection.jsonl" --selection-seed "$SELECT" \
  --trajectory-dir "$RUN/trajectories" --robotwin-root "$ROOT/RoboTwin_fixed" \
  --host "$HOST" --port "$PORT" --task-name open_microwave --task-config demo_randomized \
  --num-episodes 8 --seed "$SELECT" --candidate-seed-start "$START" --candidate-seed-stop "$STOP" \
  --output-dir "$RUN/eval" --max-candidates-per-episode 50 >"$RUN/client.log" 2>&1
status=$?
set -e
echo "$status" >"$RUN/client_exit_code.txt"

if /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python "$STAGE/audit_exploration_bulk.py" --run "$RUN" --episodes 8; then
  if [[ "$status" != 0 ]]; then touch "$RUN/POST_SUCCESS_TEARDOWN_NONZERO"; fi
  exit 0
fi
touch "$RUN/FAILED"
exit 1
