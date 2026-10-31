# Outcome-Blind Support-Energy QGF V1

## Motivation

Four supervised critic families failed to generalize across physical groups.
This route stops fitting outcomes. It tests a deployment-visible QGF signal:
how well each WAM candidate lies on the frozen native action-prefix manifold,
measured by masked reconstruction energy from the three independently trained,
outcome-blind action encoders.

## Frozen Score

- Use the same 24 development groups; confirmation remains sealed.
- For each full native/structured `32x7` candidate, mask positions
  `0,3,6,...,30`, reconstruct with each of the three frozen encoders, and
  average masked MSE across positions, dimensions, and seeds.
- Candidate score is negative reconstruction energy. No reward, success,
  progress, final state, or branch length may be read while scores are built.
- The complete score table and input/checkpoint hashes are frozen before any
  progress target is opened.

## Development Gate

- Select the lowest-energy candidate in each bank with candidate index as the
  deterministic tie breaker.
- Compare its frozen horizon-32 scalar progress against candidate0 and the
  within-bank uniform-random expectation.
- Both physical-group bootstrap improvement lower 95% bounds must exceed zero
  with 10,000 draws, and at least two task families must have positive mean
  improvement against both controls.
- A complete pass permits one new training-only online pilot of support-energy
  gradient guidance. Failure freezes this score without threshold tuning,
  checkpoint selection, or additional masks.

This development gate is not online QGF efficacy.
