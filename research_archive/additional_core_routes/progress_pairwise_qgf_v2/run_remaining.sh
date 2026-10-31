#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
V2="$ROOT/progress_pairwise_qgf_v2"
S="$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a"
TOOLCHAIN="$ROOT/toolchains/gcc11"
PY="$ROOT/runtime/simplewam_inference_py310_v2/bin/python"
RUN="$V2/population_v1_retry2"
test "$SLURM_JOB_ID" = 1593640
test "$(sha256sum "$V2/run_single_group.py" | cut -d' ' -f1)" = b2fb5abd811dd449232e59223d608b83601458e6813f2c05e80ba07af4df61ae
test "$(sha256sum "$V2/registration_v1_retry2/MANIFEST.json" | cut -d' ' -f1)" = 00e49dd200ce4851de0678c6385616f12e9c1d82392e47c1c55393670ba18226
test "$(sha256sum "$V2/authorized_v1_retry3/MANIFEST.json" | cut -d' ' -f1)" = f02f5a488f03ff0d45b2d8aebd0d3cad5ccc6bcbd303e0609ca05851b7567194
cd "$V2"
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$ROOT/qgf_gradient_v1:$V2:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/qgf-progress-v2/triton"
export TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/qgf-progress-v2/inductor"
export NUMBA_CACHE_DIR="$ROOT/cache/qgf-progress-v2/numba"
export MPLCONFIGDIR="$ROOT/cache/qgf-progress-v2/matplotlib"
export XDG_CACHE_HOME="$ROOT/cache/qgf-progress-v2/xdg"
mkdir -p "$RUN"
: > "$RUN/UNAVAILABLE_ENTRY_INDICES"

for index in $(seq 0 31); do
  entry=$(printf '%02d' "$index")
  target="$RUN/entry_$entry"
  if [[ -f "$target/PILOT_RETURNED" ]]; then
    continue
  fi
  export TMPDIR
  TMPDIR=$(mktemp -d "/tmp/qgf-progress-v2-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-${index}-XXXXXX")
  set +e
  "$PY" -u "$V2/run_single_group.py" \
    --manifest "$V2/registration_v1_retry2/MANIFEST.json" \
    --authorization "$V2/authorized_v1_retry3/entry_$entry.json" \
    --support-bases "$V2/registration_v1_retry2/SUPPORT_BASES.npz" \
    --run "$target"
  code=$?
  set -e
  if (( code != 0 )); then
    if grep -q 'Reconstructed boundary policy input differs from archive' "$target/FAILED.txt" 2>/dev/null; then
      echo "$index" >> "$RUN/UNAVAILABLE_ENTRY_INDICES"
      continue
    fi
    exit "$code"
  fi
  test -f "$target/PILOT_RETURNED"
  echo "$index" > "$RUN/LAST_COMPLETE_INDEX"
done
touch "$RUN/POPULATION_RETURNED"
