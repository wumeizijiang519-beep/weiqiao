#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R="$ROOT/runtime_anchored_qgf_v1"
S="$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a"
TOOLCHAIN="$ROOT/toolchains/gcc11"
PY="$ROOT/runtime/simplewam_inference_py310_v2/bin/python"
REG="$R/registration_v1_retry1"
RUN="$R/resume_entry11_v1_retry1"

test "$SLURM_JOB_ID" = 1593640
test "$(sha256sum "$R/run_single_group.py" | cut -d' ' -f1)" = 99fe564910ac51f0dcfba01e6bff0d94e323ace4ac0b4efa504b53ba7f543027
test "$(sha256sum "$REG/MANIFEST.json" | cut -d' ' -f1)" = 67210bb4c1f1907c990ed699f8d871f5692416201fec878f7abffacec3527d82
test -f "$R/pilot_audit_v1_retry1/RUNTIME_ANCHORED_PILOT_AUDIT_PASS"
test -f "$R/remaining_v1/entry_10/PILOT_RETURNED"
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
TMPDIR=$(mktemp -d "/tmp/qgf-runtime-resume-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-11-retry1-XXXXXX")
trap 'rm -rf "$TMPDIR"' EXIT

timeout 5890 "$PY" -u "$R/run_single_group.py" \
  --manifest "$REG/MANIFEST.json" \
  --authorization "$REG/authorization/entry_11.json" \
  --support-bases "$REG/SUPPORT_BASES.npz" --run "$RUN"
test -f "$RUN/REPORT.json"
test -f "$RUN/PILOT_RETURNED"
touch "$RUN/RESUME_RETURNED"
