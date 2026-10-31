#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
CODE=$ROOT/qgf_gradient_v1
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
REG=$1
RUN=$2
test ! -e "$RUN"
test "$SLURM_JOB_ID" = 1593640
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
if [ -n "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)" ]; then exit 42; fi
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$CODE:$SRC/third_party/LIBERO-plus:$SRC:$SRC/experiments/libero"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$SRC/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-train-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
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
    printf 'job=%s step=%s host=%s visible=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES" > "$RUN/allocation.txt"
    printf '%s\n' "$TMPDIR" > "$RUN/node_local_tmpdir.txt"
    if [ "$rc" -eq 0 ]; then touch "$RUN/PROCESS_COMPLETE"; else touch "$RUN/PROCESS_FAILED"; fi
  fi
}
trap finish EXIT
printf 'job=%s step=%s host=%s visible=%s reg=%s tmp=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES" "$REG" "$TMPDIR"
timeout 3000 "$PY" -u "$CODE/collect_v2.py" --registration "$REG" --run "$RUN"
sha256sum "$RUN/report.json" "$REG" > "$RUN/COLLECTION_SHA256SUMS"
# CPU-only independent audit is dispatched after this GPU step has exited.
