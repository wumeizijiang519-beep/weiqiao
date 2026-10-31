#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$R/toolchains/gcc11
RUN=$C/boundary_anchored_remaining_v1
test "$SLURM_JOB_ID" = 1593640
test ! -e "$RUN"
cd "$C"
sha256sum -c BOUNDARY_ANCHORED_REMAINING_V1_SHA256SUMS
test "$(sha256sum boundary_anchored_pilot_v1/REPORT.json | awk '{print $1}')" = a128546203427b6469c294459468a10b10ae1a3752e5858a8a84ae52bf13611a
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$R/qgf_gradient_v1:$C:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$R/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$R/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$R/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-boundary-rem-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
export TRITON_CACHE_DIR="$R/cache/qgf-paired-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$R/cache/qgf-paired-v1/inductor"
export NUMBA_CACHE_DIR="$R/cache/qgf-paired-v1/numba"
export MPLCONFIGDIR="$R/cache/qgf-paired-v1/matplotlib"
export XDG_CACHE_HOME="$R/cache/qgf-paired-v1/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 5900 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$C/run_boundary_anchored_paired_v1.py" --run "$RUN" --entry-start 1 --entry-stop 16
