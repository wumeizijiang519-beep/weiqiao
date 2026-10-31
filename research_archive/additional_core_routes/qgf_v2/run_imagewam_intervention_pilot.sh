#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
QGFV2="$ROOT/qgf_v2"
ENV="$ROOT/envs/imagewam_compat_v4"
IW="$ROOT/backbones/ImageWAM"
SHARD="$1"
PLAN="${2:-task0}"
RUN_NAME="${3:-imagewam_intervention_pilot_v1}"
OUT="$QGFV2/runs/$RUN_NAME/shard$SHARD"
mkdir -p "$ROOT/tmp/imagewam-libero-plus-home" "$(dirname "$OUT")"
export HOME="$ROOT/tmp/imagewam-libero-plus-home"
export PYTHONPATH="$IW:$IW/src:$IW/third_party/flux2/src:$IW/third_party/flux2"
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
"$ENV/bin/python" "$QGFV2/imagewam_intervention_collector.py" --root "$ROOT" --output "$OUT" --shard "$SHARD" --plan "$PLAN"
sha256sum "$OUT/report.json" "$OUT"/*.npz > "$OUT/OUTPUT_SHA256SUMS"

