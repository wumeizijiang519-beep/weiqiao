# QGF v5 Candidate-Centered Advantage Protocol

Frozen: 2026-10-24 11:14 CST, before candidate-set dataset preparation or
training. This is a separately named response to the frozen QGF v4 negative
result; v4 checkpoints, splits and conclusions remain unchanged.

## Motivation

QGF v4 predicts return from a state and one absolute action chunk. It improves
over state-only on average but does not beat the action-shuffled control. The
randomized-intervention logs retain all four proposals at each state while only
the uniformly selected proposal has an observed return. V5 therefore models the
selected proposal as a deviation from its contemporaneous candidate set instead
of asking a network to recover small proposal differences from absolute poses.

## Frozen Data And Estimand

- Reuse only the 32 admitted QGF v4 Train32 episodes. No new rollout is added.
- At each replan, retain state, all four native 10x16 proposals, uniformly
  randomized selected index, and the selected proposal's observed finite-horizon
  return. Propensity is exactly 1/4. Unexecuted proposals never receive labels.
- Verify selection-row count, episode segmentation, selected/committed action
  equality, finite values and source SHA before training.
- Candidate features are normalized train-only deviations from the within-state
  candidate mean, plus candidate-set spread. Candidate scores are decomposed as
  `V(s) + A(s,a_i,A)`, with advantages centered to zero across the four proposals.

## OOF Design And Controls

- Four episode-disjoint folds are the four original eight-episode collection
  shards. Each validation fold has one or two failures; training has at least
  five failures. Collection-shard identity is never an input.
- Fixed bootstrap seeds: 202624001, 202624002, 202624003.
- Compare candidate-centered action critic, identical state-only critic, and a
  within-state selected-index permutation control. The permutation is fixed by
  fold/seed and changes only training treatment assignment, never validation.
- Exactly 10000 optimizer steps, fixed final checkpoint, train-only scaling and
  episode-equal sampling. No held-out early stopping or fold/seed selection.

## Decision Rule

Pool each seed's four OOF folds. Candidate-centered action must beat state-only
and permuted-assignment controls on episode-equal finite-horizon target error in
all three seeds, and candidate-score margins must be nonzero and responsive to
within-set permutation. Otherwise stop this configuration. Passing only admits
a fresh matched online comparison of candidate0 N4, random N4 and v5 QGF N4;
it is not itself a robot success-rate result.

