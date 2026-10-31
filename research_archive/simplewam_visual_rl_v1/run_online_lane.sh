#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
R=$ROOT/simplewam_visual_rl_v1
S=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
TOOLCHAIN=$ROOT/toolchains/gcc11
EGL_REPAIR=/public/home/wangsenbao221/SothisAI/egl_535.104.05
LANE=${1:?lane required}
test "$SLURM_JOB_ID" = 1677369
test -f "$R/wam_compatibility_v1/SIMPLEWAM_VISUAL_QGF_WAM_COMPATIBILITY_PASS"
test "$LANE" -ge 0 -a "$LANE" -lt 4
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$R:$ROOT/qgf_gradient_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$ROOT/cache/simplewam-torch"
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
export __EGL_VENDOR_LIBRARY_FILENAMES="$EGL_REPAIR/egl_vendor.d/10_nvidia.json"
export OMP_NUM_THREADS=8 CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$EGL_REPAIR:$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/triton-lane-$LANE" TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/simplewam-visual-rl-v1/inductor-lane-$LANE"
OUT=$R/online_execution_v1
mkdir -p "$OUT"
for INDEX in $(seq "$LANE" 4 255); do
  TASK=$(printf 'task_%03d' "$INDEX")
  if test -f "$OUT/$TASK/SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE"; then continue; fi
  test ! -e "$OUT/$TASK"
  export TMPDIR; TMPDIR=$(mktemp -d "/tmp/simplewam-online-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-${TASK}-XXXXXX")
  "$PY" -u "$R/run_online_task.py" --root "$ROOT" --task-index "$INDEX" --output "$OUT/$TASK" \
    >"$OUT/${TASK}.log" 2>&1
  rm -rf "$TMPDIR"
  printf '%s\n' "$INDEX" >"$OUT/LANE_${LANE}_LAST_COMPLETE_TASK"
done
touch "$OUT/LANE_${LANE}_COMPLETE"
