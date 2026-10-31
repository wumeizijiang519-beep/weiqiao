# Regularized-Linear QGF V1

## Motivation

Direct-Pairwise high-capacity temporal/state interaction models catastrophically
overfit physical groups. This route tests whether the frozen data support a
low-capacity, physically structured decision rule rather than another neural
architecture. It is scientifically distinct: no learned temporal encoder and
no nonlinear state network are used.

## Frozen Inputs And Features

- Use the same audited 24 development groups; confirmation remains sealed.
- Each 16x7 action prefix is summarized by per-dimension mean, standard
  deviation, first value, last value, and cumulative sum (35 fixed features).
- Boundary state is reduced to eight principal components fitted only on the
  training groups of each OOF fold, using one state vector per physical group.
- Proposed features are the action summary and its outer product with the eight
  state components. Controls are action-only, candidate-independent state-only,
  and a fixed within-bank action permutation.

## Training And Gate

- Three fixed seeds `202642301/302/303`, three existing physical-group folds.
- Direct non-tie pairwise logistic loss, tie tolerance `1e-6`.
- One linear scorer per model, fixed AdamW learning rate `1e-2`, weight decay
  `1e-2`, exactly 3000 updates, no early stopping or architecture search.
- Primary endpoint is physical-group-equal pairwise log loss. Every seed must
  beat all controls, and each control must have a 10,000-draw group-bootstrap
  lower 95% improvement bound above zero.
- A complete development pass alone permits one locked-confirmation test.
  Failure freezes this route without added updates, seeds, or feature changes.

This is critic evidence, not online QGF efficacy.
