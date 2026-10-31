#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
RUN="$STAGE/v6_diverse_bank_v1/zero_action_gate_retry3"
PY="$ROOT/envs/unitas_retry6/bin/python"
HOST=127.0.0.1
PORT=18461
mkdir -p "$RUN" "$ROOT/tmp/mpl-v6-gate"
[[ ! -e "$STAGE/v6_diverse_bank_v1/ZERO_ACTION_GATE_COMPLETE" && ! -e "$RUN/FAILED" ]] || exit 1
export PYTHONPATH="$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
export MPLCONFIGDIR="$ROOT/tmp/mpl-v6-gate" OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export NO_PROXY=127.0.0.1,localhost no_proxy=127.0.0.1,localhost
unset HTTP_PROXY HTTPS_PROXY ALL_PROXY http_proxy https_proxy all_proxy
"$PY" -u "$ROOT/unitas_candidate_server.py" --domain robotwin \
  --checkpoint "$ROOT/checkpoints_first_tier/unitas_robotwin_retry2/unitas_robotwin_finetuned.pt" \
  --florence-dir "$ROOT/checkpoints_first_tier/unitas/Florence-2-large" --device cuda:0 \
  --steps 10 --execute-steps 10 --seed 20261022 --host 0.0.0.0 --port "$PORT" >"$RUN/server.log" 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true' EXIT
ready=0
for _ in $(seq 1 120); do
  if curl --noproxy '*' -fsS --max-time 3 "http://$HOST:$PORT/health" >"$RUN/health.json"; then ready=1; break; fi
  kill -0 "$server_pid" 2>/dev/null || { touch "$RUN/FAILED"; exit 1; }
  sleep 5
done
[[ "$ready" == 1 ]] || { touch "$RUN/FAILED"; exit 1; }
source "$STAGE/robotwin_runtime_env.sh"
for index in 1 2 3; do
  seed=$((202625100 + index))
  obs="$RUN/observation$index"
  set +e
  timeout 900 /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python -u "$STAGE/v6_zero_action_probe.py" \
    --probe-output "$obs" --scaler "$STAGE/v6_diverse_bank_v1/action_scaler.npz" \
    --trajectory-dir "$obs/trajectories" --robotwin-root "$ROOT/RoboTwin_fixed" --host "$HOST" --port "$PORT" \
    --task-name open_microwave --task-config demo_randomized --num-episodes 1 --seed "$seed" \
    --candidate-seed-start "$seed" --candidate-seed-stop "$((seed + 20))" --max-candidates-per-episode 20 \
    --save-observation "$obs/input_observation.json" --output-dir "$obs/eval" >"$obs.client.log" 2>&1
  status=$?
  set -e
  printf '%s\n' "$status" >"$obs.client_exit_code.txt"
  [[ -e "$obs/COMPLETE" ]] || { touch "$RUN/FAILED"; exit 1; }
done
"$PY" "$STAGE/summarize_v6_zero_gate.py" >"$RUN/summary.log"
