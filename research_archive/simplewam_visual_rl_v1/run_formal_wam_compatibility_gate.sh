#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
S=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
EGL_REPAIR=/public/home/wangsenbao221/SothisAI/egl_535.104.05
EXPECTED_JOB=${FORMAL_WAM_JOB_ID:?FORMAL_WAM_JOB_ID is required}
test "${SLURM_JOB_ID:-}" = "$EXPECTED_JOB"
case "$EXPECTED_JOB" in
  1581551|1598338) ;;
  *) test "$EXPECTED_JOB" -gt 1677369 ;;
esac
test -f "$R/final_critic_deployment_independent_audit_v1/SIMPLEWAM_VISUAL_QGF_FINAL_CRITIC_DEPLOYMENT_AUDIT_PASS"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R:$ROOT/qgf_gradient_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$ROOT/cache/simplewam-torch"
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export __EGL_VENDOR_LIBRARY_FILENAMES="$EGL_REPAIR/egl_vendor.d/10_nvidia.json"
export OMP_NUM_THREADS=8 CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$EGL_REPAIR:$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/triton-formal-gate" TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/inductor-formal-gate"
export TMPDIR; TMPDIR=$(mktemp -d "/tmp/simplewam-formal-gate-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-XXXXXX")
trap 'rm -rf "$TMPDIR"' EXIT
OUT=${FORMAL_GATE_OUTPUT:-$R/formal_wam_compatibility_v1}
test ! -e "$OUT"
"$PY" -u "$R/run_formal_wam_compatibility_gate.py" --root "$ROOT" --output "$OUT"
