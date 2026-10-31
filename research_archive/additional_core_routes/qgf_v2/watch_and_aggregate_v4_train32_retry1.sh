#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_v2
RUN="$ROOT/runs/v4_intervention_train32_shard3_retry1"
LOG="$ROOT/v4_intervention_train32_v1/recovery_aggregate.log"
DEADLINE=$(( $(date +%s) + 5400 ))

mkdir -p "$ROOT/v4_intervention_train32_v1"
while [[ ! -f "$RUN/COLLECTION_COMPLETE" || ! -f "$RUN/audit.json" ]]; do
  if (( $(date +%s) >= DEADLINE )); then
    printf '%s timed out waiting for shard3 retry\n' "$(date -Is)" >> "$LOG"
    exit 124
  fi
  if [[ -f "$RUN/FAILED" && ! -f "$RUN/COLLECTION_COMPLETE" ]]; then
    printf '%s shard3 retry failed before immutable completion\n' "$(date -Is)" >> "$LOG"
    exit 2
  fi
  sleep 20
done

printf '%s shard3 retry complete; aggregating exact replacement set\n' "$(date -Is)" >> "$LOG"
/public/home/wangsenbao221/.conda/envs/pi05_new/bin/python \
  "$ROOT/aggregate_v4_train32_retry1.py" >> "$LOG" 2>&1
sha256sum "$ROOT/v4_intervention_train32_v1/summary.json" \
  > "$ROOT/v4_intervention_train32_v1/summary.sha256"
printf '%s aggregate complete\n' "$(date -Is)" >> "$LOG"
