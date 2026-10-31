# Runtime-Delta QGF V1

## Motivation

The frozen outcome-blind action encoder collapsed in Setwise-Contrastive
development: cyclic action sensitivity was about `5e-6`, and the proposed
model was worse than state-only and within-bank permutation for every seed.
The next route therefore does not add updates to that representation. It tests
a model-based objective that jointly learns raw action-prefix dynamics and
predicts physical progress-component changes before converting them to value.

## Frozen Data

- Development combines the 12 audited Runtime-Anchored groups and the 12
  Setwise development groups. The 24 physical groups must be unique.
- The 12 Setwise confirmation groups remain locked and are read only after a
  complete development gate. No validation/formal scenes are read.
- Inputs are deployment-visible boundary state features and the first 16
  normalized 7-D candidate actions. Targets are the two already preregistered
  horizon-32 physical progress components. Official success, future execution
  length, final simulator state, and oracle predicates are forbidden inputs.

## Model And Controls

- Proposed: a compact temporal action encoder trained jointly with a
  state-conditioned FiLM/bilinear head to predict the two progress components.
  Family identity is represented only through the existing deployment-visible
  instruction/state embedding.
- Controls: state-only component predictor; within-bank action permutation;
  and action-only predictor without boundary state.
- Induced candidate ranking is computed only from predicted progress
  components using the frozen progress aggregation. No outcome is consulted at
  deployment time.

## Splits And Gate

- Three fixed seeds `202642301/302/303` and three physical-group-disjoint,
  family-balanced folds; all eight branches from one group stay together.
- Exactly 3000 updates per worker, no performance early stopping.
- Primary: physical-group-equal component MSE. Secondary: induced non-tie
  pairwise log loss with tie tolerance `1e-6`.
- For every seed the proposed model must beat every control on both primary
  MSE and induced pairwise loss. For every control, 10,000 physical-group
  bootstrap draws must give lower 95% improvement above zero on both metrics.
- Only a complete pass freezes the model and permits one locked-confirmation
  evaluation. Confirmation must pass the same seed/control conditions before
  any online QGF experiment.
- Failure freezes this configuration. No added seed/update, task removal,
  threshold change, or architecture search is allowed.

This route is critic evidence, not online QGF efficacy.
