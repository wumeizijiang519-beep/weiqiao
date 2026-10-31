#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
QGFV2="$ROOT/qgf_v2"
ENV="$ROOT/envs/imagewam_compat_v4"
IW="$ROOT/backbones/ImageWAM"
RUN="${RUN:-$QGFV2/runs/imagewam_n4_candidate_smoke_v1}"

mkdir -p "$RUN" "$ROOT/tmp/imagewam-libero-plus-home"
export HOME="$ROOT/tmp/imagewam-libero-plus-home"
export PYTHONPATH="$IW:$IW/src:$IW/third_party/flux2/src:$IW/third_party/flux2"
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

"$ENV/bin/python" "$QGFV2/imagewam_n4_candidate_smoke.py" \
  --root "$ROOT" \
  --output "$RUN" \
  > "$RUN/smoke.log" 2>&1

sha256sum "$RUN/report.json" "$RUN/candidates.npz" > "$RUN/OUTPUT_SHA256SUMS"
touch "$RUN/CANDIDATE_SMOKE_COMPLETE"
