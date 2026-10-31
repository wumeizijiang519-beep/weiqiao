#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/ensemble_disagreement_qgf_v1
S=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$ROOT/toolchains/gcc11
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
RUN=$R/pilot_v1
test "$SLURM_JOB_ID" = 1593640
cd "$ROOT"; sha256sum -c "$R/SOURCE_SHA256SUMS"; test ! -e "$RUN"
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$ROOT/qgf_gradient_v1:$R:$ROOT/runtime_anchored_qgf_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$ROOT/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/qgf-ensemble-disagreement-v1/triton" TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/qgf-ensemble-disagreement-v1/inductor" NUMBA_CACHE_DIR="$ROOT/cache/qgf-ensemble-disagreement-v1/numba" MPLCONFIGDIR="$ROOT/cache/qgf-ensemble-disagreement-v1/matplotlib" XDG_CACHE_HOME="$ROOT/cache/qgf-ensemble-disagreement-v1/xdg"
export TMPDIR; TMPDIR=$(mktemp -d "/tmp/qgf-ensemble-disagreement-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX"); trap 'rm -rf "$TMPDIR"' EXIT
"$PY" -u "$R/run_single_group.py" --manifest "$R/registration_v1/MANIFEST.json" --authorization "$R/authorized_v1/entry_00.json" --support-bases "$R/registration_v1/SUPPORT_BASES.npz" --run "$RUN"
test -f "$RUN/PILOT_RETURNED"
