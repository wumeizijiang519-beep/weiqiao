#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
RUN="$ROOT/runs/kairos_libero_plus_parity_v1"
KAIROS="$ROOT/backbones/kairos"
BENCH="$KAIROS/benchmarks/libero_plus"
COMMON="$KAIROS/benchmarks/common"
WAM_BENCH="$BENCH/kairos_wam"
LIBERO_ROOT="$ROOT/backbones/ImageWAM/third_party/LIBERO-plus"
SERVER_PY="$ROOT/envs/kairos/bin/python"
EVAL_PY="$ROOT/envs/imagewam_compat_v4/bin/python"
MODEL_ROOT="$ROOT/checkpoints_first_tier/kairos/model_root"
CKPT="$ROOT/checkpoints_first_tier/kairos/libero_plus/kairos-4B-robot-LIBERO-plus.safetensors"
CFG="$BENCH/configs/libero_wam_infer_config.py"
STATS="$BENCH/libero_plus_dataset_stats.json"
TOOLCHAIN="$ROOT/toolchains/gcc11"
PORT=18015

mkdir -p "$RUN/output" "$RUN/libero_config" "$RUN/tmp" "$RUN/cache/torch_extensions" "$RUN/cache/huggingface"
cat > "$RUN/libero_config/config.yaml" <<EOF
benchmark_root: $LIBERO_ROOT/libero/libero
bddl_files: $LIBERO_ROOT/libero/libero/bddl_files
init_states: $LIBERO_ROOT/libero/libero/init_files
datasets: $RUN/libero_datasets
assets: $LIBERO_ROOT/libero/libero/assets
EOF
cat > "$RUN/10_nvidia.json" <<'EOF'
{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}
EOF

export PROJECT_ROOT="$BENCH"
export LIBERO_PKG_ROOT="$LIBERO_ROOT"
export LIBERO_CONFIG_PATH="$RUN/libero_config"
export KAIROS_MODEL_DIR="$MODEL_ROOT"
export WAM_PRETRAINED_DIT="$CKPT"
export WAM_CFG_PATH="$CFG"
export DATASET_STATS_PATH="$STATS"
export MODEL_ENDPOINT="http://127.0.0.1:$PORT"
export PYTHONPATH="$KAIROS:$KAIROS/benchmarks:$WAM_BENCH:$WAM_BENCH/src:$LIBERO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME="$ROOT/cache/huggingface"
export PIP_CACHE_DIR="$ROOT/cache/pip"
export TORCH_EXTENSIONS_DIR="$ROOT/cache/torch_extensions"
export GPTQMODEL_AWQ_BUILD_ROOT="$ROOT/cache/gptqmodel/torch_extensions/awq"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export __EGL_VENDOR_LIBRARY_FILENAMES="$RUN/10_nvidia.json"
export WAM_EAGER_LOAD_ON_STARTUP=1
export WAM_SKIP_LOAD_ENGINE=1
export WAM_WORKER_STARTUP_TIMEOUT_SEC=900
export WAM_REQUEST_TIMEOUT_SEC=3600
export QW_DROP_IMG_IN_VLM=1

server_pid=""
cleanup() {
  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

date -Is > "$RUN/start_time.txt"
nvidia-smi --query-gpu=index,uuid,name,memory.total,memory.used --format=csv,noheader > "$RUN/gpu_before.txt"

(
  export CUDA_VISIBLE_DEVICES=0
  export WAM_GPU_IDS=0
  export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
  export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
  export CUDAHOSTCXX="$CXX"
  export LD_LIBRARY_PATH="$TOOLCHAIN/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  cd "$COMMON"
  exec "$SERVER_PY" -m uvicorn wam_service.server_multi_gpu:app --host 127.0.0.1 --port "$PORT"
) > "$RUN/server.log" 2>&1 &
server_pid=$!
printf '%s\n' "$server_pid" > "$RUN/SERVER_PID"

ready=0
for _ in $(seq 1 180); do
  if ! kill -0 "$server_pid" 2>/dev/null; then
    break
  fi
  health="$(curl -fsS "http://127.0.0.1:$PORT/health" 2>/dev/null || true)"
  printf '%s\n' "$health" > "$RUN/health_last.json"
  if [[ "$health" == *'"workers_loaded":true'* ]]; then
    ready=1
    break
  fi
  if [[ "$health" == *'"load_failed":true'* ]]; then
    break
  fi
  sleep 5
done
if [[ "$ready" != 1 ]]; then
  touch "$RUN/FAILED_SERVER_READY"
  exit 2
fi

start_epoch="$(date +%s)"
(
  export CUDA_VISIBLE_DEVICES=1
  export MUJOCO_EGL_DEVICE_ID=0
  cd "$WAM_BENCH"
  "$EVAL_PY" experiments/libero/eval_libero_single.py \
    task=libero_uncond_2cam224_1e-4 \
    model=external_model_adapter \
    "model.endpoint=$MODEL_ENDPOINT" \
    ckpt=/nothing/to/load \
    seed=10000 \
    gpu_id=0 \
    EVALUATION.task_suite_name=libero_mix \
    EVALUATION.task_id=0 \
    EVALUATION.num_trials=1 \
    "EVALUATION.category_value=Background Textures" \
    "EVALUATION.dataset_stats_path=$STATS" \
    "EVALUATION.output_dir=$RUN/output" \
    EVALUATION.num_steps_wait=30 \
    EVALUATION.replan_steps=10 \
    EVALUATION.binarize_gripper=true \
    EVALUATION.num_inference_steps=20
) > "$RUN/evaluator.log" 2>&1
end_epoch="$(date +%s)"
printf '%s\n' "$((end_epoch - start_epoch))" > "$RUN/episode_wall_seconds.txt"

result_file="$(find "$RUN/output" -type f -name '*results.json' -print -quit)"
video_file="$(find "$RUN/output" -type f -name '*.mp4' -print -quit)"
test -n "$result_file"
test -n "$video_file"
printf '%s\n' "$result_file" > "$RUN/RESULT_PATH"
printf '%s\n' "$video_file" > "$RUN/VIDEO_PATH"
nvidia-smi --query-gpu=index,uuid,name,memory.total,memory.used --format=csv,noheader > "$RUN/gpu_after.txt"
date -Is > "$RUN/end_time.txt"
sha256sum "$CKPT" "$CFG" "$STATS" "$result_file" "$video_file" "$ROOT/KAIROS_LIBERO_PLUS_PARITY_V1.md" "$ROOT/run_kairos_libero_plus_parity_v1.sh" > "$RUN/SHA256SUMS"
touch "$RUN/PARITY_COMPLETE"
