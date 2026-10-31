# Formal Available-Card Execution Amendment

Timestamp: 2026-10-30 15:40 CST

The user explicitly requested immediate use of available assigned GPUs before
the platform is retired after 2026-10-31. Read-only Slurm inspection confirmed
that job `1581551` is owned by `wangsenbao221`, is named `OpenWAM_5_0`, remains
RUNNING with `Reason=None`, has four A800 GPUs and 256 GB allocated host memory,
and has no active child step. A bounded one-GPU probe reported 4 MiB GPU memory
used, 0% utilization, and ample host memory.

This amendment changes orchestration authorization only: exact job `1581551`
may be supplied to the already frozen formal dispatcher. The zero-robot-action
compatibility gate remains mandatory and must pass EGL, layer-29 feature
repeatability, native/raw replay, final-critic/QGF integration, and the `1e-6`
state tolerance before any formal action. If the gate fails, no formal lane is
launched. The formal registration, 103 physical groups, 412 tasks, final critic
checkpoints, token, support bounds, QGF coefficients, seeds, endpoints, and
statistical thresholds are unchanged. Existing completed tasks, if any, remain
immutable and must never be rerun.

No scientific result or formal outcome was read to create this amendment.

The first dispatcher invocation stopped before the compatibility gate because
this older allocation reports GPU count in `TRES=` rather than `AllocTRES=`.
No execution directory was created and no formal outcome or robot action was
read. The bounded repair changes only that resource-count parser; the failed
dispatcher log and PID receipt remain archived.

The repaired strict gate on job `1581551` then failed before any robot action
or formal outcome with `held-out initial state changed`. This is a numerical
compatibility failure and is not retried or relaxed; no formal lane launched.
The user requested continued immediate attempts on available owned cards. A
read-only probe confirmed one explicitly owned GPU in job `1598338` on gpu22
was idle (4 MiB used, 0% utilization) with no child workload. Exact job
`1598338` is therefore additionally authorized for the same mandatory
zero-action gate. Because that allocation has only 60 GB host memory, it is
hard-limited to one WAM process/lane even though it owns two GPUs. Its legacy
non-WAM job name is accepted only for this exact job. All scientific bytes and
formal endpoints remain unchanged; gate failure still launches no lane.

Both strict gate attempts failed at the pre-runtime initial-state SHA check.
Source comparison established the deterministic root cause: the first frozen
formal scene uses an `_add_17.pruned_init` asset, and the audited online runner
reshapes `_add_`/`_level` init arrays to one row before indexing, while the
gate omitted that same loader branch. Thus each gate hashed a scalar slice,
not the registered state. The bounded repair copies the already frozen runner
reshape condition into the gate verbatim. It changes no state, hash, tolerance,
model, action, registration, or endpoint. Both failed logs and costs remain
archived; one source-audited retry is allowed on job `1598338`.

After the corrected gpu22 gate passed, observed one-lane throughput was about
eight tasks per hour, which risks missing the platform deadline. The earlier
gpu4 gate failure is now known to have been caused by the same fixed loader
bug, not a gpu4 numerical result. A second zero-action gate may therefore run
on exact owned OpenWAM job `1581551` while the gpu22 lane continues. The gate
wrapper accepts an explicit alternate output directory solely to keep the two
gate receipts separate. No formal lane may be added until this independent
gpu4 gate passes and the active task boundary is safely coordinated.

The independent gpu4 gate passed with the same zero-action metrics as gpu22.
At that time the gpu22 lane had 12 immutable complete tasks and had created an
incomplete task 012. Step 1598338.70 was cancelled, the incomplete task 012
directory and log were preserved under an explicit infrastructure-preemption
suffix, and no completed task was moved or rerun. A dedicated audited resume
dispatcher starts exactly four modulo lanes on job `1581551`; each lane skips
the 12 existing complete receipts, while task 012 is recollected once as the
first unfinished task. Finalization still requires exactly 412 reports and
complete markers and zero FAILED receipts.

The first four-lane launch requested eight Slurm CPUs per process, but legacy
job `1581551` owns 16 CPUs total, so Slurm admitted only two GPU steps. Before
either step completed a task, both were cancelled; incomplete task 012 and 014
directories/logs were preserved with `infra_gpu4_cpu8_preemption_partial`
suffixes. The bounded orchestration repair requests four Slurm CPUs per WAM
process, allowing four GPU steps within the fixed 16-CPU allocation. The WAM
runtime's frozen environment and OMP settings are unchanged; this modifies
only scheduler CPU accounting and does not change any scientific input.
