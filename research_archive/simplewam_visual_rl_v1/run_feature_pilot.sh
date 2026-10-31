#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
S=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
RUN=${SIMPLEWAM_VISUAL_RL_RUN:-$R/feature_pilot_v1}

test "$SLURM_JOB_ID" = 1593640
test ! -e "$RUN"
cd "$ROOT"
sha256sum -c "$R/SOURCE_SHA256SUMS"
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R:$ROOT/qgf_gradient_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/triton" TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/inductor"
export TMPDIR; TMPDIR=$(mktemp -d "/tmp/simplewam-visual-rl-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
trap 'code=$?; printf "%s\n" "$code" > "$R/feature_pilot_exit_code"; rm -rf "$TMPDIR"' EXIT
"$PY" -u "$R/run_feature_pilot.py" \
  --observation "$ROOT/support_gradient_qgf_v1/pilot_v1/train_0250/frozen_policy_input.npz" \
  --description "put the black bowl in the bottom drawer of the cabinet and close it add 28" \
  --run "$RUN"
