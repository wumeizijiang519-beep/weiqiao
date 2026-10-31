# ImageWAM Native N4 Candidate Smoke v1

Frozen: 2026-10-24 19:06 CST, before candidate generation.

## Purpose

Test whether the released ImageWAM FLUX.2-4B policy exposes a finite,
reproducible, same-observation native candidate interface suitable for later
equal-compute candidate0/random/QGF comparison. This is an engineering gate,
not online improvement evidence.

## Frozen query

- Reuse the passed ImageWAM/LIBERO-Plus release stack and checkpoint step
  `34720` from the baseline-parity smoke.
- Suite/task: `libero_10`, task id `0`; environment/global seed `10000`.
- Observation: official initial state after the unchanged 30 dummy wait steps.
  No policy action is executed.
- Candidate seeds: `[10000, 11000, 12000, 13000]`; seed `10000` is candidate0
  and preserves the baseline policy contract.
- Generate all four candidates from the exact same observation, proprioception,
  task text, model weights, memory state, action horizon `16`, and inference
  configuration. No decoded-action perturbation is allowed.
- Repeat candidate0 once from the same inputs to audit deterministic seed
  replay. Save all raw decoded chunks, images, hashes, timings, and config.

## Admission gate

Pass only if every chunk is finite with shape `[16,7]`, all four hashes are
distinct, repeated candidate0 has maximum absolute error `<=1e-6`, gripper
values obey the released binarized contract, and median pairwise mean absolute
action difference is at least `1e-4`. Report minimum/median/mean pairwise
difference and per-candidate latency. Any failure freezes this exact seeded
configuration without changing seeds or thresholds.

Passing this gate admits only a separately preregistered training-only random
intervention/critic compatibility stage. The smoke task/seed cannot be reused
for critic training, method validation, or formal evaluation.

## Budget

One allocated idle A800, at most 20 wall-minutes and 0.34 GPU-hours. The full
checkpoint is loaded once; no simulator rollout or reward query is made.
