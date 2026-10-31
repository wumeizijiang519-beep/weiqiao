#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R="$ROOT/runtime_anchored_qgf_v1"
S="$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a"
TOOLCHAIN="$ROOT/toolchains/gcc11"
PY="$ROOT/runtime/simplewam_inference_py310_v2/bin/python"
RUN="$R/pilot_v1"

test "$SLURM_JOB_ID" = 1593640
test "$(sha256sum "$R/run_single_group.py" | cut -d' ' -f1)" = 99fe564910ac51f0dcfba01e6bff0d94e323ace4ac0b4efa504b53ba7f543027
test "$(sha256sum "$R/registration_v1/MANIFEST.json" | cut -d' ' -f1)" = ba97d5303ceabc9d4455356d7f732cdc643f995fb00f9393b6819db8752947c1
test "$(sha256sum "$R/registration_v1/authorization/entry_00.json" | cut -d' ' -f1)" = 5c74c5557b18477dd1422fc4aa1ec562cac2891096c5dd527458af44af73eeb1
test ! -e "$RUN"

cd "$R"
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$ROOT/qgf_gradient_v1:$R:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/qgf-runtime-anchored-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/qgf-runtime-anchored-v1/inductor"
export NUMBA_CACHE_DIR="$ROOT/cache/qgf-runtime-anchored-v1/numba"
export MPLCONFIGDIR="$ROOT/cache/qgf-runtime-anchored-v1/matplotlib"
export XDG_CACHE_HOME="$ROOT/cache/qgf-runtime-anchored-v1/xdg"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-runtime-anchor-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")

"$PY" -u "$R/run_single_group.py" \
  --manifest "$R/registration_v1/MANIFEST.json" \
  --authorization "$R/registration_v1/authorization/entry_00.json" \
  --support-bases "$R/registration_v1/SUPPORT_BASES.npz" \
  --run "$RUN"
test -f "$RUN/PILOT_RETURNED"
