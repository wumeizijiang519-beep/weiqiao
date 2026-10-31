#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
T=$R/toolchains/gcc11
test "$SLURM_JOB_ID" = 1593640
test ! -e "$C/runtime_inventory_retry1"
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
cd "$C"
tr -d '\r' < RUNTIME_INVENTORY_RETRY1_SHA256SUMS | sha256sum -c -
export CUDA_VISIBLE_DEVICES=0 MUJOCO_EGL_DEVICE_ID=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export PYTHONPATH="$C:$R/qgf_gradient_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero"
export LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export LD_LIBRARY_PATH="$T/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2
export NUMBA_CACHE_DIR="$R/cache/qgf-gradient-collector-v1/numba"
export MPLCONFIGDIR="$R/cache/qgf-gradient-collector-v1/matplotlib"
export XDG_CACHE_HOME="$R/cache/qgf-gradient-collector-v1/xdg"
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$C/runtime_inventory_retry1_process_exit_code"
  printf 'job=%s step=%s host=%s zero_model_actions=1\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" > "$C/runtime_inventory_retry1_allocation.txt"
}
trap finish EXIT
timeout 240 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$C/runtime_inventory.py" --output runtime_inventory_retry1
