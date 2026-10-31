# Kairos Native N4 Candidate Smoke V1

## Scope

- Backbone: Kairos3.1-4B LIBERO-Plus official checkpoint.
- Task: `libero_mix / Background Textures / task0`.
- Environment seed: `10000`; initial state index: `0`.
- This is a zero-action engineering gate. No candidate is committed to the environment.

## Frozen candidate contract

- Advance the official environment with exactly 30 dummy wait actions, matching parity.
- Capture one observation and generate all candidates from that unchanged observation.
- Native diffusion seeds: `[10000, 11000, 12000, 13000]`.
- Inference steps: `20`; action horizon: official configured horizon (`16`).
- Generate candidate0 once more after all four candidates to detect non-determinism or hidden server memory.

## Pass criteria

- All five inference requests complete without service or action errors.
- Every N4 chunk has shape `[16, 7]`, contains only finite values, and has binary gripper values.
- The four chunks have four distinct SHA256 hashes and positive pairwise action diversity.
- Repeated candidate0 maximum absolute error is at most `1e-6`.
- Persist raw candidates, hashes, pairwise metrics, per-request latency, peak GPU memory, config and SHA256 evidence.

Passing this smoke establishes only candidate-interface eligibility. It is not QGF effectiveness evidence.
