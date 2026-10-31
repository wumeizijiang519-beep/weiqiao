# Outcome-Blind Ensemble-Consensus QGF V1

The mean support energy did not predict progress. This distinct route tests
epistemic consistency across the three independently trained outcome-blind
action encoders. For each frozen 32x7 candidate and the same fixed mask
positions `0,3,...,30`, compute each encoder's masked reconstruction MSE and
score the candidate by the negative variance across the three energies.

Scores for all 24 development groups are frozen before outcomes are read.
Select minimum variance with candidate index as tie breaker. Relative to both
candidate0 and within-bank uniform-random expected progress, 10,000 physical-
group bootstrap lower 95% bounds must exceed zero, with positive improvements
in at least two task families. Passing permits a small training-only online
pilot; failure freezes the route without mask/checkpoint selection.

This gate is not online QGF efficacy.
