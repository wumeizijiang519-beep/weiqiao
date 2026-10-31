#!/usr/bin/env bash
set -euo pipefail
C=/public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1
cd "$C"
test ! -e dynamic_aba_gate_v4
rm -rf dynamic_aba_gate_v4_process
mkdir dynamic_aba_gate_v4_process
date -Ins > dynamic_aba_gate_v4_process/launch_time
nohup bash -lc '
  srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
    --mem=45G --gres=gpu:1 --time=00:21:40 bash -lc \
    "export CUDA_VISIBLE_DEVICES=0; tr -d '\''\r'\'' < /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/run_dynamic_aba_gate_v4.sh | bash"
  rc=$?
  echo "$rc" > /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/dynamic_aba_gate_v4_process/exit_code
  date -Ins > /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/dynamic_aba_gate_v4_process/end_time
  exit "$rc"
' > dynamic_aba_gate_v4_srun.log 2>&1 < /dev/null &
echo "$!" > dynamic_aba_gate_v4_process/launcher_pid
cat dynamic_aba_gate_v4_process/launcher_pid
