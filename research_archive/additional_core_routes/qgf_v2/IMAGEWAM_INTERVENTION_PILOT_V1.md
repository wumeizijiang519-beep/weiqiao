# ImageWAM randomized intervention pilot v1

Frozen: 2026-10-24 19:20 CST, before any pilot policy query.

## Purpose

Qualify training data for an ImageWAM-specific action-aware critic. This is
training-only randomized intervention, not online QGF evaluation and not an
oracle. Only the selected candidate is executed and receives its observed
finite-horizon return. Unexecuted candidates receive no label.

## Frozen model and environment

- ImageWAM FLUX.2-4B official LIBERO-plus checkpoint step 34720.
- LIBERO-plus source commit 4976dc30028e805ff8094b55501d532c48fec182.
- Task suite libero_10, task id 0.
- Action horizon 16, replan interval 12, wait 30, max policy steps 700.
- Candidate seeds [10000, 11000, 12000, 13000].
- No decoded-action perturbation, reward shaping, snapshot branching or oracle.

## Pilot episodes

Four fresh training-only episodes split over two independent workers:

- shard0: initial-state indices [1,2], environment seeds
  [202630101,202630102], selection seeds [202630501,202630502].
- shard1: initial-state indices [3,4], environment seeds
  [202630201,202630202], selection seeds [202630601,202630602].

These episodes and all attempted seeds are permanently excluded from validation
and formal evaluation. Selection is uniform among the four candidates at every
replanning boundary.

## Required evidence

For every replan save the current RGB observations and proprioception, all four
native candidate chunks, their hashes, selected index, selected chunk, exact
executed prefix, actual execution length, per-step environment rewards, observed
finite-horizon return, and next observation. Save complete videos and all logs.

The pilot passes only if:

1. all four episodes complete without infrastructure/model errors;
2. all candidate tensors are finite [4,16,7] with four distinct hashes;
3. selected/committed action max absolute error is <=1e-6;
4. gripper actions satisfy the official binary contract;
5. all transition arrays satisfy R current observations, R chunks and R next
   observations with explicit executed lengths and rewards;
6. aggregate outcomes contain at least one success and one failure.

If the pilot fails class diversity, freeze this task/config as negative evidence.
Do not extend, pick another seed, or lower the gate.

## Budget

Measured official candidate0 episode was 157.49 seconds. N4 adds roughly three
warm inference calls per replan. Estimate 8-15 minutes wall time with two A800
workers and 0.3-0.5 A800 GPU-hours. Hard cap 35 minutes wall / 1.2 GPU-hours.
No stage beyond this pilot is authorized until its audit passes.

## Next gate

Only after PASS, preregister a bounded multi-shard training collection and then
episode-disjoint fixed-final-step OOF critics comparing action-aware,
same-target state-only, and within-set selected-index permutation/action-shuffle.
No matched online QGF validation begins before stable action evidence.

