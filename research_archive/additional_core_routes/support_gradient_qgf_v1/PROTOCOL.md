# Support-Gradient QGF V1

## Motivation

Outcome-blind mean support energy and ensemble uncertainty did not rank a
discrete candidate bank, while supervised cross-group critics repeatedly
overfit. This route tests a different intervention: use the differentiable
support energy only as a local projection direction from candidate0. A failed
global selector does not imply that a small local support gradient is useless.

## Frozen Guidance

- Use all three audited outcome-blind action encoders; none reads reward,
  success, progress, validation, or formal outcomes.
- Energy is the ensemble-mean masked reconstruction MSE at fixed positions
  `0,3,...,30` on a normalized `32x7` action prefix.
- Compute the gradient at candidate0. Gripper values are immutable. Normalize
  the six continuous-action gradient and construct four candidates at fixed
  fractions `0.25,0.50,0.75,1.00` of the already frozen family support median
  radius, clipped to the existing normalized action bounds. Zero/non-finite
  gradients fail closed.
- Candidate0 and native candidates remain unchanged. No outcome determines the
  gradient, scale, branch order, or candidate inclusion.

## Prospective Diagnostic

- Select new training-only physical groups by a result-independent hash after
  excluding every group used by prior branches. No replacement or task
  substitution is allowed.
- Every branch is a fresh environment replaying the identical frozen prefix;
  physical state, policy input, RNG, commit error `<=1e-6`, artifacts, and
  official terminal/success follow the Runtime-Anchored contract.
- Pilot one fixed group first. A clean engineering audit permits the remaining
  preregistered groups automatically.
- Primary endpoint is official success. Secondary endpoint is frozen horizon-32
  progress. Admission requires at least 12 complete groups and either four
  binary-discordant groups across two families or positive physical-group
  bootstrap lower 95% progress improvement over candidate0 and uniform-random
  in at least two families.

Passing this diagnostic permits a new held-out online support-gradient QGF
validation. It is not itself online efficacy. Failure freezes the route without
step-size, mask, checkpoint, group, or horizon tuning.

## Execution Budget

The audited fixed pilot and remaining 15 groups share a 28,800 allocated
GPU-second cap including failures. After pilot audit PASS, the remaining groups
run once in frozen index order. Exact dummy/prefix replay mismatch is retained
as unavailable; it does not authorize replacement or retry.
