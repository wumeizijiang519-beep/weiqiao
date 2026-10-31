# Ensemble-Disagreement Projection QGF V1

## Motivation

Support-Gradient QGF did not produce stable real progress gains. This route
tests a scientifically different outcome-blind local objective: reduce the
disagreement among three independently trained masked-action encoders rather
than reduce their mean reconstruction energy.

## Frozen Intervention

- At candidate0, compute each frozen encoder's reconstruction at mask positions
  `0,3,...,30` and the mean squared deviation from their ensemble prediction.
- Differentiate this disagreement with respect to the 16-step continuous action
  prefix. Gripper values are immutable.
- Follow the negative normalized gradient at fixed fractions
  `0.25,0.50,0.75,1.00` of the already frozen family median support radius,
  clipped to the existing normalized action range. Degenerate gradients fail
  closed.
- The N8 bank is candidate0, native candidates1-3, and four disagreement
  projection candidates. No reward, progress, success, validation, or formal
  outcome enters candidate construction.

## Prospective Test

Select 8 new training-only physical groups, two per task family, by a frozen
result-independent hash after excluding every group with prior real branch
results. Run one fixed pilot, then the remaining 11 groups only after a clean
artifact audit. Every candidate uses an independent fresh environment and the
Runtime-Anchored replay/commit contract.

Admission requires all 8 groups complete and either two binary-discordant
groups across two families, or at least two families whose physical-group
bootstrap lower 95% progress delta for the fixed full-radius projection exceeds
both candidate0 and uniform-random. Pilot plus population cap is 14,400 allocated
GPU seconds including failures. Passing is only an online-validation admission,
not QGF efficacy. Failure freezes direction, radius, masks, checkpoints, groups,
and horizon.

The initial 12-group registration attempt was rejected before registration or
GPU use because one family had only two never-executed eligible physical groups.
The frozen repair uses the common minimum of two per family; it does not replace
groups or inspect outcomes.
