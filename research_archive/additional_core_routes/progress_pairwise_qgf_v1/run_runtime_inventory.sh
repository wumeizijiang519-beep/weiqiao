#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
P=$R/progress_pairwise_qgf_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$R/toolchains/gcc11
RUN=$P/runtime_inventory_v1
MANIFEST=$P/registration_v1/MANIFEST.json
test "$SLURM_JOB_ID" = 1593640
test ! -e "$RUN"
test "$(sha256sum "$P/runtime_inventory.py" | cut -d' ' -f1)" = "${RUNTIME_INVENTORY_SOURCE_SHA256:?}"
test "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = "${MANIFEST_SHA256:?}"
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$R/qgf_gradient_v1:$R/paired_action_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export OMP_NUM_THREADS=4
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-progress-inventory-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
timeout 280 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$P/runtime_inventory.py" --manifest "$MANIFEST" --manifest-sha256 "$MANIFEST_SHA256" \
  --output "$RUN/REPORT.json"
