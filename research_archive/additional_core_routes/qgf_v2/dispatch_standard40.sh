#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
case "${SLURM_PROCID:?Slurm task rank required}" in
  0) HOST="${1:?gpu1 host required}"; PORT=18231; SEED=202615100 ;;
  1) HOST="${1:?gpu1 host required}"; PORT=18232; SEED=202615200 ;;
  2) HOST="${2:?gpu22 host required}"; PORT=18233; SEED=202615300 ;;
  3) HOST="${2:?gpu22 host required}"; PORT=18234; SEED=202615400 ;;
  *) exit 2 ;;
esac
exec bash "$ROOT/qgf_v2/run_standard_collection.sh" "$HOST" "$PORT" "$SEED" 10 "standard_train10_seed$SEED"
