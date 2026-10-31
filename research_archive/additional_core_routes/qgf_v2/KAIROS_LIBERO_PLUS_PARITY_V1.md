# Kairos3.1-4B LIBERO-Plus baseline parity smoke v1

Frozen: 2026-10-25 03:27 CST

## Purpose

Run exactly one official closed-loop episode after the Kairos model-load release
gate. This is an infrastructure and baseline-parity smoke only. Its outcome is
not a baseline-rate estimate and is not QGF evidence.

## Frozen setting

- Backbone: official Kairos3.1-4B LIBERO-Plus checkpoint already SHA256-frozen.
- Benchmark source: the already pinned public LIBERO-Plus checkout used by the
  ImageWAM release gate; no task, asset, success, or action code is changed.
- Suite/category/task: `libero_mix` / `Background Textures` / task `0`.
- One trial, global/environment/model seed `10000`.
- Official external WAM adapter, dataset statistics, normalization, camera
  preprocessing, 20 inference steps, 10-step replanning, binary gripper, and
  official environment success predicate.
- One allocated A800 hosts the Kairos service and a second allocated A800 hosts
  the simulator. No other GPU or historical service may be used.

## Budget and evidence

- Expected wall time: 10-20 minutes from the measured 145-second model load.
- Hard limit: 45 minutes and 1.5 GPU-hours across the two allocated GPUs.
- Preserve launcher, server/evaluator logs, exact config and input hashes,
  result JSON, video, timing, GPU inventory, and all failures.
- Passing parity requires a complete official episode, finite legal actions,
  a result JSON, and a video. Episode success is reported but is not required
  for this one-episode infrastructure gate.
- Only after this smoke completes may the separately preregistered same-state
  native-N4 action-contract and diversity smoke begin.
