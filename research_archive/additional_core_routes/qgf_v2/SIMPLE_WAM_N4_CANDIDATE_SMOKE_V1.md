# Simple-WAM Native N4 Candidate Smoke V1

## Purpose

This is an engineering qualification gate, not evidence that QGF improves robot success.
It tests whether the frozen Simple-WAM checkpoint can produce a reproducible, diverse native
candidate set from exactly one held observation without committing any model action.

## Frozen setup

- Source: Simple-WAM commit `396cba18c318bc33a1ef42513b85298e3016e28a`.
- Checkpoint: frozen `libero_joint_2cam224_1e-4.pt` used by the passed parity run.
- Benchmark: `libero_10`, task 0, environment seed 10000, initial state index 0.
- Observation: after the official 30 dummy wait steps; no model action is submitted.
- Native candidate seeds: `[10000, 11000, 12000, 13000]`.
- Inference: 10 denoising steps, action horizon 32, BF16, official dual-camera and state
  preprocessing, frozen future-video noise, compiled action inference, text encoder offload.
- Cost: one A800, 45 wall-minute / 0.75 GPU-hour hard limit.

## Required artifacts

- Raw candidate chunks and candidate-0 replay in NPZ form.
- Candidate hashes, shape, finite/binary-gripper checks, pairwise mean absolute differences,
  inference latencies, peak CUDA memory, checkpoint/config hashes, and a JSON report.
- Candidate 0 is generated first, all other candidates are generated, then candidate 0 is
  replayed from the same held observation and prompt cache.

## Pass criteria

All criteria are fixed before execution:

1. Candidate tensor shape is exactly `[4, 32, 7]`.
2. Every value is finite and every gripper value is binary (`-1` or `+1`).
3. All four native chunks have distinct SHA256 hashes.
4. Minimum pairwise mean absolute difference is strictly positive.
5. Candidate-0 replay maximum absolute error is at most `1e-6`.
6. No model action is committed to the environment.

Failure freezes this candidate interface/configuration. Thresholds, seeds, task, checkpoint,
and observation may not be changed to rescue the gate.
