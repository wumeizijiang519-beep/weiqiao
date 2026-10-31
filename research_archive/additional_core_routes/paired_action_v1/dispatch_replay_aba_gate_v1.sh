#!/usr/bin/env bash
set -euo pipefail
C=/public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1
cd "$C"
test ! -e replay_aba_gate_v1
rm -rf replay_aba_gate_v1_process
mkdir replay_aba_gate_v1_process
date -Ins > replay_aba_gate_v1_process/launch_time
nohup bash -lc '
  srun --jobid=1593640 --overlap --nodes=1 --ntasks=1 --cpus-per-task=8 \
    --mem=45G --gres=gpu:1 --time=00:21:40 bash -lc \
    "export CUDA_VISIBLE_DEVICES=0; tr -d '\''\r'\'' < /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/run_replay_aba_gate_v1.sh | bash"
  rc=$?
  echo "$rc" > /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/replay_aba_gate_v1_process/exit_code
  date -Ins > /public/wangsenbao221/pqr/qgf_mainstream_20261022/paired_action_v1/replay_aba_gate_v1_process/end_time
  exit "$rc"
' > replay_aba_gate_v1_srun.log 2>&1 < /dev/null &
echo "$!" > replay_aba_gate_v1_process/launcher_pid
cat replay_aba_gate_v1_process/launcher_pid
