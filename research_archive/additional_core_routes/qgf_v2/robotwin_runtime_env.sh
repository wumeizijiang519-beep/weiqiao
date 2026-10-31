ROOT=/public/wangsenbao221/pqr/qgf_mainstream_20261022
SITE="$ROOT/envs/robotwin_py310_site"
TOOLCHAIN="$ROOT/toolchains/gcc11"
export PYTHONPATH="$ROOT/robotwin_host_compat:$ROOT/envs/warp_host_compat:$ROOT/deps/curobo-0.7.8/src:$SITE:$ROOT/backbones/UNITAS/src:$ROOT/backbones/UNITAS:$ROOT"
export CUDA_HOME=/usr/local/cuda-12.2
export CC="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-gcc" CXX="$TOOLCHAIN/bin/x86_64-conda-linux-gnu-g++"
export PATH="$TOOLCHAIN/bin:$CUDA_HOME/bin:$SITE/bin:$PATH"
export LD_LIBRARY_PATH="$TOOLCHAIN/lib:$CUDA_HOME/lib64:$SITE/nvidia/cuda_runtime/lib:${LD_LIBRARY_PATH:-}"
export TORCH_EXTENSIONS_DIR="$ROOT/envs/torch_extensions_curobo078_host_gcc11"
export CPATH=/public/home/wangsenbao221/.conda/envs/pi05_new/include/python3.10
export CPLUS_INCLUDE_PATH="$CPATH"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
