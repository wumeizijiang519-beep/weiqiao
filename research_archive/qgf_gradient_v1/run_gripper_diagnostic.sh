#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
export QGF_DIAGNOSTIC_RUN=$ROOT/runs/qgf_gradient_native_gripper_diagnostic_v1
test ! -e "$QGF_DIAGNOSTIC_RUN"
test "$SLURM_JOB_ID" = 1593640
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
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
TMPDIR=$(mktemp -d "/tmp/qgf-gripper-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
export TRITON_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/inductor"
export NUMBA_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/numba"
export MPLCONFIGDIR="$ROOT/cache/qgf-gradient-collector-v1/matplotlib"
export XDG_CACHE_HOME="$ROOT/cache/qgf-gradient-collector-v1/xdg"
finish() {
  rc=$?
  if [ -d "$QGF_DIAGNOSTIC_RUN" ]; then
    printf '%s\n' "$rc" > "$QGF_DIAGNOSTIC_RUN/process_exit_code"
    printf 'job=%s step=%s host=%s visible=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES" > "$QGF_DIAGNOSTIC_RUN/allocation.txt"
    if [ "$rc" -eq 0 ]; then touch "$QGF_DIAGNOSTIC_RUN/PROCESS_COMPLETE"; else touch "$QGF_DIAGNOSTIC_RUN/PROCESS_FAILED"; fi
  fi
}
trap finish EXIT
printf 'job=%s step=%s host=%s visible=%s\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" "$CUDA_VISIBLE_DEVICES"
timeout 880 "$PY" -u "$CODE/diagnose_gripper.py"
sha256sum "$QGF_DIAGNOSTIC_RUN/REPORT.json" "$QGF_DIAGNOSTIC_RUN/bank.npz" > "$QGF_DIAGNOSTIC_RUN/SHA256SUMS"
