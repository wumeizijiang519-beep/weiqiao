#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
test "$SLURM_JOB_ID" = 1593640
test ! -e "$C/replay_aba_gate_v2"
cd "$C"
tr -d '\r' < REPLAY_ABA_GATE_V2_SHA256SUMS | sha256sum -c -
export PYTHONPATH="$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a/third_party/LIBERO-plus:$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a:$R/qgf_gradient_v1:${PYTHONPATH:-}"
export MUJOCO_GL=egl PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8
timeout 1200 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$C/run_replay_aba_gate_v2.py"
