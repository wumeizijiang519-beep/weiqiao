# Direct-Pairwise Runtime QGF V1

## Motivation

Runtime-Delta increased raw-action sensitivity, but component regression did
not produce stable candidate ordering. The action-only component predictor was
strong while induced pairwise loss remained near chance. This route therefore
optimizes the deployment decision directly: non-tie within-bank candidate
pairs, without first fitting absolute progress components.

## Frozen Data And Inputs

- Development is the same 24 unique training-only groups in the audited
  Runtime-Delta corpus. Setwise confirmation remains sealed.
- Inputs are only deployment-visible boundary state features and the first 16
  normalized 7-D candidate actions.
- Pair labels are the sign of the already frozen scalar progress difference;
  differences within `1e-6` are ties and excluded before training.
- Three fixed seeds `202642301/302/303`, the existing three group-disjoint
  family-balanced folds, and exactly 3000 updates are used.

## Model And Controls

- Proposed: a raw temporal action encoder plus a low-rank state-conditioned
  action gate. Scores are used only through within-bank pair differences.
- Controls: action-only scorer, candidate-independent state-only scorer, and
  the proposed scorer trained with a fixed within-bank action permutation.
- Every model receives the same sampled pair indices and update budget.

## Gate

- Primary endpoint is physical-group-equal non-tie pairwise log loss.
- For every seed, proposed must beat all three controls.
- For every control, 10,000 physical-group bootstrap draws must have a lower
  95% improvement bound above zero.
- Only a complete development pass permits one locked-confirmation evaluation.
  Failure freezes this configuration without extra seeds, updates, task
  removal, threshold changes, or architecture search.

This is critic evidence, not online QGF efficacy.
