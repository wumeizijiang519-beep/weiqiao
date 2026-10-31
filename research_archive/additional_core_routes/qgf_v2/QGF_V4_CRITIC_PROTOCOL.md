# QGF v4 Randomized-Intervention Critic Protocol

Frozen: 2026-10-24 09:44 CST, before latent export or critic training.

## Source

- Aggregate: `v4_intervention_train32_v1/summary.json`.
- Population: exactly 32 audited `open_microwave/demo_randomized` training-only
  episodes collected by uniformly committing one native N=4 proposal.
- Admission: aggregate audit valid, 32 unique seeds, and at least 6 successes
  and 6 failures. Observed admitted population is 25 successes and 7 failures.
- Only executed proposals receive observed returns. No label is assigned to an
  unexecuted proposal.

## Representation And Split

- Freeze UNITAS Florence-2 pooled visual-language state, proprioception and
  remaining-time features using the same 9216D encoder contract as QGF v3.
- Four-GPU export is sharded by aggregate episode index; every source and latent
  file is SHA256 verified before training.
- One episode-disjoint 24/8 split is selected without model results. Validation
  contains the 2 failures and 6 successes with the lowest SHA256 ordering under
  salt `qgf-v4-intervention-split-v1`; the remaining 5 failures and 19 successes
  form training. No checkpoint or threshold is selected on validation outcomes.
- State and action normalization is fit on training episodes only with equal
  total episode weight.

## Fixed Controls

- Three bootstrap seeds: `202623001`, `202623002`, `202623003`.
- Conditions: action-aware critic, same-target state-only critic, and action-
  shuffled critic. Shuffling is fixed within each training episode from the
  condition seed and never changes validation labels.
- Each condition runs exactly 10000 optimizer steps; the final checkpoint is
  reported. No held-out early stopping or best-checkpoint selection.
- Report episode-equal held-out finite-horizon target MSE and calibration,
  per-seed action-aware minus state-only/shuffle differences, action-shuffle
  sensitivity, runtime and GPU-hours.

## Decision Rule

Admit a selector to fresh matched online validation only if action-aware beats
both state-only and action-shuffled controls on held-out episode-equal error in
at least 2 of 3 bootstrap seeds and the aggregate difference is positive. This
diagnostic cannot itself establish robot success-rate improvement. Otherwise
freeze the result as no stable action-value evidence for this configuration.

