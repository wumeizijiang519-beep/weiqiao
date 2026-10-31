# Remaining Orchestration Repair V1

Step 1593640.400 completed entries 1 and 2, then stopped at entry 3 because
that frozen group's reconstructed dual-camera policy observation differed from
its archive. Entry 3 remains fail-closed and is never retried or replaced.

The scientific runner, model, candidate bank, seeds, support basis, progress
labels, horizon and thresholds are unchanged. The only orchestration repair is
to continue at entry 4 and, for this exact boundary-observation mismatch only,
record a group as unavailable and proceed to the next preregistered entry.
Every other nonzero exit stops the process. Completed entries are never rerun.

The failed step consumed 1,442 allocated GPU seconds. Together with the
754-second pilot, 2,196 seconds are charged, leaving at most 12,204 seconds of
the original 14,400-second cap. The resume hard timeout is 12,180 seconds.
This is the single user-authorized minimal infrastructure repair; no further
automatic GPU retry is allowed.
