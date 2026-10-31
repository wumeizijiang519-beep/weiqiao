# Exploration Engineering Smoke Retry2

The original exact-seed smoke202619000 stopped at expert feasibility: unstable
object018_microphone. No policy action/candidate selection was executed; no
policy failure label exists. Keep its FAILED marker, traces and checksums.
Candidate server loaded and shut down cleanly; teardown also segfaulted after
the primary expert-feasibility exhaustion. Do not misattribute the root cause.

New named run exploration_smoke_window202619100_retry2 uses the FIRST official
expert-feasible scene in [202619100,202619120), at most20 feasibility attempts
and ONE executed policy episode. Freeze before launch. This supersedes the
exact-seed-only engineering rule for this retry only; never change the old run.
Selection seed202619001, task/config/checkpoint/action/success/deadline and all
parity/commit tests unchanged. Window exhausted means stop, not unbounded retry.
Exclude this whole window from subsequent training/validation/formal episodes.
No outcome-based scene acceptance. All failed feasibility attempts are retained.

45minute hard stage cap, two new assigned GPU tasks (1.5GPU-hours maximum), or
2.25GPU-hours conservatively including existing native reference. No bulk data
or critic training admitted until the new safety/timing smoke passes its audits.
