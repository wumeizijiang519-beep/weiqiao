#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
CODE=$ROOT/qgf_gradient_v1
SRC=$ROOT/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
PY=$ROOT/runtime/simplewam_inference_py310_v2/bin/python
RUN=$ROOT/runs/qgf_resource_v2_gpu22_gpu0_wam
test "$(hostname -s)" = gpu22
test "$(id -u)" = 2292
grep -q '/job_1598338/step_extern' /proc/self/cgroup
test "$(nvidia-smi -i 0 --query-gpu=uuid --format=csv,noheader)" = GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
test ! -e "$RUN"
mkdir "$RUN"
START=$(date +%s)
finish() {
  rc=$?
  end=$(date +%s)
  printf '%s\n' "$rc" > "$RUN/process_exit_code"
  printf '%s\n' "$((end-START))" > "$RUN/charged_gpu_seconds"
  date -Is > "$RUN/end_time"
  if [ "$rc" -eq 0 ]; then touch "$RUN/RESOURCE_COMPLETE"; else touch "$RUN/PROCESS_FAILED"; fi
}
trap finish EXIT
date -Is > "$RUN/start_time"
cat /proc/self/cgroup > "$RUN/cgroup.txt"
printf 'job=1598338 mode=owned_step_extern pid=%s host=gpu22 physical_gpu=0 uuid=%s\n' \
  "$$" GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db > "$RUN/owner.txt"
sha256sum "$CODE/GPU22_WAM_PORTABILITY_V1.md" "$CODE/run_gpu22_wam_portability_v1.sh" \
  "$CODE/resource_check.py" "$CODE/zero_action_probe.py" "$CODE/core.py" > "$RUN/SOURCE_SHA256SUMS"
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 QGF_RUN=$RUN
export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl MUJOCO_EGL_DEVICE_ID=0
export PYTHONPATH="$CODE:$SRC/third_party/LIBERO-plus:$SRC:$SRC/experiments/libero"
export PYTHONDONTWRITEBYTECODE=1 LIBERO_CONFIG_PATH="$SRC/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$ROOT/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$ROOT/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$ROOT/cache/simplewam-torch"
export CC="$ROOT/toolchains/gcc11/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$ROOT/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$ROOT/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$ROOT/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d "/tmp/qgf-gpu22-portability-${USER}-XXXXXX")
export TRITON_CACHE_DIR="$RUN/cache/triton" TORCHINDUCTOR_CACHE_DIR="$RUN/cache/inductor"
export NUMBA_CACHE_DIR="$RUN/cache/numba" MPLCONFIGDIR="$RUN/cache/matplotlib" XDG_CACHE_HOME="$RUN/cache/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 120 "$PY" -u "$CODE/resource_check.py" egl --run "$RUN" > "$RUN/preflight.log" 2>&1
timeout 1250 "$PY" -u "$CODE/zero_action_probe.py" > "$RUN/probe.log" 2>&1
grep -q '"status": "ENGINEERING_PASS"' "$RUN/report.json"
timeout 30 "$PY" -u "$CODE/resource_check.py" compare --run "$RUN" > "$RUN/comparison.log" 2>&1
sha256sum "$RUN"/*report.json > "$RUN/RESULT_SHA256SUMS"
