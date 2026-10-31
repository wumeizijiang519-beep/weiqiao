#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$R/toolchains/gcc11
RUN=$C/paired_diagnostic_v1_retry2
test "$SLURM_JOB_ID" = 1593640
test ! -e "$RUN"
cd "$C"
tr -d '\r' < PAIRED_DIAGNOSTIC_RETRY2_SHA256SUMS | sha256sum -c -
test "$(sha256sum "$R/qgf_gradient_v1/core.py" | awk '{print $1}')" = 1b30c5d66f3958b05aa9dcc582f2eef42ee03a308300260fbe0b6d74fc0f6d29
test "$(sha256sum "$R/qgf_gradient_v1/data_contract.py" | awk '{print $1}')" = 39301bf91924133f275ca4780a751a0c37c4787c5164fa45bb182e5d20bb26df
test "$(sha256sum "$R/qgf_gradient_v1/wam_runtime.py" | awk '{print $1}')" = 5c4b354b5903d6c4b955e557bbdd1bbec07bc6f6eedec35874bfda0211e3dad0
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$R/qgf_gradient_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$R/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$R/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$R/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-paired-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
export TRITON_CACHE_DIR="$R/cache/qgf-paired-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$R/cache/qgf-paired-v1/inductor"
export NUMBA_CACHE_DIR="$R/cache/qgf-paired-v1/numba"
export MPLCONFIGDIR="$R/cache/qgf-paired-v1/matplotlib"
export XDG_CACHE_HOME="$R/cache/qgf-paired-v1/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 6690 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$C/run_paired_diagnostic_v1_retry2.py" --run "$RUN"
