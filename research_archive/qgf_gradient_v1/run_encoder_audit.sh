#!/usr/bin/env bash
set -euo pipefail
R=/public/wangsenbao221/pqr/qgf_mainstream_20261022
C=$R/qgf_gradient_v1
S=$R/backbones/Simple-WAM-396cba18c318bc33a1ef42513b85298e3016e28a
CONTROL=$1
test "$SLURM_JOB_ID" = 1593640
case ",$CUDA_VISIBLE_DEVICES," in *,0,*) ;; *) exit 41;; esac
test -z "$(nvidia-smi -i 0 --query-compute-apps=pid --format=csv,noheader)"
test ! -e "$CONTROL"
mkdir "$CONTROL"
START=$(date +%s)
finish() {
  rc=$?
  printf '%s\n' "$rc" > "$CONTROL/process_exit_code"
  printf '%s\n' "$(($(date +%s)-START))" > "$CONTROL/charged_gpu_seconds"
  date -Is > "$CONTROL/end_time"
  if [ "$rc" -eq 0 ]; then touch "$CONTROL/PROCESS_COMPLETE"; else touch "$CONTROL/PROCESS_FAILED"; fi
}
trap finish EXIT
date -Is > "$CONTROL/start_time"
printf 'job=%s step=%s host=%s physical_gpu=0\n' "$SLURM_JOB_ID" "$SLURM_STEP_ID" "$(hostname)" > "$CONTROL/allocation.txt"
export CUDA_VISIBLE_DEVICES=0 OMP_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$C:$S/third_party/LIBERO-plus:$S:$S/experiments/libero"
export LIBERO_CONFIG_PATH="$S/third_party/LIBERO-plus/.libero"
export DIFFSYNTH_MODEL_BASE_PATH="$R/checkpoints" DIFFSYNTH_SKIP_DOWNLOAD=true
export HF_HOME="$R/cache/simplewam-hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TORCH_HOME="$R/cache/simplewam-torch"
export CC="$R/toolchains/gcc11/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$R/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++" CUDAHOSTCXX="$R/toolchains/gcc11/bin/x86_64-conda-linux-gnu-g++"
export LD_LIBRARY_PATH="$R/toolchains/gcc11/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export TMPDIR
TMPDIR=$(mktemp -d /tmp/qgf-encoder-audit-XXXXXX)
export TRITON_CACHE_DIR="$CONTROL/cache/triton" TORCHINDUCTOR_CACHE_DIR="$CONTROL/cache/inductor"
export NUMBA_CACHE_DIR="$CONTROL/cache/numba" MPLCONFIGDIR="$CONTROL/cache/matplotlib" XDG_CACHE_HOME="$CONTROL/cache/xdg"
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR" "$NUMBA_CACHE_DIR" "$MPLCONFIGDIR"
test -f "$C/ENCODER_AUDIT_REGISTRATION.json"
"$R/runtime/simplewam_inference_py310_v2/bin/python" -c 'import json,pathlib,hashlib; p=pathlib.Path("/public/wangsenbao221/pqr/qgf_mainstream_20261022/qgf_gradient_v1"); r=json.loads((p/"ENCODER_AUDIT_REGISTRATION.json").read_text()); assert all(hashlib.sha256((p/n).read_bytes()).hexdigest()==v for n,v in r["source_sha256"].items()); d=p/"training288_v2_remaining/DATASET_RESULT.json"; assert hashlib.sha256(d.read_bytes()).hexdigest()==r["dataset_sha256"]; assert json.loads(d.read_text())["status"]=="ADMIT_FOR_RL_QUALIFICATION"'
timeout 1200 "$R/runtime/simplewam_inference_py310_v2/bin/python" -u "$C/audit_current_features.py" --run "$CONTROL/audit"
test -f "$CONTROL/audit/ENCODER_AUDIT_PASS"
sha256sum "$CONTROL/audit/REPORT.json" "$CONTROL/audit/features.npz" > "$CONTROL/RESULT_SHA256SUMS"
