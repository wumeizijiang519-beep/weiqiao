#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
OUTPUT="$STAGE/v4_unitas_latents_v1"
AUDIT="$STAGE/v4_intervention_train32_v1/summary.json"
JOB_ID="${1:?Slurm job id required}"

mkdir "$OUTPUT"
export PYTHONPATH="$ROOT/backbones/UNITAS/src:$STAGE:${PYTHONPATH:-}"
export HF_HOME="$ROOT/cache_v3/hf"
export TORCH_HOME="$ROOT/cache_v3/torch"
sha256sum "$STAGE/QGF_V4_CRITIC_PROTOCOL.md" "$STAGE/export_v4_unitas_latents.py" \
  "$STAGE/validate_v4_unitas_latents.py" > "$OUTPUT/code.sha256"

timeout --signal=TERM --kill-after=30 1800 \
  srun --jobid="$JOB_ID" --overlap --nodes=1 --ntasks=4 --gpus-per-task=1 \
  --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  "$ROOT/envs/unitas_retry6/bin/python" -u "$STAGE/export_v4_unitas_latents.py" \
  --audit "$AUDIT" --florence-dir "$ROOT/checkpoints_first_tier/unitas/Florence-2-large" \
  --output "$OUTPUT" --device cuda:0 --batch-size 4 > "$OUTPUT/export.log" 2>&1

"$ROOT/envs/unitas_retry6/bin/python" "$STAGE/validate_v4_unitas_latents.py" \
  --audit "$AUDIT" --output "$OUTPUT" > "$OUTPUT/validation.log" 2>&1
sha256sum "$OUTPUT/manifest.json" > "$OUTPUT/result.sha256"

