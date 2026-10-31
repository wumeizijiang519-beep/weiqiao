#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
export QGF_CHECKPOINT_RUN=$ROOT/runs/qgf_gradient_checkpoint_gate_v3
test ! -e "$QGF_CHECKPOINT_RUN"
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
trap 'rc=$?; test ! -d "$QGF_CHECKPOINT_RUN" || printf "%s\n" "$rc" > "$QGF_CHECKPOINT_RUN/process_exit_code"' EXIT
timeout 550 "$PY" -u "$CODE/checkpoint_gate_v3.py"
sha256sum "$QGF_CHECKPOINT_RUN/REPORT.json" "$CODE/replay_checkpoint_v3.py" "$CODE/CHECKPOINT_RECOVERY_V3.md" > "$QGF_CHECKPOINT_RUN/SHA256SUMS"
