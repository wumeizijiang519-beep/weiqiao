#!/usr/bin/env bash
set -euo pipefail

ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022/simplewam_visual_rl_v1
RUN="$ROOT/online_execution_v2_support_abstention"
STAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE="$ROOT/online_execution_v2_support_abstention_infra_partial_dual_oom_$STAMP"

mkdir -p "$ARCHIVE"
for task_dir in "$RUN"/task_*; do
  [[ -d "$task_dir" ]] || continue
  [[ -f "$task_dir/SIMPLEWAM_VISUAL_QGF_ONLINE_TASK_COMPLETE" ]] && continue
  task_name=$(basename "$task_dir")
  mv "$task_dir" "$ARCHIVE/$task_name"
  task_log="$RUN/${task_name}.log"
  [[ -f "$task_log" ]] && mv "$task_log" "$ARCHIVE/${task_name}.log"
done

for evidence in \
  online_v2_accelerated_dispatch.log \
  online_v2_accelerated_gpu_0_srun.log \
  online_v2_accelerated_gpu_1_srun.log \
  online_v2_accelerated_gpu_2_srun.log \
  online_v2_accelerated_gpu_3_srun.log; do
  [[ -f "$ROOT/$evidence" ]] && cp -p "$ROOT/$evidence" "$ARCHIVE/$evidence"
done

sacct -j 1677369.16,1677369.17,1677369.18,1677369.19 \
  --format=JobID,State,ExitCode,Elapsed,AllocTRES,MaxRSS -P > "$ARCHIVE/SACCT.txt" || true
find "$ARCHIVE" -type f -print0 | sort -z | xargs -0 sha256sum > "$ARCHIVE/SHA256SUMS"
printf '%s\n' "$ARCHIVE"
