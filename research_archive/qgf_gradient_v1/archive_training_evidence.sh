#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
test "$SLURM_JOB_ID" = 1593640
OUT=$R/evidence_exports/qgf_training288_raw_20261026.tar
test ! -e "$OUT"
test ! -e "$OUT.partial"
test "$(cat "$R/qgf_gradient_v1/training288_v2_remaining/dispatcher_exit_code")" = 0
printf 'job=%s step=%s host=%s zero_gpu=1 scope=immutable_training_raw_archive\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)"
tar -cf "$OUT.partial" -C "$R" \
  runs/qgf_gradient_collector_integrity_v1 \
  runs/qgf_gradient_training288_v1_shard0 \
  runs/qgf_gradient_resume_v2_one \
  runs/qgf_gradient_remaining257_v2_shard0 \
  runs/qgf_gradient_remaining257_v2_shard1 \
  runs/qgf_gradient_remaining257_v2_shard2 \
  runs/qgf_gradient_remaining257_v2_shard3
mv "$OUT.partial" "$OUT"
sha256sum "$OUT" > "$OUT.sha256"
stat -c '%s' "$OUT" > "$OUT.bytes"
printf 'ARCHIVE_COMPLETE_NOT_LOCAL_TRANSFER\n'
