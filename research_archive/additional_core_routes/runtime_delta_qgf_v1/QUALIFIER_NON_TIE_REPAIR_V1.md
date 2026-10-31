# Runtime-Delta Qualifier Non-Tie Repair V1

The first qualification implementation incorrectly required every physical
group to contain at least one non-tie candidate pair. The frozen protocol
defines the secondary endpoint as non-tie pairwise log loss with tolerance
`1e-6`; it does not make the absence of a non-tie pair a collection failure.

This repair preserves the first qualification output and changes only the
aggregation of the secondary endpoint:

- component MSE continues to include all 24 physical groups;
- pairwise log loss includes every physical group with at least one pair whose
  target difference exceeds the frozen `1e-6` tolerance;
- no group, target, prediction, seed, control, threshold, update, or model is
  changed;
- bootstrap resampling uses the complete physical-group inventory defined for
  each endpoint (24 for MSE and the frozen non-tie inventory for pairwise).

The repaired qualification is written to a new directory and the invalid
first implementation remains preserved.
