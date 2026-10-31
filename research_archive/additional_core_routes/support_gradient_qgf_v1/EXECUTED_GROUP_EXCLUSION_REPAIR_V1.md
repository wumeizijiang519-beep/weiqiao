# Executed-Group Exclusion Repair V1

The first cohort builder excluded every group ever registered by earlier
prospective protocols. That was stricter than the frozen Support-Gradient
contract, which excludes groups used by prior real branches. V1 and V2 contain
registered groups that failed boundary reconstruction before any candidate
branch was executed.

This repair derives exclusions from the frozen completed-result receipts:
Failure-Critical complete entries, Progress-Pairwise V1 final results,
Progress-Pairwise V2 final receipts, and all complete Setwise entries.
Unavailable groups with no branch outcome remain eligible. No prior outcome is
used to rank eligible groups; the unchanged result-independent hash selects the
new cohort. The failed first build log is preserved.
