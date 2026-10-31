#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
test "$(id -u)" = 2292; test "$(hostname -s)" = gpu22; test "$SLURM_JOB_ID" = 1598338; grep -q '/job_1598338/step_extern' /proc/self/cgroup
test "$(nvidia-smi -i 0 --query-gpu=uuid --format=csv,noheader)" = GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db; test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
CONTROL=$ROOT/runs/qgf_ensemble_consensus_scores_v1_process; mkdir "$CONTROL"; START=$(date +%s); finish(){ rc=$?; echo "$rc" > "$CONTROL/process_exit_code"; echo "$(($(date +%s)-START))" > "$CONTROL/charged_gpu_seconds"; }; trap finish EXIT
export CUDA_VISIBLE_DEVICES=GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db OMP_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
timeout 900 "$ROOT/runtime/simplewam_inference_py310_v2/bin/python" -u "$ROOT/ensemble_consensus_qgf_v1/build_scores.py" --root "$ROOT" --metadata "$ROOT/runtime_delta_qgf_v1/development_corpus_v1/METADATA.json" --output "$ROOT/ensemble_consensus_qgf_v1/scores_v1"
