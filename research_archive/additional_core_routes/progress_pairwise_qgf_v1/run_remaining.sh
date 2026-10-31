#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/progress_pairwise_qgf_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
TOOLCHAIN=$R/toolchains/gcc11
MANIFEST=$C/registration_v1/MANIFEST.json
BASES=$C/registration_v1/SUPPORT_BASES.npz
test "$SLURM_JOB_ID" = 1593640
test "$(sha256sum "$C/run_single_group.py" | cut -d' ' -f1)" = 6f0739866b59225760aa1b8c2dc6ffd6e97db7e46a1f939f35445698544371fa
test "$(sha256sum "$C/candidate_bank.py" | cut -d' ' -f1)" = 5f4a3257c4dbba76ac6fc83ecb5b543b3531e62615b67b9dae296f9c80ce80d8
test "$(sha256sum "$C/progress_metric.py" | cut -d' ' -f1)" = fa0696a0d4f2d185ae80fa4d9ef9491ae66fc439f17637dc3eaa9c1ee9963c19
test "$(sha256sum "$MANIFEST" | cut -d' ' -f1)" = aa20335f10dfe3b39c6ebf0ce3a4f77c24d694f9a2a5e7672cf90fb08120e256
(cd "$R" && sha256sum -c "$C/REMAINING_SHA256SUMS")
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
export TRITON_CACHE_DIR="$R/cache/qgf-progress-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$R/cache/qgf-progress-v1/inductor"
export NUMBA_CACHE_DIR="$R/cache/qgf-progress-v1/numba"
export MPLCONFIGDIR="$R/cache/qgf-progress-v1/matplotlib"
export XDG_CACHE_HOME="$R/cache/qgf-progress-v1/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
for index in $(seq 1 15); do
  run="$C/remaining_v1/entry_$(printf '%02d' "$index")"
  auth="$C/remaining_authorized_v1/entry_$(printf '%02d' "$index").json"
  test ! -e "$run"
  export TMPDIR
  TMPDIR=$(mktemp -d "/tmp/qgf-progress-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-${index}-XXXXXX")
  "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
    "$C/run_single_group.py" --manifest "$MANIFEST" --authorization "$auth" \
    --support-bases "$BASES" --run "$run"
  printf '%s\n' "$index" > "$C/remaining_v1/LAST_COMPLETE_INDEX"
done
touch "$C/remaining_v1/REMAINING_RETURNED"
