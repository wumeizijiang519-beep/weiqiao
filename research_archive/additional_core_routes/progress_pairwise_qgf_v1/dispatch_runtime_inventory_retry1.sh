#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
P=$R/progress_pairwise_qgf_v1
PROCESS=$P/runtime_inventory_process_retry1
REG=$P/RUNTIME_INVENTORY_RETRY1_REGISTRATION.json
test "$SLURM_JOB_ID" = 1593640
test ! -e "$P/runtime_inventory_v1"
test ! -e "$PROCESS"
test "$(sha256sum "$P/runtime_inventory.py" | cut -d' ' -f1)" = 7aa58ecb90852d3efdf38555c08201bc331b659ea10acf4dba4e8af9e1bcdda6
test "$(sha256sum "$P/RUNTIME_INVENTORY_REPAIR_V1.md" | cut -d' ' -f1)" = cbafb970bc5d0def441e59a6417075c6d48264de822a734b8a7fe6644410eb16
test "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$REG")" = RUNTIME_INVENTORY_RETRY1_USER_AUTHORIZED
mkdir "$PROCESS"
date -Is > "$PROCESS/start_time"
set +e
srun --jobid=1593640 --overlap --ntasks=1 --cpus-per-task=4 --mem=12G \
  --gres=gpu:1 --time=00:05:00 \
  env RUNTIME_INVENTORY_SOURCE_SHA256=7aa58ecb90852d3efdf38555c08201bc331b659ea10acf4dba4e8af9e1bcdda6 \
      MANIFEST_SHA256=aa20335f10dfe3b39c6ebf0ce3a4f77c24d694f9a2a5e7672cf90fb08120e256 \
  bash "$P/run_runtime_inventory.sh" > "$PROCESS/srun.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$PROCESS/exit_code"
date -Is > "$PROCESS/end_time"
exit "$rc"
