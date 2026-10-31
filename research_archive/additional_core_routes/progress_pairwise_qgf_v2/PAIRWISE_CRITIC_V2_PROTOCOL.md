# Progress-Pairwise Critic V2 Preregistration Draft

## Release Preconditions

- Collection and independent artifact audit must both pass.
- At least 24 of 32 V2 groups must be complete, including at least 12 of 16
  locked-confirmation groups.
- Before model and source hashes are frozen, code may read only the 14 frozen
  complete V1 groups and the released V2 development labels. Confirmation
  artifacts are receipts only and must not be decoded, summarized, or used for
  architecture, normalization, checkpoint, or threshold selection.

## Fixed Development Study

- The unit of splitting and weighting is the physical input group. All eight
  candidates from one group remain together.
- Four folds are formed by sorting
  `sha256(episode_id + "|pairwise-critic-v2")` within each task family and
  assigning round-robin. No outcome-dependent reassignment is allowed.
- Seeds are `202642001`, `202642002`, and `202642003`.
- Primary target is the horizon-32 within-group pairwise preference. Absolute
  progress differences at or below `1e-6` are ties and excluded. Horizon 16 is
  secondary and cannot select a model.
- Deployment-visible inputs are the frozen boundary representation, the first
  16 normalized 14-D candidate actions, and candidate-kind metadata. Outcome,
  success, future execution length, final state, progress, and simulator-only
  predicates are forbidden inputs.

## Models And Controls

- Action-aware model: one fixed state trunk and action-prefix trunk joined by
  feature-wise linear modulation followed by a bilinear state-action score.
  This is one architecture, not a post-hoc choice between FiLM and bilinear
  variants.
- State-only control: the same state trunk, width, optimizer, update count, and
  checkpoint rule without candidate action content.
- Permutation control: the action-aware model after a seed-fixed within-bank
  action permutation while labels remain fixed.
- Normalizers are fit on each training fold only. WAM remains frozen and no
  actor gradient is permitted.
- Exact update count and dimensions are frozen after a development-only cost
  pilot and before any locked-confirmation label is released.

## Development Gate

- Primary metric is physical-group-equal held-out pairwise accuracy at horizon
  32, pooled only after every group has exactly one held prediction per seed.
- For every seed, action-aware accuracy must exceed both controls.
- With 10,000 physical-group bootstrap draws and seed `202642101`, the lower
  95% confidence bound of action-aware minus each control must exceed zero.
- Within-bank action substitution must change the action-aware score beyond
  the frozen numerical tolerance for at least 90% of non-tied comparisons.
- Any failed seed freezes the development result. No added seed, update,
  architecture, group, or threshold is allowed.

## Locked Confirmation

- Only after the development gate passes are the model/source/normalizer,
  training receipt hashes, and confirmation evaluator frozen and the
  confirmation labels released once.
- The frozen models are evaluated without fitting or checkpoint selection on
  the 16 locked groups. Every seed must beat both controls on group-equal
  accuracy and both paired group-bootstrap lower confidence bounds must exceed
  zero.
- Failure freezes `NO_STABLE_V2_PROGRESS_PAIRWISE_CRITIC`. Passing only admits
  a separately preregistered same-compute online QGF experiment; it is not an
  online efficacy result.

No GPU training is authorized by this draft alone. A clean collection audit,
sealed development corpus, source hashes, fixed cost, and execution manifest
are required first.
