#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
HOST="${1:?dynamic server host required}"
PORT="${2:?server port required}"
SEED="${3:?scene seed required}"
COUNT="${4:?episode count required}"
NAME="${5:?new run name required}"
[[ "$SEED" =~ ^[0-9]+$ && "$COUNT" =~ ^(1|10)$ && "$NAME" =~ ^[a-zA-Z0-9_]+$ ]]
OUT="$ROOT/qgf_v2/runs/$NAME"
if [[ -e "$OUT/provenance.json" ]]; then exit 2; fi
mkdir -p "$OUT"
exec >"$OUT/launcher.log" 2>&1
SITE="$ROOT/envs/robotwin_py310_site"
TOOLCHAIN="$ROOT/toolchains/gcc11"
export PYTHONPATH="$ROOT/robotwin_host_compat:$ROOT/envs/warp_host_compat:$ROOT/deps/curobo-0.7.8/src:$SITE:$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
export CUDA_HOME=/usr/local/cuda-12.2
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export PATH="$TOOLCHAIN/bin:$CUDA_HOME/bin:$SITE/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib:$CUDA_HOME/lib64:$SITE/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
export TORCH_EXTENSIONS_DIR="$ROOT/envs/torch_extensions_curobo078_host_gcc11"
export CPATH=/public/home/wangsenbao221/.conda/envs/pi05_new/include/python3.10
export CPLUS_INCLUDE_PATH="$CPATH"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
printf '{"task":"stack_bowls_three","task_config":"demo_randomized","seed_start":%s,"episodes":%s}\n' "$SEED" "$COUNT" >"$OUT/provenance.json"
sha256sum "$0" "$ROOT/qgf_v2/trajectory_collector.py" >"$OUT/checksums.sha256"
PYTHON=/public/home/wangsenbao221/.conda/envs/pi05_new/bin/python
curl --fail --max-time 10 -s "http://$HOST:$PORT/health" >"$OUT/server_health.json"
"$PYTHON" -c 'import json,sys; p=json.load(open(sys.argv[1])); c=p["protocol"]; assert p["status"]=="ok" and p["domain"]=="robotwin"; assert c["checkpoint_sha256"]=="886711f01a3a48b27999939cc92e34ba5005f680f03de0e62468325fed874e48"; assert c["execute_steps"]==10 and c["denoise_steps"]==10 and c["sampling_seed"]==20261022' "$OUT/server_health.json"
printf '%s\n' "job=${SLURM_JOB_ID:-unset} step=${SLURM_STEP_ID:-unset} rank=${SLURM_PROCID:-unset} devices=${CUDA_VISIBLE_DEVICES:-unset} server=$HOST:$PORT" >"$OUT/allocation.txt"
LIMIT=10800
MAX_CANDIDATES=1000
if [[ "$COUNT" == 1 ]]; then LIMIT=900; MAX_CANDIDATES=1; fi
set +e
timeout "$LIMIT" "$PYTHON" -u "$ROOT/qgf_v2/trajectory_collector.py" \
  --trajectory-dir "$OUT/trajectories" --robotwin-root "$ROOT/RoboTwin_fixed" \
  --host "$HOST" --port "$PORT" --task-name stack_bowls_three \
  --task-config demo_randomized --num-episodes "$COUNT" --seed 20261023 \
  --candidate-seed-start "$SEED" --output-dir "$OUT/eval" \
  --candidate-seed-stop "$((SEED + 100))" \
  --max-candidates-per-episode "$MAX_CANDIDATES"
STATUS=$?
set -e
printf '%s\n' "$STATUS" >"$OUT/client_exit_code.txt"
if ! "$PYTHON" "$ROOT/qgf_v2/validate_transitions.py" --runs "$OUT" --output "$OUT/audit.json"; then
  touch "$OUT/FAILED"
  exit 1
fi
touch "$OUT/COLLECTION_COMPLETE"
