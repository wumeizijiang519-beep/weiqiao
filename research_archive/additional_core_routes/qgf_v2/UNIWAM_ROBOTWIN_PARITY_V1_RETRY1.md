# UniWAM RoboTwin Parity V1 Retry 1

- Parent run `runs/uniwam_robotwin_parity_v1` failed before model
  construction, environment construction, or action execution.
- Root cause 1: the launcher selected nonexistent generic `gcc`/`g++`
  paths instead of the already validated prefixed GCC 11 binaries.
- Root cause 2: the Slurm launch inherited two tasks, duplicating the
  pre-model import failure.
- This retry changes only `CC`, `CXX`, and `CUDAHOSTCXX` to the validated
  `x86_64-conda-linux-gnu-gcc/g++` binaries and launches with `--ntasks=1`.
- Task, task config, seed, checkpoint, assets, observation/action processing,
  inference settings, reward, success criterion, and resource ceilings remain
  identical to `UNIWAM_ROBOTWIN_PARITY_V1.md`.
