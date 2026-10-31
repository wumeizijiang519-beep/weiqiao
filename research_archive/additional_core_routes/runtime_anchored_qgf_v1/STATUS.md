# Runtime-Anchored QGF V1 Status

## 2026-10-28 20:55 CST - Critic qualification stopped negative

- All nine fixed three-seed by three-fold workers completed 3,000 updates with
  clean process exits. Their original 30 MiB result tree was written to home by
  a relative-path registration bug; it was copied byte-for-byte to pqr with a
  matching sorted SHA manifest and was not retrained.
- One of 12 physical groups has exactly identical horizon-32 progress for all
  eight candidates, hence no non-tie pair under the frozen `1e-6` tolerance.
  The repaired zero-GPU qualifier conservatively keeps it in the denominator
  with zero control improvement and requires complete 12/12 coverage.
- Frozen status: `NO_STABLE_RUNTIME_ANCHORED_CRITIC`. Report SHA:
  `f4bfadc77edd7df19cdbee5245eaa5880773e3fc8c78081a8652e92e4bbeeaee`.
  All seeds beat state-only and have action sensitivity 1.0, but seeds
  202642301 and 202642302 do not beat within-bank permutation. The state-only
  delta CI is [-0.0744, 0.1151] and permutation delta CI is
  [-0.1131, 0.0943], both crossing zero.
- The Runtime-Anchored data therefore show real continuous candidate effects,
  but the preregistered critic does not identify those effects stably beyond
  action permutation. This is not online QGF efficacy. No held-out online
  five-arm evaluation or formal run is authorized by the gate.

## 2026-10-28 20:32 CST - Signal admitted; four-GPU critic qualification running

- Fixed-index resume step `1593640.416` completed cleanly in 3,023 GPU seconds
  with eight real branches, unchanged candidate bank, replay error 0, and
  commit errors 0. Total collection cost including all failures is 11,180 GPU
  seconds, below the frozen 14,400-second cap.
- The finalizer combined exactly pilot entry 0, original entries 1-10, and the
  clean resumed entry 11. Entries 12-15 were not executed under the stopping
  rule frozen before the resumed outcome. Final REPORT SHA is
  `0b282cc4a8f6063a9c8b71292abbec8d3aa16df7c94ab604bfaba0836731b0b0`.
- Independent audit passed for 12 physical groups and 96 real branches with no
  errors; audit SHA is
  `eb8aa754a2dd333cb708e7ea394b90b30973c77a05adcbd06a079b2dfb3aacc4`.
- Status is `RUNTIME_ANCHORED_ACTION_VALUE_SIGNAL_ADMIT`. Binary discordance is
  insufficient, but continuous progress-range bootstrap lower bounds exceed 0
  in 2 families at step16 and 3 families at step32. This admits critic research
  only and is not online QGF efficacy.
- A deployment-visible 96-row critic corpus passed independent audit. Nine
  fixed seed-by-fold workers (three seeds, three group-disjoint folds, matched
  action-aware/state-only/permutation models) are now dispatched across four
  owned critic-only A800s on gpu22 and gpu4. The matching outcome-blind action
  encoder initialization is frozen per seed.

## 2026-10-28 19:31 CST - Fixed-index infrastructure continuation running

- Root-cause evidence is frozen in `INFRASTRUCTURE_ROOT_CAUSE_V1.md`. The
  interrupted step is classified infrastructure-invalid: no OOM evidence,
  MaxRSS 34,113,940 KiB under 45 GiB, task tree disappeared while `srun`
  remained blocked, and index 11 had only four partial branches.
- The recovery rule was frozen before reading a resumed outcome: run only
  registration index 11 once in a new directory. A clean result yields the
  preregistered minimum 12/16 groups; indices 12-15 will not be adaptively run.
- First wrapper step `1593640.415` failed in 7 s before model construction or
  actions because the wrapper pre-created the runner-owned directory. The
  preserved retry1 changes only that wiring error.
- Exact step `1593640.416` is now running on job1593640/gpu1/GPU0 with the
  unchanged runner, manifest, authorization, model, seed, candidates, horizon,
  and thresholds. Its hard limit is 6,000 GPU seconds. No further retry is
  authorized.

## 2026-10-28 19:25 CST - Remaining execution stopped on infrastructure hang

- The repaired pilot remains independently audited PASS (`1593640.411`, 535
  GPU seconds). The non-duplicated remaining run `1593640.412` completed fixed
  registration indices 1 through 10 with no unavailable groups.
- During index 11, the worker produced the frozen candidate bank and began real
  branch execution, then disappeared without `REPORT.json`, `PILOT_RETURNED`,
  `FAILED.txt`, or a process exit receipt. Slurm left the step RUNNING with no
  task PIDs, no log growth, and the `srun` frontend blocked in `pipe_wait`.
- After confirming the step had no remaining task process, the owned orphaned
  step was cancelled once to stop charging idle GPU allocation. Final Slurm
  state is `CANCELLED by 2292`, exit `0:9`, elapsed 7348 seconds. All ten valid
  completed groups and the partial index-11 directory are preserved.
- This is an infrastructure-invalid partial population, not a scientific gate
  result and not QGF efficacy evidence. No finalizer, critic, replacement group,
  or automatic GPU retry has been run.

## 2026-10-28 13:49 CST - CPU preparation complete, GPU not launched

- Motivation: Progress-Pairwise V2 became scientifically inadmissible because
  exact equality to legacy archived policy images failed for too many otherwise
  deterministic physics replays.
- New prospective contract uses all 16 V2 development groups selected before
  V2 outcomes. It generates N8 once from a newly captured runtime boundary
  observation, then executes each frozen candidate in an independently replayed
  fresh environment. Full simulator state, proprioception, prefix receipts, and
  action commit remain exact; branch raster hashes are metadata because no
  branch invokes the policy.
- Registration contains 16 unique training-only groups. Manifest SHA:
  `ba97d5303ceabc9d4455356d7f732cdc643f995fb00f9393b6819db8752947c1`.
- Protocol, runner, registration builder, pilot wrapper, and independent pilot
  audit are implemented. Local and remote CPU syntax/contract tests pass.
- The pilot is intentionally not launched while V2 step `1593640.407` owns the
  only numerically qualified WAM GPU. After V2 exits cleanly and its insufficient
  result is finalized/audited, the fixed entry-0 pilot may launch once.
- No Runtime-Anchored paired result, critic result, or online QGF result exists.
