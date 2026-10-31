# Runtime-Anchored Remaining Infrastructure Root-Cause Audit V1

## Frozen evidence

- Step `1593640.412` completed registration indices 1 through 10.
- Index 11 created the frozen policy input, RNG receipts, N8 bank, branch order,
  and four complete branch artifacts for candidates 6, 0, 2, and 5.
- The last artifact was published at 2026-10-28 19:20:49 CST. The worker was
  still CPU-active after 19:22, then the complete Slurm task process tree
  disappeared without `REPORT.json`, `PILOT_RETURNED`, `FAILED.txt`, or a
  process exit receipt.
- Slurm continued charging the step with no task PIDs. The client-side `srun`
  remained blocked in `pipe_wait` and the log stopped growing. There was no
  kernel OOM report; MaxRSS was 34,113,940 KiB under the 45 GiB request.
- After the no-task condition was confirmed, the owned orphan step was
  cancelled. Final state: `CANCELLED by 2292`, exit `0:9`, elapsed 7,348 s.

## Classification

This is an infrastructure-invalid interrupted execution, not a scientific
failure. The original completed groups and partial index-11 directory are
immutable evidence. No result from the partial group is admitted.

## Bounded recovery

The only permitted recovery is one new step for frozen registration index 11
using the unchanged manifest, authorization, support basis, runner, model,
seed, candidate construction, horizon, and thresholds. It writes to a new
directory and does not alter or reuse the partial artifacts. Indices 0 through
10 are not rerun. Indices 12 through 15 are not run: index 11 was fixed before
outcomes and, if complete, raises the population to the preregistered minimum
12 of 16. This stopping rule is frozen before the resumed outcome is observed.

The recovery receives at most 6,000 allocated GPU seconds. Together with the
267 s failed pilot, 535 s valid pilot, and 7,348 s interrupted remaining step,
the worst case is 14,150 s, below the 14,400 s collection cap. Any nonzero
recovery exit freezes the branch; there is no further retry.
