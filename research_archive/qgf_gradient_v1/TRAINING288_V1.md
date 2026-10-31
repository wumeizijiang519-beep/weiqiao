# Fixed Prospective Training Cohort Collection

Registered2026-10-26CST after the four integrity entries completed cleanly in
step1593640.314 and passed independent action/reward/RNG/observation/video audit.
That step used819allocated GPU seconds; the four entries had2successes and
2failures. Their outcomes do not select any task,seed or sample count.

The original COHORT_MANIFEST.json remains byte-identical. Four completed IDs
train_0003,train_0006,train_0002,train_0000 count once. Remaining284entries retain
manifest order and are split into four sequential71episode shards, without
outcome selection. The union is exactly the fixed288training entries, with no
validation/formal entry and no replacement. All scientific collector settings,
model/source/checkpoint/statistics/RNG/labels are identical to the audited
collector. No stopped old dataset is used.

register_remaining.py writes training288_v1/REGISTRATION.json and four hashed
per-shard manifests once. It checks the preceding audit/clean exit, all original
collector source hashes and exact entry union. Source files are copied to each
run by the unchanged collector before model loading. Dispatch uses a fresh run
directory per shard and stops on any failure. Completed episodes are retained
and never resampled automatically. No automatic retry is included in this batch.

## Budget and Resources

Observed integrity p90episode time220.684444488s, including its cold first
episode. Measured non-episode load/setup overhead297.291169900s. Conservative
forecast:819spent seconds +284*p90 +4*(measured overhead+60s housekeeping).
The exact computed value is frozen in REGISTRATION.json; it must be<=19.2GPUh,
preserving20percent of the24GPUh cap. Hard bound819+4*16500=66819s=18.560833333GPUh.
All failures remain charged. The unused reserve is not a request to consume it.

One model at a time under verified job1593640/nodegpu1/GPU0,8CPUs/45GB.
Each GPU shard hard4h35m,Python collection4h33m20s; no overlapping WAM in the
50GBallocation. Parent expiry2026-10-29 15:50CST is checked before dispatch.
Full actual wall time and Slurm resource costs must be frozen afterward.

Independent file/video/RNG audit runs AFTER releasing the GPU step, in a
separate1CPU/4GB/zero-GPU Slurm step with30minute hard cap. This changes only
resource scheduling, not the auditor or scientific contract. Record audit CPU
wall/step separately instead of burning reserved GPU time while decoding files.
The next GPU shard starts only after the previous independent audit passes.
No environment/model action occurs during this file audit.

## Completion and Next Gate

The dispatcher writes ALL_SHARDS_AUDITED only after all four GPU processes
complete0and all four CPU audits pass. Then independently aggregate these284
entries with the four integrity entries. Verify actual unique288episode IDs,
SHA/scene mapping,action contracts and episode/group counts. Require at least
12successes and12failures,eachclass in8physical groups,and every frozen group
OOFfold containing both classes. If not met, freeze data insufficient and stop
this version without extra collection or label changes. Interim class counts
do not stop or change the frozen cohort.

Only admitted data can enter the separately registered current-observation
feature extraction and fixed-step IQL/control comparisons. There is still no
learned critic or online QGF efficacy claim at collection launch.
