# Paired Diagnostic V1 Retry 1

The original step 1593640.369 failed before checkpoint construction,
environment creation, candidate inference, or robot actions because its wrapper
omitted the official `experiments/libero` directory from `PYTHONPATH`.

Retry 1 changes infrastructure only. It adds the exact official runtime path,
LIBERO config, offline asset variables, GCC 11 toolchain, and run-local cache
and temporary directories already used by the audited training collector. The
registered Python runner, model, checkpoint, 16 entries, seeds, actions,
horizon, contract, labels, thresholds, and budgets are unchanged. The failed
step and its elapsed cost remain preserved. No automatic retry follows this
one.
