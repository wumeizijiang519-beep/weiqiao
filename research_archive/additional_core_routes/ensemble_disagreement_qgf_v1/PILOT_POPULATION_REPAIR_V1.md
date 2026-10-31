# Pilot Population Repair V1

The first pilot step failed before WAM construction or robot actions because
the reused runner retained the predecessor route's hard-coded population size
of 16. The registered population contains 8 entries. This repair changes only
that fail-closed metadata assertion from 16 to 8. Model, group, authorization,
candidate construction, seed, action, horizon, budget, and thresholds remain
byte-identical. The failed step and cost are retained.
