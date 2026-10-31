#!/usr/bin/env bash
set -u
echo "CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-unset}"
nvidia-smi --query-gpu=index,uuid,name,driver_version --format=csv,noheader
echo LIBS
ldconfig -p 2>/dev/null | grep -E 'lib(EGL|GLX)_nvidia|libEGL.so' || true
echo VENDORS
ls -l /usr/share/glvnd/egl_vendor.d /etc/glvnd/egl_vendor.d 2>/dev/null || true
echo DRIVER
find /usr/lib64 /usr/lib/x86_64-linux-gnu -maxdepth 1 -name 'libEGL*' -o -name 'libGLX_nvidia*' 2>/dev/null | sort | head -40
