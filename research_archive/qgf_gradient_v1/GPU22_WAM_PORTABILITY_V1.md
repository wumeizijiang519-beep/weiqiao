# GPU22 WAM Portability V1

## Purpose

Qualify one explicitly allocated and idle A800 on `gpu22/job1598338` for the
frozen Simple-WAM runtime before the platform cutoff. This is infrastructure
acceleration only. It executes no robot action or cohort episode and cannot be
used as QGF evidence.

## Frozen contract

- Host `gpu22`, physical GPU0,
  UUID `GPU-f39a66d0-5c4f-f2ca-4e60-5f52ed1b78db`.
- UID2292 and cgroup `/slurm/uid_2292/job_1598338/step_extern` must match.
- GPU must be idle at launch; expose exactly physical GPU0.
- Use the unchanged Simple-WAM checkpoint, Torch runtime, dtype, compiler,
  `zero_action_probe.py`, `core.py`, seed, cache contract, and Stage0 reference.
- Run EGL preflight, then the zero-action probe. Compare every saved native
  action, normalized action, and support-basis value to frozen Stage0 arrays at
  maximum absolute error `1e-6`.
- No cohort observation, environment transition, critic, or QGF guidance.

One attempt is allowed, with a hard 1500-second limit and one GPU. Any error,
nonzero exit, or numerical mismatch freezes this resource as unusable for WAM
work. Existing gpu1 work is not interrupted. Actual elapsed time, including a
failure, is charged to the integration/resource ledger.
