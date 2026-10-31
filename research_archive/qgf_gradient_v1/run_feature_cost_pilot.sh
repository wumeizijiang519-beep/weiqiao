#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/qgf_gradient_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
REG=$1
CONTROL=$R/runs/qgf_gradient_feature_cost_pilot_v1_process
test "$SLURM_JOB_ID" = 1593640
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
mkdir "$CONTROL"
START=$(date +%s)
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$CONTROL/process_exit_code"
  printf '%s\n' "$(($(date +%s)-START))" > "$CONTROL/charged_gpu_seconds"
  date -Is > "$CONTROL/end_time"
}
trap finish EXIT
date -Is > "$CONTROL/start_time"
printf 'job=%s step=%s host=%s physical_gpu=0\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" > "$CONTROL/allocation.txt"
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$C:$S/third_party/LIBERO-plus:$S:$S/experiments/libero"
export LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$R/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$R/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$R/cache/simplewam-torch"
export CC="$R/toolchains/gcc11/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$R/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$R/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$R/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d /tmp/qgf-feature-pilot-XXXXXX)
export TRITON_CACHE_DIR="$CONTROL/cache/triton" TORCHINDUCTOR_CACHE_DIR="$CONTROL/cache/inductor"
export NUMBA_CACHE_DIR="$CONTROL/cache/numba" MPLCONFIGDIR="$CONTROL/cache/matplotlib" XDG_CACHE_HOME="$CONTROL/cache/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
timeout 1200 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$C/extract_feature_blocks.py" --registration "$REG"
