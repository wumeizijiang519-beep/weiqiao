#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
STAGE="$ROOT/qgf_v2"
OUTPUT="$STAGE/unitas_latents_v1"
JOB_ID="${1:?Slurm job id required}"

mkdir "$OUTPUT"
export PYTHONPATH="$ROOT/backbones/UNITAS/src:$STAGE:${PYTHONPATH:-}"
export HF_HOME="$ROOT/cache_v3/hf"
export TORCH_HOME="$ROOT/cache_v3/torch"

sha256sum \
  "$STAGE/probe_unitas_latent.py" \
  "$STAGE/export_unitas_latents.py" \
  "$STAGE/validate_unitas_latents.py" \
  "$STAGE/QGF_V3_WAM_LATENT_PROTOCOL.md" >"$OUTPUT/code.sha256"

timeout --signal=TERM --kill-after=30 1800 \
  srun --jobid="$JOB_ID" --overlap --nodes=1 --ntasks=4 \
  --gpus-per-task=1 --gpu-bind=single:1 --cpus-per-task=4 --kill-on-bad-exit=1 \
  "$ROOT/envs/unitas_retry6/bin/python" -u "$STAGE/export_unitas_latents.py" \
  --audit "$STAGE/standard60_combined_audit.json" \
  --florence-dir "$ROOT/checkpoints_first_tier/unitas/Florence-2-large" \
  --output "$OUTPUT" --device cuda:0 --batch-size 4 >"$OUTPUT/export.log" 2>&1

"$ROOT/envs/unitas_retry6/bin/python" "$STAGE/validate_unitas_latents.py" \
  --audit "$STAGE/standard60_combined_audit.json" --output "$OUTPUT"

sha256sum "$OUTPUT/manifest.json" >"$OUTPUT/result.sha256"
