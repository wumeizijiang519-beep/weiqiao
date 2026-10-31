# Simple-WAM Visual RL/QGF Online V2: Support Abstention

## Motivation

Online V1 stopped before completion when the shared shadow critic rejected an
out-of-training-support candidate0 in the uniform-random arm. This is a
deployment-contract failure, not an outcome comparison. V1 and all attempted
scene-arm evidence remain frozen.

## Prospective cohort

- Use only untouched validation scene indices 4 through 63.
- Exclude indices 0 through 3 because at least one V1 arm was attempted there;
  exclusion does not depend on success or reward.
- Keep the four frozen arms, arm-order seed 202644501, random seed 202644502,
  N4 native bank, denoising budget, token, critic ensemble, QGF weight, support
  bounds, horizon, and commit threshold unchanged.

## Frozen support policy

- candidate0 and uniform-random are baselines and never require critic support.
- critic-rerank ranks only supported native candidates; if none are supported,
  it abstains to candidate0.
- visual-QGF ranks only supported guided candidates; if none are supported, it
  abstains to candidate0.
- Every decision records native/guided support masks and an abstention flag.
- No support bound is expanded, clipped, or estimated from online data.

## Analysis

All 60 scenes and 240 scene-arm tasks must complete. Use the already frozen
paired bootstrap seed 202644601 with 10,000 draws. Online admission still
requires visual-QGF lower CI greater than zero versus candidate0 and
uniform-random, and at least -0.05 versus critic-rerank. Abstention rate is
reported as a safety metric, not an endpoint.
