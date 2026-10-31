#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE="$ROOT/setwise_contrastive_qgf_v1"
S="$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a"
TOOLCHAIN="$ROOT/toolchains/gcc11"
PY="$ROOT/runtime/simplewam_inference_py310_v2/bin/python"
RUN="$CODE/remaining_v1"

test "$SLURM_JOB_ID" = 1593640
test "$(sha256sum "$CODE/run_single_group.py" | cut -d' ' -f1)" = f27d690236d96791ab03cb6a47939aad07bf178ada7eb3b1c2ad34f56deeae69
test "$(sha256sum "$CODE/registration_v1/MANIFEST.json" | cut -d' ' -f1)" = 3cf5228bed57d3c7174ac129ea2ff2744c09e2576957814333107053c781d003
test "$(sha256sum "$CODE/authorized_v1_retry1/MANIFEST.json" | cut -d' ' -f1)" = b91432d91004e620edcfc29b8714b62b8880bbbd216818b8894106885f37ffb0
test "$(sha256sum "$CODE/pilot_audit_v1/REPORT.json" | cut -d' ' -f1)" = 9c43609d54595e40c406dd2e89a7b62025481e93b15dcaf831786efc8976e600
test ! -e "$RUN"

cd "$CODE"
export CUDA_VISIBLE_DEVICES=0 MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$ROOT/qgf_gradient_v1:$CODE:$ROOT/runtime_anchored_qgf_v1:$S/third_party/LIBERO-plus:$S:$S/experiments/libero:${PYTHONPATH:-}"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export TORCH_HOME="$ROOT/cache/simplewam-torch" OMP_NUM_THREADS=8
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TRITON_CACHE_DIR="$ROOT/cache/qgf-setwise-v1/triton"
export TORCHINDUCTOR_CACHE_DIR="$ROOT/cache/qgf-setwise-v1/inductor"
export NUMBA_CACHE_DIR="$ROOT/cache/qgf-setwise-v1/numba"
export MPLCONFIGDIR="$ROOT/cache/qgf-setwise-v1/matplotlib"
export XDG_CACHE_HOME="$ROOT/cache/qgf-setwise-v1/xdg"

mkdir "$RUN"
: > "$RUN/UNAVAILABLE_ENTRY_INDICES"
for index in $(seq 1 23); do
  entry=$(printf '%02d' "$index")
  target="$RUN/entry_$entry"
  export TMPDIR
  TMPDIR=$(mktemp -d "/tmp/qgf-setwise-${USER}-${SLURM_JOB_ID}-${SLURM_STEP_ID}-${index}-XXXXXX")
  set +e
  "$PY" -u "$CODE/run_single_group.py" \
    --manifest "$CODE/registration_v1/MANIFEST.json" \
    --authorization "$CODE/authorized_v1_retry1/entry_$entry.json" \
    --support-bases "$CODE/registration_v1/SUPPORT_BASES.npz" \
    --run "$target" > "$RUN/entry_$entry.log" 2>&1
  code=$?
  set -e
  if (( code != 0 )); then
    if grep -q 'Reconstructed boundary policy input differs from archive' "$RUN/entry_$entry.log"; then
      echo "$index" >> "$RUN/UNAVAILABLE_ENTRY_INDICES"
      continue
    fi
    exit "$code"
  fi
  test -f "$target/PILOT_RETURNED"
  echo "$index" > "$RUN/LAST_COMPLETE_INDEX"
done
touch "$RUN/POPULATION_RETURNED"
