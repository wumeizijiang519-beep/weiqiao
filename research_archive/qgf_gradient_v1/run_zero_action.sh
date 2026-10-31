#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
CODE=$ROOT/qgf_gradient_v1
RUN=$ROOT/runs/qgf_gradient_zero_action_v1_retry2
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
mkdir "$RUN"
export QGF_RUN=$RUN
finish() {
  code=$?
  printf '%s\n' "$code" > "$RUN/process_exit_code"
  date -Is > "$RUN/end_time"
  if [ "$code" -eq 0 ]; then touch "$RUN/PROCESS_COMPLETE"; else touch "$RUN/PROCESS_FAILED"; fi
}
trap finish EXIT
date -Is > "$RUN/start_time"
printf 'job=%s step=%s host=%s visible=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES" > "$RUN/allocation.txt"
# This launch is frozen for the dynamically verified job1593640 / GPU0 only.
test "$SLURM_JOB_ID" = 1593640
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
if [ -n "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)" ]; then
  printf 'Assigned GPU0 busy; refusing to launch.\n' >&2
  exit 42
fi
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="$CODE:$SRC/third_party/LIBERO-plus:$SRC:$SRC/experiments/libero"
export PYTHONDONTWRITEBYTECODE=1
export LIBERO_CONFIG_PATH="$SRC/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints"
export DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch"
export TRITON_CACHE_DIR="$RUN/cache/triton"
export TORCHINDUCTOR_CACHE_DIR="$RUN/cache/inductor"
export NUMBA_CACHE_DIR="$RUN/cache/numba"
export MPLCONFIGDIR="$RUN/cache/matplotlib"
export XDG_CACHE_HOME="$RUN/cache/xdg"
export OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export CUDAHOSTCXX="$CXX"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-gradient-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
printf '%s\n' "$TMPDIR" > "$RUN/node_local_tmpdir.txt"
mkdir -p "$TMPDIR" "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv > "$RUN/gpu_before.csv"
sha256sum "$CODE/core.py" "$CODE/zero_action_probe.py" "$CODE/PROTOCOL.md" "$CODE/stage0.json" "$CODE/STAGE0_RETRY2_APPROVED.json" > "$RUN/PREFLIGHT_SHA256SUMS"
set +e
timeout 2700 "$PY" -u "$CODE/zero_action_probe.py" > "$RUN/probe.log" 2>&1
rc=$?
set -e
nvidia-smi --query-gpu=index,uuid,memory.used,utilization.gpu --format=csv > "$RUN/gpu_after.csv"
if [ "$rc" -ne 0 ]; then exit "$rc"; fi
grep -q '"status": "ENGINEERING_PASS"' "$RUN/report.json"
sha256sum "$RUN/report.json" "$RUN/arrays.npz" "$RUN/composed_config.yaml" > "$RUN/SHA256SUMS"
touch "$RUN/ENGINEERING_AUDIT_PASS"
