# QGF v3 WAM-Latent Protocol

## Purpose

The completed RGB-statistics diagnostic did not establish action-value evidence.
This separately named revision tests whether the frozen UNITAS representation used
by its action decoder supports action-conditioned value learning. It does not
reinterpret or overwrite `small_data_cv_v1`.

## Representation

- Frozen local Florence-2 encoder shipped with the fixed UNITAS checkpoint.
- Exact three stored RGB views and the task instruction, with the same successful
  ALOHA trajectory prompt used by UNITAS inference.
- Pool conditioned primary visual tokens, language tokens, and per-view raw image
  tokens. Record exact dimensions, hashes, finite checks, latency and deterministic
  repeat error.
- Joint/TCP/time features remain explicit auxiliary state inputs. Candidate action
  chunks remain full `10 x 16` inputs and are never outcome-masked.

## Admission gates

1. One frozen trajectory, three preregistered frames: all features finite, shapes
   fixed, exact repeat error zero, and projected full-60 extraction no more than
   8 GPU-hours. Failure stops this representation.
2. Export all frozen 60 trajectories without changing their labels or folds.
3. Compare action-aware critic against the same-target state-only control and an
   action-shuffle diagnostic at fixed final steps across the existing four folds
   and seeds 0/1/2. No fold or checkpoint selection.
4. Online matched smoke is admitted only if action-aware OOF performance beats
   state-only in all three seed aggregates and action-shuffle response is nonzero.

## Claims and exclusions

The 60 trajectories contain only four independent failures, so this remains a
diagnostic. Action-shuffle response is not causal ranking evidence. No snapshot
restore branch labels, episode oracle, engineering seeds or formal seeds are used.
Negative results are retained. Online success rate remains the first efficacy
claim, and formal evaluation is permitted only after fresh matched improvement.
