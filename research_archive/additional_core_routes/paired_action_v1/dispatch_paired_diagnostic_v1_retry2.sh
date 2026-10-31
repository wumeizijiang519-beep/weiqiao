#!/usr/bin/env bash
set -euo pipefail
C=/public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1
cd "$C"
test ! -e paired_diagnostic_v1_retry2
test ! -e paired_diagnostic_v1_retry2_process
mkdir paired_diagnostic_v1_retry2_process
date -Ins > paired_diagnostic_v1_retry2_process/launch_time
nohup bash -lc '
  srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
    --mem=45G --gres=gpu:1 --time=01:53:00 bash -lc \
    "export CUDA_VISIBLE_DEVICES=0; tr -d '\''\r'\'' < /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/run_paired_diagnostic_v1_retry2.sh | bash"
  rc=$?
  echo "$rc" > /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/paired_diagnostic_v1_retry2_process/exit_code
  date -Ins > /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/paired_diagnostic_v1_retry2_process/end_time
  exit "$rc"
' > paired_diagnostic_v1_retry2_srun.log 2>&1 < /dev/null &
echo "$!" > paired_diagnostic_v1_retry2_process/launcher_pid
cat paired_diagnostic_v1_retry2_process/launcher_pid
