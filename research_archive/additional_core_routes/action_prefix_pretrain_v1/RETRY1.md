# Deterministic CuBLAS Retry 1

The first two workers exited before the first optimizer update because
deterministic PyTorch requires `CUBLAS_WORKSPACE_CONFIG` on CUDA 10.2+.
Retry 1 adds only `CUBLAS_WORKSPACE_CONFIG=:4096:8`. Corpus, architecture,
three seeds, optimizer, mask schedule and 5000-update budget are unchanged.
The failed logs and charged seconds remain preserved in `dispatch_v1` and the
original process receipts. No further automatic retry is authorized.

