# Support-Gradient Remaining Execution V1

The fixed pilot completed in 762 GPU seconds and passed the independent audit.
The remaining execution visits preregistered entries 1 through 15 exactly once,
in index order, on the same WAM-compatible allocation. It does not regenerate
the pilot or replace unavailable groups.

The total collection cap is 28,800 allocated GPU seconds, including the pilot
and any failed infrastructure time. The remaining wrapper has an inner limit
of 28,140 seconds. Exact dummy or prefix replay mismatch is recorded as
unavailable and execution continues; every other nonzero result stops the run.
The model, action bank construction, groups, seeds, support radii, horizon, and
scientific thresholds are unchanged.
