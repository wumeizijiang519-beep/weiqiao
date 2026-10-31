#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$R/toolchains/gcc11
RUN=$C/failure_critical_boundary_v1_remaining
MANIFEST=$C/failure_critical_boundary_v1_remaining_authorized/AUTHORIZED_REMAINING_MANIFEST.json
test "$SLURM_JOB_ID" = 1593640
test ! -e "$RUN"
test "$(sha256sum "$C/run_failure_critical_boundary_v1.py" | cut -d' ' -f1)" = 0c59ea1be29323e0db907a92924ff20fd226daad5c44983207b756b4458b3ed6
test "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = 30f16115bb7b4f4b9dcfd9920ca92e298fe8daf07a78b27135a47297e290d6ab
cd "$C"
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
TMPDIR=$(mktemp -d "/tmp/qgf-failure-critical-rem-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
export TRITON_CACHE_DIR="$R/cache/qgf-paired-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$R/cache/qgf-paired-v1/inductor"
export NUMBA_CACHE_DIR="$R/cache/qgf-paired-v1/numba"
export MPLCONFIGDIR="$R/cache/qgf-paired-v1/matplotlib"
export XDG_CACHE_HOME="$R/cache/qgf-paired-v1/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 13300 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$C/run_failure_critical_boundary_v1.py" --manifest "$MANIFEST" \
  --run "$RUN" --entry-start 1 --entry-stop 16
