#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
export QGF_RENDER_DIAGNOSTIC_RUN=$ROOT/runs/qgf_gradient_render_diagnostic_v1_retry1
test ! -e "$QGF_RENDER_DIAGNOSTIC_RUN"
test "$SLURM_JOB_ID" = 1593640
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$CODE:$SRC/third_party/LIBERO-plus:$SRC:$SRC/experiments/libero"
export LIBERO_CONFIG_PATH="$SRC/third_party/LIBERO-plus/.libero" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export NUMBA_CACHE_DIR="$ROOT/cache/qgf-gradient-collector-v1/numba"
export MPLCONFIGDIR="$ROOT/cache/qgf-gradient-collector-v1/matplotlib"
export XDG_CACHE_HOME="$ROOT/cache/qgf-gradient-collector-v1/xdg"
cd "$CODE"
timeout 300 "$PY" -u "$CODE/diagnose_restore_render.py"
sha256sum "$QGF_RENDER_DIAGNOSTIC_RUN/DIAGNOSTIC_REPORT.json" "$CODE/diagnose_restore_render.py" > "$QGF_RENDER_DIAGNOSTIC_RUN/SHA256SUMS"
