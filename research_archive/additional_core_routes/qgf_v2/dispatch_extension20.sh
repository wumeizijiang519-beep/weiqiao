#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
case "${SLURM_PROCID:?Slurm task rank required}" in
  0) PORT=18231; SEED=202616100 ;;
  1) PORT=18232; SEED=202616200 ;;
  *) exit 2 ;;
esac
exec bash "$ROOT/qgf_v2/run_standard_collection.sh" "${1:?dynamic gpu1 host required}" "$PORT" "$SEED" 10 "standard_train10_seed$SEED"
