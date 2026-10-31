#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
S=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
test "$SLURM_JOB_ID" = 1593640
cd "$ROOT"
export CUDA_VISIBLE_DEVICES=0 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R:$ROOT/qgf_gradient_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$ROOT/cache/simplewam-torch"
export OMP_NUM_THREADS=8 CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/triton" TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/inductor"
export TMPDIR; TMPDIR=$(mktemp -d "/tmp/simplewam-visual-export-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX"); trap 'rm -rf "$TMPDIR"' EXIT
"$PY" -u "$R/export_features.py" --registration "$R/FEATURE_EXPORT_REGISTRATION.json"
