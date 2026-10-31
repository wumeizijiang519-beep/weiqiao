#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/paired_action_v1
test "$SLURM_JOB_ID" = 1593640
test ! -e "$C/paired_diagnostic_v1"
cd "$C"
tr -d '\r' < PAIRED_DIAGNOSTIC_V1_SHA256SUMS | sha256sum -c -
test "$(sha256sum "$R/qgf_gradient_v1/core.py" | awk '{print $1}')" = 1b30c5d66f3958b05aa9dcc582f2eef42ee03a308300260fbe0b6d74fc0f6d29
test "$(sha256sum "$R/qgf_gradient_v1/data_contract.py" | awk '{print $1}')" = 39301bf91924133f275ca4780a751a0c37c4787c5164fa45bb182e5d20bb26df
test "$(sha256sum "$R/qgf_gradient_v1/wam_runtime.py" | awk '{print $1}')" = 5c4b354b5903d6c4b955e557bbdd1bbec07bc6f6eedec35874bfda0211e3dad0
export PYTHONPATH="$R/qgf_gradient_v1:$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a/third_party/LIBERO-plus:$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a:${PYTHONPATH:-}"
export MUJOCO_GL=egl PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=8
timeout 7100 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u \
  "$C/run_paired_diagnostic_v1.py" --run "$C/paired_diagnostic_v1"
