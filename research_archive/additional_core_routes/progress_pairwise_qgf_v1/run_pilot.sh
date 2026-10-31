#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/progress_pairwise_qgf_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$R/toolchains/gcc11
RUN=$C/pilot_v1
MANIFEST=$C/registration_v1/MANIFEST.json
AUTH=$C/pilot_authorized_v1/AUTHORIZATION.json
BASES=$C/registration_v1/SUPPORT_BASES.npz
test "$SLURM_JOB_ID" = 1593640
test ! -e "$RUN"
test "$(sha256sum "$C/run_pilot.py" | cut -d' ' -f1)" = 3a56df127704bc20e154d24efb1d47306fba66c918b697377feb442706a0f584
test "$(sha256sum "$C/candidate_bank.py" | cut -d' ' -f1)" = 5f4a3257c4dbba76ac6fc83ecb5b543b3531e62615b67b9dae296f9c80ce80d8
test "$(sha256sum "$C/progress_metric.py" | cut -d' ' -f1)" = fa0696a0d4f2d185ae80fa4d9ef9491ae66fc439f17637dc3eaa9c1ee9963c19
test "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = aa20335f10dfe3b39c6ebf0ce3a4f77c24d694f9a2a5e7672cf90fb08120e256
test "$(sha256sum "$AUTH" | cut -d' ' -f1)" = a114b5eaac2a8452fd4d035c72980085c2d86c8c361513a674f648e60dce7cd3
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
TMPDIR=$(mktemp -d "/tmp/qgf-progress-pilot-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
export TRITON_CACHE_DIR="$R/cache/qgf-progress-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$R/cache/qgf-progress-v1/inductor"
export NUMBA_CACHE_DIR="$R/cache/qgf-progress-v1/numba"
export MPLCONFIGDIR="$R/cache/qgf-progress-v1/matplotlib"
export XDG_CACHE_HOME="$R/cache/qgf-progress-v1/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 1700 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$C/run_pilot.py" --manifest "$MANIFEST" --authorization "$AUTH" \
  --support-bases "$BASES" --run "$RUN"
