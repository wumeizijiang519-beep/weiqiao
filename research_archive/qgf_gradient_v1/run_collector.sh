#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
CODE=$ROOT/qgf_gradient_v1
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
RUN=$ROOT/runs/qgf_gradient_collector_integrity_v1
REG=$CODE/COLLECTOR_INTEGRITY_V1.json
# The collector creates the fresh directory after validating the registration.
test ! -e "$RUN"
test "$SLURM_JOB_ID" = 1593640
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
if [ -n "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)" ]; then
  printf 'Assigned GPU0 is busy; launch refused.\n' >&2
  exit 42
fi
export CUDA_VISIBLE_DEVICES=0
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$CODE:$SRC/third_party/LIBERO-plus:$SRC:$SRC/experiments/libero"
export PYTHONDONTWRITEBYTECODE=1
export LIBERO_CONFIG_PATH="$SRC/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints"
export DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch"
export OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export CUDAHOSTCXX="$CXX"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-collect-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
export TRITON_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/inductor"
export NUMBA_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/numba"
export MPLCONFIGDIR="$ROOT/cache/qgf-gradient-collector-v1/matplotlib"
export XDG_CACHE_HOME="$ROOT/cache/qgf-gradient-collector-v1/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
finish() {
  rc=$?
  if [ -d "$RUN" ]; then
    printf '%s\n' "$rc" > "$RUN/process_exit_code"
    date -Is > "$RUN/end_time"
    if [ "$rc" -eq 0 ]; then touch "$RUN/PROCESS_COMPLETE"; else touch "$RUN/PROCESS_FAILED"; fi
  fi
}
trap finish EXIT
printf 'job=%s step=%s host=%s visible=%s tmp=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES" "$TMPDIR"
# Redirect outside the not-yet-created scientific directory so no path is reused.
timeout 3300 "$PY" -u "$CODE/collect.py" --registration "$REG" --run "$RUN"
printf 'job=%s step=%s host=%s visible=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES" > "$RUN/allocation.txt"
printf '%s\n' "$TMPDIR" > "$RUN/node_local_tmpdir.txt"
CUDA_VISIBLE_DEVICES='' timeout 240 "$PY" -u "$CODE/audit_collection.py" --run "$RUN" > "$RUN/independent_audit.log" 2>&1
sha256sum "$RUN/report.json" "$RUN/INDEPENDENT_AUDIT.json" "$REG" "$CODE/collect.py" "$CODE/data_contract.py" "$CODE/audit_collection.py" > "$RUN/SHA256SUMS"
