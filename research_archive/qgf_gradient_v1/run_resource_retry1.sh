#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
RUN=$ROOT/runs/qgf_resource_v1_gpu4_gpu3_retry1
test "$(hostname -s)" = gpu4
test "$(id -u)" = 2292
test "$SLURM_JOB_ID" = 1581551
grep -q /job_1581551/step_extern /proc/self/cgroup
test "$(nvidia-smi -i 3 --query-gpu=uuid --format=csv,noheader)" = GPU-e3a3e35f-949f-6746-45a4-43577f0b9b68
test -z "$(nvidia-smi -i 3 --query-compute-apps=pid --format=csv,noheader)"
test ! -e "$RUN"
mkdir "$RUN"
START=$(date +%s)
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$RUN/process_exit_code"
  printf '%s\n' "$(($(date +%s)-START))" > "$RUN/charged_gpu_seconds"
  date -Is > "$RUN/end_time"
  if [ "$rc" -eq 0 ]; then touch "$RUN/RESOURCE_COMPLETE"; else touch "$RUN/PROCESS_FAILED"; fi
}
trap finish EXIT
date -Is > "$RUN/start_time"
printf 'job=1581551 mode=owned_step_extern pid=%s gpu=3 uuid=GPU-e3a3e35f-949f-6746-45a4-43577f0b9b68\n' "$$" > "$RUN/owner.txt"
cat /proc/self/cgroup > "$RUN/cgroup.txt"
sha256sum "$CODE/resource_egl_retry1.py" "$CODE/run_resource_retry1.sh" "$CODE/RESOURCE_RETRY1.md" "$CODE/zero_action_probe.py" "$CODE/core.py" > "$RUN/SOURCE_SHA256SUMS"
export CUDA_VISIBLE_DEVICES=3 OMP_NUM_THREADS=8 QGF_RUN=$RUN
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=3
export PYTHONPATH="$CODE:$SRC/third_party/LIBERO-plus:$SRC:$SRC/experiments/libero"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$SRC/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$ROOT/cache/simplewam-torch"
export CC="$ROOT/toolchains/gcc11/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$ROOT/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$ROOT/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$ROOT/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d /tmp/qgf-resource-retry1-XXXXXX)
export TRITON_CACHE_DIR="$RUN/cache/triton" TORCHINDUCTOR_CACHE_DIR="$RUN/cache/inductor"
export NUMBA_CACHE_DIR="$RUN/cache/numba" MPLCONFIGDIR="$RUN/cache/matplotlib" XDG_CACHE_HOME="$RUN/cache/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 150 "$PY" -u "$CODE/resource_egl_retry1.py" > "$RUN/preflight.log" 2>&1
timeout 1000 "$PY" -u "$CODE/zero_action_probe.py" > "$RUN/probe.log" 2>&1
grep -q '"status": "ENGINEERING_PASS"' "$RUN/report.json"
timeout 30 "$PY" -u "$CODE/resource_check.py" compare --run "$RUN" > "$RUN/comparison.log" 2>&1
sha256sum "$RUN"/*report.json "$RUN/arrays.npz" > "$RUN/RESULT_SHA256SUMS"
