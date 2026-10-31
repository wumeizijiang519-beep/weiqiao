#!/usr/bin/env bash
set -euo pipefail
ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
RUN_NAME="${3:-robot_restore_smoke_retry2}"
if [[ ! "$RUN_NAME" =~ ^robot_restore_smoke_[a-zA-Z0-9_]+$ ]]; then
  exit 2
fi
OUT="$ROOT/qgf_v2/$RUN_NAME"
if [[ -e "$OUT/result.json" ]]; then exit 2; fi
mkdir -p "$OUT"
exec >"$OUT/launcher.log" 2>&1
SITE="$ROOT/envs/robotwin_py310_site"
TOOLCHAIN="$ROOT/toolchains/gcc11"
export PYTHONPATH="$ROOT/robotwin_host_compat:$ROOT/envs/warp_host_compat:$ROOT/deps/curobo-0.7.8/src:$SITE:$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
export CUDA_HOME=/usr/local/cuda-12.2
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc"
export CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export PATH="$TOOLCHAIN/bin:$CUDA_HOME/bin:$SITE/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib:$CUDA_HOME/lib64:$SITE/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
export TORCH_EXTENSIONS_DIR="$ROOT/envs/torch_extensions_curobo078_host_gcc11"
export CPATH=/public/home/wangsenbao221/.conda/envs/pi05_new/include/python3.10
export CPLUS_INCLUDE_PATH="$CPATH"
sha256sum "$0" "$ROOT/qgf_v2/robot_restore_smoke.py" >"$OUT/checksums.sha256"
timeout 900 /public/home/wangsenbao221/.conda/envs/pi05_new/bin/python -u \
  "$ROOT/qgf_v2/robot_restore_smoke.py" --root "$ROOT/RoboTwin_fixed" \
  --host "${1:?dynamic server host required}" --port "${2:?server port required}" \
  --output "$OUT/result.json" "${@:4}"
