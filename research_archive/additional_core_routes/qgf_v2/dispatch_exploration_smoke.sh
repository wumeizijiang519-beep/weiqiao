#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
RUN="$STAGE/runs/${3:-exploration_smoke_seed202619000_v1}"
START="${4:-202619000}"
STOP="${5:-202619001}"
SCENES="$((STOP - START))"
HOST="${1:?fresh gpu4 host required}"
NATIVE="${2:?fresh native gpu1 host required}"
printf '%s\n' "job=$SLURM_JOB_ID step=$SLURM_STEP_ID rank=$SLURM_PROCID devices=$CUDA_VISIBLE_DEVICES" >"$RUN/allocation_rank${SLURM_PROCID}.txt"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export MPLCONFIGDIR="$ROOT/tmp/mpl-exploration" XDG_CACHE_HOME="$STAGE/cache"
mkdir -p "$MPLCONFIGDIR"
if [[ "$SLURM_PROCID" == 0 ]]; then
  export PYTHONPATH="$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
  "$ROOT/envs/unitas_retry6/bin/python" -u "$ROOT/unitas_candidate_server.py" \
    --domain robotwin --checkpoint "$ROOT/checkpoints_first_tier/unitas_robotwin_retry2/unitas_robotwin_finetuned.pt" \
    --florence-dir "$ROOT/checkpoints_first_tier/unitas/Florence-2-large" \
    --device cuda:0 --steps 10 --execute-steps 10 --seed 20261022 --host 0.0.0.0 --port 18341 >"$RUN/server.log" 2>&1 &
  server_pid=$!
  trap 'kill "$server_pid" 2>/dev/null || true; wait "$server_pid" 2>/dev/null || true' EXIT
  for _ in $(seq 1 540); do
    if [[ -e "$RUN/COLLECTION_COMPLETE" || -e "$RUN/FAILED" ]]; then exit 0; fi
    if ! kill -0 "$server_pid" 2>/dev/null; then touch "$RUN/FAILED"; exit 1; fi
    sleep 5
  done
  touch "$RUN/FAILED"
  exit 1
fi
[[ "$SLURM_PROCID" == 1 ]]
exec >"$RUN/launcher.log" 2>&1
SITE="$ROOT/envs/robotwin_py310_site"
TOOLCHAIN="$ROOT/toolchains/gcc11"
export PYTHONPATH="$ROOT/robotwin_host_compat:$ROOT/envs/warp_host_compat:$ROOT/deps/curobo-0.7.8/src:$SITE:$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
export CUDA_HOME=/usr/local/cuda-12.2
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export PATH="$TOOLCHAIN/bin:$CUDA_HOME/bin:$SITE/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib:$CUDA_HOME/lib64:$SITE/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
export TORCH_EXTENSIONS_DIR="$ROOT/envs/torch_extensions_curobo078_host_gcc11"
export CPATH=/public/home/wangsenbao221/.conda/envs/pi05_new/include/python3.10
export CPLUS_INCLUDE_PATH="$CPATH"
PYTHON=/public/home/wangsenbao221/.conda/envs/pi05_new/bin/python
ready=0
for _ in $(seq 1 120); do
  if [[ -e "$RUN/FAILED" ]]; then exit 1; fi
  if curl -fsS --max-time 3 "http://$HOST:18341/health" >"$RUN/server_health.json"; then ready=1; break; fi
  sleep 5
done
if [[ "$ready" != 1 ]]; then touch "$RUN/FAILED"; exit 1; fi
"$PYTHON" -c 'import json,sys; p=json.load(open(sys.argv[1]))["protocol"]; assert p["candidate_endpoint"] and p["candidate_zero_is_baseline"]; assert p["checkpoint_sha256"]=="886711f01a3a48b27999939cc92e34ba5005f680f03de0e62468325fed874e48"; assert p["execute_steps"]==10 and p["denoise_steps"]==10 and p["sampling_seed"]==20261022' "$RUN/server_health.json" || { touch "$RUN/FAILED"; exit 1; }
set +e
timeout 2100 "$PYTHON" -u "$STAGE/exploration_collector.py" \
  --exploration-log "$RUN/selection.jsonl" --selection-seed 202619001 --native-host "$NATIVE" --native-port 18231 \
  --trajectory-dir "$RUN/trajectories" --robotwin-root "$ROOT/RoboTwin_fixed" \
  --host "$HOST" --port 18341 --task-name stack_bowls_three --task-config demo_randomized \
  --num-episodes 1 --seed 20261023 --candidate-seed-start "$START" --candidate-seed-stop "$STOP" \
  --output-dir "$RUN/eval" --max-candidates-per-episode "$SCENES"
status=$?
set -e
printf '%s\n' "$status" >"$RUN/client_exit_code.txt"
if "$PYTHON" "$STAGE/audit_exploration.py" --run "$RUN"; then
  touch "$RUN/COLLECTION_COMPLETE"
else
  touch "$RUN/FAILED"
  exit 1
fi
