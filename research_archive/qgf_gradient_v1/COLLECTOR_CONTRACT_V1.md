# Prospective Training Collector Contract

The user authorized completion of collection, RL critic fitting, matched online
comparisons and a new45minute progress heartbeat on2026-10-26. Prior stopped
configurations remain frozen. This contract implements Stage1 of PROTOCOL.md.

## Population and First Dispatch

Use the frozen COHORT_MANIFEST.json SHA
7194f02c8dba2c9ae01fddab1d0c48c169e28f6778e3926a0386dfeff0307af9.
Select the first training entry in manifest order for each of its four task
families. register_integrity.py writes COLLECTOR_INTEGRITY_V1.json once, with
source hashes and exact episode IDs before execution. These four entries count
once in the fixed288training cohort. No class-balance gate is applied to four
integrity episodes; class qualification occurs after the fixed full cohort.

First dispatch uses one verified idle GPU0 under job1593640/gpu1,8CPUs/45GB,
one model, hard60minutes including independent audit. Python collection has
55minutes and independent audit4minutes. Preliminary load/compile reference is
431s from Stage0; actual worst-case episode times must be measured before the
remaining284entries can be scheduled. At most two initial integrity attempts,
aggregate2GPUh counted within the24GPUh collection cap. Valid completed episodes
must never be replayed or discarded. Unknown errors stop; preserved prefixes
do not acquire fictional completion labels.

## Action and Reward

Use official BF16/compiled Simple-WAM, frozen checkpoint/statistics, dual camera,
32generated actions, at most10executed,700model steps after30official dummy
waits,10inference steps, frozen future video noise and text encoder offload.
The initial-state bytes and scene assets must match the manifest; actual
simulator restore must agree within1e-6 before any dummy/model action.

At every boundary generate four native seeds10000/11000/12000/13000 under the
same current observation. Zero-weight scheduler instrumentation records raw
normalized actions while preserving native output. The independent selection
Generator uses the frozen per-episode selection seed. Execute only its selected
native prefix. Save per-step reward, done, official check_success, simulator
state, actual execution length and remaining horizon. Terminal includes success,
environment done and the fixed task timeout. Never bootstrap beyond that timeout.
Only the selected candidate receives the actual chunk reward sum; all three
unexecuted returns stayNaN. Dummy feedback is stored separately from model RL
transitions. Pre-boundary termination is retained without replacing the scene.

Native gripper is binary-1/+1 after official conversion. For critic inputs,
invert that conversion to dataset0/1 then apply the frozen affine action
normalizer. Continuous inverse mapping does not clip to[-5,5], so it exactly
reconstructs the executed action. Save both raw sampler actions and canonical
actually-executed normalized actions. This distinction must also be respected
when constructing the later online Q input; gripper gradients remain masked.

## RNG and Model State

Each boundary records Python random, NumPy legacy, Torch CPU and every visible
CUDA generator, plus separate selection-Generator state. Candidate inference
uses the official explicit local generator seed. Restore the same caller
snapshot before each inference. After all candidates/replays, restore the
candidate0 post-inference caller state before stepping the environment. Save
before, each candidate post, committed caller and after-execution RNG files.
The simulated trajectory therefore does not inherit extra random draws from
unused candidates. Selected native/raw actions replay within1e-6 at every
boundary; candidate0 replays at every episode's first boundary.

Official Simple-WAM infer_action is stateless across replans: video K/V and
latent caches are local to each call. Compiled executable caches are retained;
the text context cache is immutable after first encoding. Record context
hashes and verify registered model buffers are unchanged over first-boundary
replays. Source/checkpoint remain fixed, actor parameters have requires_gradFalse.
There is no persistent policy-history object being silently discarded.

## Retained Evidence and Independent Audit

Every boundary persists proposals before action execution, then overwrites a
run-local execution_progress.npz after each real step. Keep contiguous
transition NPZ, R+1 observation NPZ, selection/RNG snapshots, raw state traces,
config, progress, summary, video and original process status. Scientific runs
use fresh directories; failures are retained. A proposal without execution has
no measured reward label.

The independent auditor reloads files, reconstructs the uniform selection
sequence, action affine roundtrip, prefix commit, finite-horizon progression,
terminal mask, actual reward sum, counterfactualNaN labels, observations,
simulator traces and caller RNG hashes. It verifies all transition hashes and
decodes the full video, requiring31+model_steps frames. Audited data validity
and clean process exit are recorded separately. No eligibility follows from
software tests alone.

After all four entries pass, freeze actual costs and use measured p90 with
loading/compile overhead and20%reserve to assess the24GPUh full-cohort cap.
Only then register remaining training shards. No outcome-driven sample-count
change, task screening or extra failure collection is permitted. The final
12success/12failure/8physical-groups-per-class and OOF coverage gates remain
unchanged.
