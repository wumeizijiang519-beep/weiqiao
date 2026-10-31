# Deadline and resource acceleration V1

User confirmed platform cutoff: 2026-11-01 00:00 Asia/Shanghai (October31 24:00).
Target October30 for a recoverable off-platform evidence export; this is not a
promise of positive scientific results. Never start work that cannot finish,
be audited and be exported before the platform cutoff.

Keep current dispatcher and fixed cohort unchanged. Do not split/restart its
last shard or re-run completed episodes. Full data admission still precedes
feature extraction and critic fitting. No science gates or budgets change.

Fresh allocated resources on October26: job1581551/gpu4 has256GB/16CPU/4A800;
physical GPU0 and GPU2 have unrelated actors and must not be touched. GPU1 and
GPU3 were idle. Job1598338/gpu22 has60GB/16CPU/2A800, both idle; use primarily
for independent small critic folds/seeds, not two simultaneous WAMs. Job1593640
on gpu1 expires October29 15:50CST and has50GB, at most one loaded WAM.
Re-check Slurm, UID, cgroup, UUID, process occupancy and memory before launch.

Resource qualification uses owned Slurm step_extern on the verified allocated
node, not a fabricated exclusive Slurm step. Record real PID/cgroup/UUID/start/
end/exit. Charge one GPU for each bounded worker's elapsed time, including
failures, separately from parent-allocation reservation hours. Never describe
these workers as newly allocated Slurm steps. Existing unrelated workloads and
their reservation costs remain outside this experiment; report this distinction.

First qualify gpu22 CUDA kernels and gpu4 EGL/current official inference without
robot actions. Use one GPU3 WAM at a time, original8-thread settings, checkpoint,
seeds, dtype, compilation and immutable zero_action_probe.py. Compare every
stored action/normalized action and support basis against frozen Stage0 arrays
at max absolute error1e-6; no new model implementation or reinterpreted result.
This is resource portability, not new Stage0 efficacy evidence. EGL probe uses
an empty MuJoCo scene, never a cohort episode. No real-data features or fits.

One gpu4 attempt hard1200s and two sequential gpu22 kernel checks hard180s
each, at most1560GPU seconds =0.433334GPUh, charged to integration2GPUh.
Stage0 previously1058s; total integration worst2618s remains below80% of2h.
No automatic retries. Resource failure does not revise scientific thresholds.
Source hashes are frozen in RESOURCE_ACCELERATION_SOURCES.json before dispatch.

After qualification/data admission, implement independent critic fold/seed
workers on gpu22, and WAM feature/online workers on gpu4 idle devices. Keep
at most2 WAMs under256GB and within CPU limits, requalifying any thread change.
Online assignment changes scheduling only, not cohort, seeds, paired arms,
compute matching or outcome-driven stopping. Forecast p90 stage cost before
launch; existing128GPUh caps and20% reserve apply. Full trainer and online
dispatcher are not claimed implemented by this resource registration.

Export priority: source/protocols/manifests/configs/critics/results/cost ledgers,
then irreplaceable training trajectories and selected evidence videos. Inventory
sizes and local free space first. Never put large files in cluster home or
upload to an unapproved cloud. Missing exports remain explicitly outstanding.
Sound notifications remain forbidden.
